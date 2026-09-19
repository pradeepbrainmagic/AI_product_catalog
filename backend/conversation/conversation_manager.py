import re
from backend.ai.qwen_service import (
    extract_catalog_query,
    understand_initial_message,
    generate_display_format_question
)

from backend.entity_pipeline import (
    resolve_extracted_entities,
    discover_missing_entities
)

from backend.conversation.conversation_state import (ConversationState)

from backend.conversation.dynamic_question_engine import (
    DynamicQuestionEngine
)

from backend.database.frontend_mapping import FrontendMapper

class ConversationManager:
    """
    Generic AI Product Catalog Conversation Manager.

    Conversation memory is persistent across messages.

    No fixed question sequence.
    No hardcoded product values.
    No hardcoded OEM/model/year logic.
    """

    def __init__(
        self,
        catalog_search,
        database_layer=None
    ):

        self.catalog_search = catalog_search
        self.database_layer = database_layer

        self.state = None

        self.question_engine = (
            DynamicQuestionEngine(
                database_layer=database_layer
            )
        )

        self.last_question_field = None
        self.last_question_options = []
        self.part_number_narrowing = False
        
        # =========================================================
        # PRODUCT DISPLAY FORMAT
        # =========================================================

        self.display_format = None
        self.display_format_pending = False
        self.pending_display_records = []

    # =========================================================
    # PREVIOUS QUESTION ANSWER
    # =========================================================

    def _resolve_previous_question_answer(
        self,
        user_message
    ):

        if not self.last_question_field:
            return {}

        if not self.last_question_options:
            return {}

        message = (
            user_message
            .strip()
            .lower()
        )

        for option in self.last_question_options:

            if message == str(
                option
            ).strip().lower():

                return {
                    self.last_question_field:
                        option
                }

        try:

            from backend.normalization.entity_normalizer import (
                resolve_entity
            )

            result = resolve_entity(
                user_value=user_message,
                candidates=self.last_question_options,
                entity_type=self.last_question_field
            )

            if result.get("status") == "resolved":

                return {
                    self.last_question_field:
                        result.get("matched_value")
                }

        except Exception:
            pass

        return {}

    # =========================================================
    # GET CURRENT FILTERS
    # =========================================================

    def _get_active_filters(self):

        if not self.state:
            return {}

        state_data = (
            self.state.get_all()
        )

        return {
            field: value
            for field, value in state_data.items()
            if value is not None
            and str(value).strip() != ""
        }
    # =========================================================
    # USER EVIDENCE GATE
    # =========================================================
    #
    # Qwen may sometimes generate additional fields which the
    # user never supplied.
    #
    # This gate keeps only values for which there is evidence
    # in the current user message.
    #
    # Important:
    # - Does NOT hardcode catalog values.
    # - Does NOT change database search.
    # - Does NOT change ConversationState.
    # - Does NOT change DynamicQuestionEngine.
    # - Legitimate user-provided Part Number / Fenner values
    #   are preserved.
    # =========================================================
    # =========================================================
    # USER EVIDENCE GATE
    # =========================================================

    def _filter_user_evidence(
        self,
        user_message,
        extracted_data
    ):

        if not isinstance(extracted_data, dict):
            return {}

        message = str(
            user_message or ""
        ).strip().lower()

        if not message:
            return {}

        # -----------------------------------------------------
        # Normalize text
        # -----------------------------------------------------

        def normalize(value):

            value = str(
                value or ""
            ).lower().strip()

            value = re.sub(
                r"[^a-z0-9\s]",
                " ",
                value
            )

            value = re.sub(
                r"\s+",
                " ",
                value
            ).strip()

            return value

        normalized_message = normalize(
            message
        )
        message_tokens = set(
            normalized_message.split()
        )

        # -----------------------------------------------------
        # Get database field metadata dynamically
        # -----------------------------------------------------

        available_fields = []

        if self.database_layer:

            try:

                available_fields = (
                    self.database_layer
                    .get_available_fields()
                )

            except Exception:

                available_fields = []

        field_metadata = {}

        if isinstance(
            available_fields,
            list
        ):

            for field in available_fields:

                if isinstance(field, dict):

                    canonical = (
                        field.get(
                            "canonical_field"
                        )
                    )

                    if canonical:
                        field_metadata[
                            canonical
                        ] = field

                else:

                    canonical = str(
                        field
                    ).strip()

                    if canonical:

                        field_metadata[
                            canonical
                        ] = {
                            "canonical_field": canonical
                        }
        # -----------------------------------------------------
        # Build dynamic field labels
        # -----------------------------------------------------

        field_labels = {}

        for field, metadata in field_metadata.items():

            label = (
                metadata.get(
                    "display_name"
                )
                or metadata.get(
                    "label"
                )
                or FrontendMapper.FRONTEND_MAPPING.get(
                    field
                )
                or field
            )

            field_labels[field] = normalize(
                label
            )
        # -----------------------------------------------------
        # Detect whether the user explicitly mentioned a field
        #
        # Examples:
        #
        # "part number 12345"
        # "fenner ABC123"
        # "id 2004"
        #
        # No catalog values are hardcoded here.
        # Only database field metadata is used.
        # -----------------------------------------------------

        explicitly_mentioned_fields = set()

        normalized_tokens = (
            normalized_message.split()
        )

        for field, label in field_labels.items():

            if not label:
                continue

            # Full field label
            if label in normalized_message:

                explicitly_mentioned_fields.add(
                    field
                )
                continue

            # Canonical field name
            canonical_label = normalize(
                field
            )

            if (
                canonical_label
                and canonical_label in normalized_message
            ):

                explicitly_mentioned_fields.add(
                    field
                )
                continue

            # Individual words from field label
            label_tokens = [
                token
                for token in label.split()
                if len(token) >= 3
            ]

            if label_tokens:

                if all(
                    token in normalized_tokens
                    for token in label_tokens
                ):

                    explicitly_mentioned_fields.add(
                        field
                    )

        # -----------------------------------------------------
        # Determine user-queryable fields dynamically
        # -----------------------------------------------------

        user_queryable_fields = set()

        if self.database_layer:

            try:

                queryable_fields = (
                    self.database_layer
                    .get_user_queryable_fields()
                )

                if isinstance(
                    queryable_fields,
                    list
                ):

                    for field in queryable_fields:

                        if isinstance(
                            field,
                            dict
                        ):

                            canonical = (
                                field.get(
                                    "canonical_field"
                                )
                            )

                            if canonical:
                                user_queryable_fields.add(
                                    canonical
                                )

                        else:

                            user_queryable_fields.add(
                                str(field)
                            )

            except Exception:

                pass
        
        # -----------------------------------------------------
        # Determine identifier fields dynamically
        # -----------------------------------------------------
        identifier_fields = set()

        if self.database_layer:

            try:

                identifier_fields_list = (
                    self.database_layer
                    .get_identifier_fields()
                )

                if isinstance(
                    identifier_fields_list,
                    list
                ):

                    for field in identifier_fields_list:

                        if isinstance(field, dict):

                            canonical = (
                                field.get(
                                    "canonical_field"
                                )
                            )

                            if canonical:
                                identifier_fields.add(
                                    canonical
                                )

                        else:

                            identifier_fields.add(
                                str(field)
                            )

            except Exception:

                identifier_fields = set()
            

        # -----------------------------------------------------
        # Final filtering
        # -----------------------------------------------------

        filtered_data = {}

        for field, value in extracted_data.items():

            if value is None:
                continue

            value_text = normalize(
                value
            )

            if not value_text:
                continue

            # -------------------------------------------------
            # CASE 1
            #
            # User explicitly mentioned this field.
            #
            # This is the strongest evidence.
            #
            # Therefore even fields normally not asked by the
            # AI can be accepted when the user explicitly gives
            # the field.
            #
            # Example:
            #
            # "part number ABC123"
            # "fenner XYZ"
            # "id 12345"
            # -------------------------------------------------

            if field in explicitly_mentioned_fields:

                # Make sure the value itself occurs after
                # normalizing the complete message.
                #
                # This prevents accepting a completely unrelated
                # Qwen-generated value merely because the field
                # label exists.
                normalized_value = re.sub(r"[^a-z0-9\s]", " ", str(value_text).lower())
                normalized_value = re.sub(r"\s+", " ", normalized_value).strip()

                value_tokens = normalized_value.split()

                if (
                    normalized_value == normalized_message
                    or all(token in message_tokens for token in value_tokens)
                ):

                    filtered_data[field] = value
                    continue

            # -------------------------------------------------
            # CASE 2
            #
            # Normal user-queryable fields.
            #
            # Example:
            #
            # "Ford Ka 2004"
            #
            # OEM = Ford
            # Model = Ka
            # Year = 2004
            #
            # These are allowed when the actual value exists
            # in the user's message.
            # -------------------------------------------------

            if (
                field in user_queryable_fields
                or field in identifier_fields
            ):

                value_tokens = value_text.split()

                if (
                    value_text == normalized_message
                    or all(
                        token in message_tokens
                        for token in value_tokens
                    )
                ):
                    filtered_data[field] = value
                    continue

            # -------------------------------------------------
            # CASE 3
            #
            # User abbreviation / spelling variation.
            #
            # Resolve against REAL DATABASE CANDIDATES.
            #
            # IMPORTANT:
            #
            # We DO NOT pass candidates=[value].
            #
            # Instead, we get the complete candidate list from
            # the database and let entity_normalizer determine
            # whether the user's token really maps to this value.
            # -------------------------------------------------

            if field in user_queryable_fields:

                try:

                    from backend.normalization.entity_normalizer import (
                        resolve_entity
                    )

                    field_candidates = []

                    if self.database_layer:

                        try:

                            field_candidates = (
                                self.database_layer
                                .get_unique_values(
                                    field
                                )
                            )

                        except Exception:

                            field_candidates = []

                    if field_candidates:

                        message_tokens = [
                            token
                            for token
                            in normalized_message.split()
                            if len(token) >= 2
                        ]

                        for token in message_tokens:

                            result = resolve_entity(
                                user_value=token,
                                candidates=field_candidates,
                                entity_type=field
                            )

                            if (
                                result.get(
                                    "status"
                                ) == "resolved"
                                and normalize(
                                    result.get(
                                        "matched_value"
                                    )
                                )
                                == value_text
                            ):

                                filtered_data[field] = value
                                break

                        if field in filtered_data:
                            continue

                except Exception:
                    pass

            # -------------------------------------------------
            # NO USER EVIDENCE
            #
            # Drop Qwen / DB generated value.
            # -------------------------------------------------

        return filtered_data
    # =========================================================
    # PROCESS MESSAGE
    # =========================================================

    def process_message(
        self,
        user_message
    ):
        # =========================================================
        # DISPLAY FORMAT SELECTION
        # =========================================================
        #
        # If the previous response asked the user whether they
        # want Card or Table format, handle that selection here.
        #
        # This must happen before catalog extraction so that
        # "Card" / "Table" are never treated as catalog values.
        # =========================================================

        if self.display_format_pending:

            selected_format = (
                str(user_message or "")
                .strip()
                .lower()
            )

            if selected_format == "card":

                self.display_format = "card"
                self.display_format_pending = False

                display_records = (
                    self.pending_display_records
                )

                self.pending_display_records = []

                frontend_records = (
                    FrontendMapper.map_records(
                        display_records
                    )
                )

                return {
                    "user_message": user_message,

                    "extracted_data": {},

                    "resolved_data": {},

                    "resolution_details": {},

                    "conversation_state": (
                        self.state.get_all()
                        if self.state
                        else {}
                    ),

                    "matching_records": display_records,

                    "frontend_records": frontend_records,

                    "result": {
                        "action": "show_products",
                        "status": "found",
                        "field": None,
                        "question": "",
                        "message": (
                            "Sure, I'll show the "
                            "product details as cards."
                        ),
                        "options": [],
                        "records_found": len(
                            display_records
                        ),
                        "records": display_records,
                        "presentation_format": "card",
                        "frontend_records": frontend_records
                    }
                }

            elif selected_format == "table":

                self.display_format = "table"
                self.display_format_pending = False

                display_records = (
                    self.pending_display_records
                )

                self.pending_display_records = []

                frontend_records = (
                    FrontendMapper.map_records(
                        display_records
                    )
                )

                return {
                    "user_message": user_message,

                    "extracted_data": {},

                    "resolved_data": {},

                    "resolution_details": {},

                    "conversation_state": (
                        self.state.get_all()
                        if self.state
                        else {}
                    ),

                    "matching_records": display_records,

                    "frontend_records": frontend_records,

                    "result": {
                        "action": "show_products",
                        "status": "found",
                        "field": None,
                        "question": "",
                        "message": (
                            "Sure, I'll show the "
                            "product details in a table."
                        ),
                        "options": [],
                        "records_found": len(
                            display_records
                        ),
                        "records": display_records,
                        "presentation_format": "table",
                        "frontend_records": frontend_records
                    }
                }

            # ---------------------------------------------------------
            # Invalid format input
            # ---------------------------------------------------------

            else:

                return {
                    "user_message": user_message,

                    "result": {
                        "action": "choose_display_format",
                        "status": "waiting",
                        "field": None,
                        "question": "",
                        "message": (
                            "Please choose either Card "
                            "or Table format."
                        ),
                        "options": [
                            "Card",
                            "Table"
                        ],
                        "records_found": len(
                            self.pending_display_records
                        ),
                        "records": [],
                        "frontend_records": []
                    }
                }
        # =========================================================
        # INITIAL MESSAGE UNDERSTANDING
        # =========================================================
        #
        # Only run this when a conversation has not started yet.
        #
        # Existing questioning / catalog flow is NOT changed.
        # =========================================================

        if (
            self.state is None
            and self.last_question_field is None
        ):

            understanding = (
                understand_initial_message(
                    user_message=user_message
                )
            )

            intent = understanding.get(
                "intent",
                "CATALOG_QUERY"
            )

            # -----------------------------------------------------
            # GREETING ONLY
            # -----------------------------------------------------

            if intent == "GREETING_ONLY":

                greeting_response = (
                    understanding.get(
                        "greeting_response",
                        ""
                    )
                )

                if not greeting_response:
                    greeting_response = (
                        "Hi! How can I help you today?"
                    )

                return {
                    "result": {
                        "action": "greeting",
                        "status": "greeting",
                        "field": None,
                        "question": "",
                        "message": greeting_response,
                        "options": [],
                        "records_found": 0,
                        "records": [],
                        "frontend_records": []
                    }
                }

        # =========================================================
        # EXISTING CATALOG FLOW STARTS HERE
        # =========================================================
        # -----------------------------------------------------
        # 1. GET AVAILABLE FIELDS
        # -----------------------------------------------------

        available_fields = []

        if self.database_layer:

            available_fields = (
                self.database_layer
                .get_available_fields()
            )

        # -----------------------------------------------------
        # 2. CREATE MEMORY
        # -----------------------------------------------------

        if self.state is None:

            self.state = ConversationState(
                available_fields=available_fields
            )

        # -----------------------------------------------------
        # 3. PREVIOUS QUESTION CONTEXT GATE
        # -----------------------------------------------------
        #
        # If the AI has already asked a question and the user
        # is answering that question, only that answer is accepted.
        #
        # IMPORTANT:
        #
        # In this case:
        # - Do NOT run broad Qwen extraction
        # - Do NOT discover unrelated entities from the DB
        # - Do NOT infer missing OEM/model/engine/year/etc.
        #
        # Only the value answering the previous question is used.
        # -----------------------------------------------------

        contextual_answer = (
            self._resolve_previous_question_answer(
                user_message
            )
        )

        if contextual_answer:

            # User answered the previous AI question.
            # Accept ONLY that answer.

            extracted_data = contextual_answer

        else:

            # -------------------------------------------------
            # No active previous-question answer.
            #
            # This is a normal/new user message, so keep the
            # existing Qwen + database discovery flow.
            # -------------------------------------------------

            extracted_query = extract_catalog_query(
                user_message=user_message,
                available_fields=available_fields
            )

            if isinstance(
                extracted_query,
                dict
            ):
              
                extracted_data = (
                    extracted_query.get(
                        "extracted_data",
                        extracted_query
                    )
                )

            else:

                if hasattr(
                    extracted_query,
                    "model_dump"
                ):

                    extracted_data = (
                        extracted_query.model_dump()
                    )

                else:

                    extracted_data = dict(
                        extracted_query
                    )
            # -------------------------------------------------
            # DEBUG QWEN EXTRACTION
            # -------------------------------------------------

            print(
                "DEBUG QWEN extracted_data:",
                extracted_data
            )

            # -------------------------------------------------
            # DISCOVER ENTITIES MISSED BY QWEN
            # -------------------------------------------------

            extracted_data = (
                discover_missing_entities(
                    user_message=user_message,
                    extracted_data=extracted_data,
                    database_layer=self.database_layer
                )
            )
 
            # -------------------------------------------------
            # DEBUG AFTER DATABASE DISCOVERY
            # -------------------------------------------------

            print(
                "DEBUG AFTER DISCOVERY:",
                extracted_data
            )

            # -------------------------------------------------
            # FINAL USER EVIDENCE GATE
            # -------------------------------------------------
            #
            # After Qwen + DB discovery, keep only values that
            # are actually supported by the current user message.
            #
            # This prevents DB-derived ID/Fenner/etc. values from
            # being added to the conversation state when the user
            # never supplied them.
            # -------------------------------------------------

            extracted_data = (
                self._filter_user_evidence(
                    user_message=user_message,
                    extracted_data=extracted_data
                )
            )
        # -----------------------------------------------------
        # 5. BUILD FILTERS USING MEMORY + NEW MESSAGE
        # -----------------------------------------------------

        previous_state = (
            self._get_active_filters()
        )

        combined_filters = (
            previous_state.copy()
        )

        combined_filters.update(
            extracted_data
        )

        # -----------------------------------------------------
        # 6. GET DATABASE CANDIDATES
        # -----------------------------------------------------

        candidates = {}

        if self.database_layer:

            candidates = (
                self.database_layer
                .get_entity_candidates(
                    combined_filters
                )
            )

        # -----------------------------------------------------
        # 7. RESOLVE NEW ENTITIES
        # -----------------------------------------------------

        resolved_result = (
            resolve_extracted_entities(
                extracted_data=extracted_data,
                candidates=candidates
            )
        )

        resolved_data = (
            resolved_result.get(
                "resolved_data",
                {}
            )
        )

        resolution_details = (
            resolved_result.get(
                "resolution_details",
                {}
            )
        )

        # -----------------------------------------------------
        # 8. UPDATE MEMORY
        # -----------------------------------------------------

        self.state.update(
            resolved_data
        )

        current_state = (
            self.state.get_all()
        )

        # -----------------------------------------------------
        # 9. SEARCH DATABASE USING COMPLETE MEMORY
        # -----------------------------------------------------

        active_filters = {
            field: value
            for field, value
            in current_state.items()
            if value is not None
            and str(value).strip() != ""
        }

        matching_records = []

        if self.database_layer:

            matching_records = ( self.database_layer .get_matching_records( active_filters)) 
            print("DEBUG matching_records:", len(matching_records))
       
        # -----------------------------------------------------
        # FALLBACK SEARCH
        # -----------------------------------------------------

        fallback_records = []
        fallback_level = None
        
        print("DEBUG: BEFORE FALLBACK")

        if (
            self.database_layer
            and not matching_records
        ):
            print("DEBUG: CALLING get_fallback_records()")

            fallback_result = (self.database_layer.get_fallback_records(active_filters))
            
            print("DEBUG: fallback_result:", fallback_result)
            
            if isinstance(fallback_result,dict):
                fallback_records = (fallback_result.get("records",[]))
                fallback_level = (fallback_result.get( "fallback_level"))
        
        print("DEBUG: AFTER FALLBACK")
        print("DEBUG fallback_level:", fallback_level)
        print("DEBUG fallback_records:", len(fallback_records))
                        
        print("\nDEBUG extracted_data:", extracted_data)
        print("DEBUG resolved_data:", resolved_data)
        print("DEBUG conversation_state:", current_state)
        print("DEBUG active_filters:", active_filters)
        print("DEBUG matching_records:", len(matching_records))

        # -----------------------------------------------------
        # 10. AI DECIDES NEXT ACTION
        # -----------------------------------------------------

        print("DEBUG: BEFORE QUESTION ENGINE")

        # -----------------------------------------------------
        # DETERMINE ACTIVE IDENTIFIER FIELDS
        # -----------------------------------------------------

        identifier_fields = set()

        if self.database_layer:

            try:

                identifier_fields_list = (
                    self.database_layer
                    .get_identifier_fields()
                )

                if isinstance(
                    identifier_fields_list,
                    list
                ):

                    for field in identifier_fields_list:

                        if isinstance(field, dict):

                            canonical = (
                                field.get(
                                    "canonical_field"
                                )
                            )

                            if canonical:
                                identifier_fields.add(
                                    canonical
                                )

                        else:

                            identifier_fields.add(
                                str(field).strip()
                            )

            except Exception:

                identifier_fields = set()


        # -----------------------------------------------------
        # CHECK WHETHER CURRENT SEARCH HAS AN IDENTIFIER
        # -----------------------------------------------------

        has_active_identifier = any(
            field in identifier_fields
            and value is not None
            and str(value).strip() != ""
            for field, value
            in active_filters.items()
        )

        print(
            "DEBUG identifier_fields:",
            identifier_fields
        )

        print(
            "DEBUG has_active_identifier:",
            has_active_identifier
        )

        print(
            "DEBUG part_number_narrowing:",
            self.part_number_narrowing
        )

        # =====================================================
        # PART NUMBER THRESHOLD / NARROWING LOGIC
        # =====================================================

        # The <=10 / >10 rule is checked only when the
        # Part Number search starts.
        #
        # Once narrowing starts:
        # - Do NOT apply the <=10 shortcut again.
        # - Continue DynamicQuestionEngine while useful
        #   differences exist.
        # - If only one record remains -> show_product.
        # - If multiple records remain but all useful
        #   fields are identical -> DynamicQuestionEngine
        #   will return show_products.

        if (
            has_active_identifier
            and not self.part_number_narrowing
        ):

            initial_count = len(
                matching_records
            )

            print(
                "DEBUG INITIAL PART NUMBER COUNT:",
                initial_count
            )

            # -------------------------------------------------
            # NO RECORDS
            # -------------------------------------------------

            if initial_count == 0:

                engine_result = (
                    self.question_engine.analyze(
                        conversation_state=current_state,
                        matching_records=matching_records,
                        fallback_records=fallback_records,
                        fallback_level=fallback_level
                    )
                )

            # -------------------------------------------------
            # INITIAL RESULT <= 10
            #
            # Show ALL matching records.
            #
            # Do NOT ask unnecessary questions.
            # -------------------------------------------------

            elif initial_count <= 10:

                print(
                    "DEBUG INITIAL PART NUMBER <= 10 "
                    "-> SHOW ALL RECORDS"
                )

                engine_result = {
                    "action": "show_products",
                    "status": "found",
                    "field": None,
                    "question": "",
                    "options": [],
                    "message": (
                        "I found the matching "
                        "product details."
                    ),
                    "records_found": initial_count,
                    "records": matching_records
                }

            # -------------------------------------------------
            # INITIAL RESULT > 10
            #
            # Start narrowing.
            # -------------------------------------------------

            else:

                print(
                    "DEBUG INITIAL PART NUMBER > 10 "
                    "-> START NARROWING"
                )

                self.part_number_narrowing = True

                engine_result = (
                    self.question_engine.analyze(
                        conversation_state=current_state,
                        matching_records=matching_records,
                        fallback_records=fallback_records,
                        fallback_level=fallback_level
                    )
                )


        # =====================================================
        # CONTINUE PART NUMBER NARROWING
        # =====================================================

        elif (
            has_active_identifier
            and self.part_number_narrowing
        ):

            current_count = len(
                matching_records
            )

            print(
                "DEBUG PART NUMBER NARROWING COUNT:",
                current_count
            )

            # -------------------------------------------------
            # ONE RECORD
            #
            # Unique product found.
            # -------------------------------------------------

            if current_count == 1:

                print(
                    "DEBUG PART NUMBER UNIQUE "
                    "-> FINAL ANSWER"
                )

                engine_result = {
                    "action": "show_product",
                    "status": "found",
                    "field": None,
                    "question": "",
                    "options": [],
                    "message": (
                        "I found the matching "
                        "product details."
                    ),
                    "records_found": 1,
                    "records": matching_records
                }

                self.part_number_narrowing = False

            # -------------------------------------------------
            # MULTIPLE RECORDS
            #
            # IMPORTANT:
            #
            # Even if count becomes <= 10, DO NOT directly
            # show them.
            #
            # DynamicQuestionEngine checks whether there are
            # still useful differences:
            #
            # OEM
            # Model
            # Engine
            # Year
            # Product
            # Category
            #
            # If a useful difference exists:
            #     ASK_QUESTION
            #
            # If all are identical:
            #     SHOW_PRODUCTS
            # -------------------------------------------------

            elif current_count > 1:

                print(
                    "DEBUG PART NUMBER NARROWING "
                    "-> CONTINUE DYNAMIC QUESTIONS"
                )

                engine_result = (
                    self.question_engine.analyze(
                        conversation_state=current_state,
                        matching_records=matching_records,
                        fallback_records=fallback_records,
                        fallback_level=fallback_level
                    )
                )

            # -------------------------------------------------
            # ZERO RECORDS
            # -------------------------------------------------

            else:

                engine_result = (
                    self.question_engine.analyze(
                        conversation_state=current_state,
                        matching_records=matching_records,
                        fallback_records=fallback_records,
                        fallback_level=fallback_level
                    )
                )


        # =====================================================
        # NORMAL CATALOG FLOW
        # =====================================================
        #
        # OEM / Model / Engine / Product / Year / Category
        # continue using the existing DynamicQuestionEngine.
        #
        # No threshold is applied here.
        # =====================================================

        else:

            engine_result = (
                self.question_engine.analyze(
                    conversation_state=current_state,
                    matching_records=matching_records,
                    fallback_records=fallback_records,
                    fallback_level=fallback_level
                )
            )
            
        # -----------------------------------------------------
        # 11. REMEMBER QUESTION CONTEXT
        # -----------------------------------------------------

        if (
            engine_result.get(
                "action"
            ) == "ask_question"
        ):

            self.last_question_field = (
                engine_result.get(
                    "field"
                )
            )

            self.last_question_options = (
                engine_result.get(
                    "options",
                    []
                )
            )

        else:

            self.last_question_field = None
            self.last_question_options = []
            
        # -----------------------------------------------------
        # 12. PREPARE PRODUCT DISPLAY FORMAT
        # -----------------------------------------------------
        #
        # Once the catalog flow has finished and products are
        # ready to display, ask the user how they want the
        # product details presented.
        #
        # IMPORTANT:
        # This does NOT affect:
        # - catalog extraction
        # - entity resolution
        # - database search
        # - DynamicQuestionEngine
        # - Part Number threshold logic
        #
        # It only controls presentation.
        # -----------------------------------------------------

        frontend_records = []

        if engine_result.get("action") in (
            "show_product",
            "show_products"
        ):

            display_records = (
                matching_records
                if matching_records
                else fallback_records
            )

            # -------------------------------------------------
            # Ask display format only when we have records.
            # -------------------------------------------------

            if display_records:

                # Store records temporarily until the user
                # selects Card or Table.

                self.pending_display_records = (
                    display_records
                )

                self.display_format_pending = True

                # -------------------------------------------------
                # Generate natural AI format question.
                # -------------------------------------------------

                format_question = (
                    generate_display_format_question(
                        records_count=len(
                            display_records
                        ),
                        conversation_context=(
                            user_message
                        )
                    )
                )

                engine_result = {
                    "action": "choose_display_format",
                    "status": "waiting",
                    "field": None,
                    "question": "",
                    "message": format_question,
                    "options": [
                        "Card",
                        "Table"
                    ],
                    "records_found": len(
                        display_records
                    ),
                    "records": [],
                    "presentation_format": None
                }

                # Do NOT send product records to the
                # frontend yet.
                frontend_records = []
        # -----------------------------------------------------
        # 12. RETURN RESPONSE
        # -----------------------------------------------------

        return {

            "user_message":
                user_message,

            "extracted_data":
                extracted_data,

            "resolved_data":
                resolved_data,

            "resolution_details":
                resolution_details,

            "conversation_state":
                current_state,

            "matching_records":
                matching_records,
                
            "frontend_records":
                frontend_records,

            "result":
                engine_result
        }

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        if self.state:

            self.state.reset()

        self.last_question_field = None
        self.last_question_options = []
        self.part_number_narrowing = False
        
        self.display_format = None
        self.display_format_pending = False
        self.pending_display_records = []

        return (
            self.state.get_all()
            if self.state
            else {}
        )