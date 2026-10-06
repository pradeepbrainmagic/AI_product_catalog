import json
from collections import Counter

from ollama import chat


MODEL_NAME = "qwen2.5:7b"


class DynamicQuestionEngine:
    """
    Database-driven conversation decision engine.

    Main principle:

        DATABASE decides WHAT is needed.
        AI decides HOW to ask.

    The AI is NOT allowed to invent:
        - values
        - vehicle information
        - years
        - engine names
        - product names
        - arbitrary context

    No fixed field sequence.
    No fixed question templates.
    No hardcoded catalog values.
    """

    def __init__(
        self,
        database_layer,
        model_name=MODEL_NAME
    ):

        self.database_layer = database_layer
        self.model_name = model_name

    # =========================================================
    # NORMALIZE VALUE
    # =========================================================

    @staticmethod
    def _normalize(value):

        if value is None:
            return ""

        return str(value).strip().lower()

    # =========================================================
    # GET ACTIVE FIELDS
    # =========================================================

    def _get_active_fields(
        self,
        conversation_state
    ):

        active = {}

        for field, value in conversation_state.items():

            if value is None:
                continue

            if str(value).strip() == "":
                continue

            active[field] = value

        return active

    # =========================================================
    # GET MISSING FIELDS
    # =========================================================

    def _get_missing_fields(
        self,
        conversation_state,
        available_fields
    ):
        """
        Return only fields that are:

        1. Supported by the current database.
        2. Allowed to be requested from the user.
        3. Not already present in conversation state.

        The decision about whether a field can be
        requested comes from database metadata.

        No field names are hardcoded here.
        """

        if not self.database_layer:
            return []

        # -----------------------------------------------------
        # Fields that AI is allowed to ask the user
        # -----------------------------------------------------

        user_queryable_fields = (
            self.database_layer.get_questionable_fields()
        )
        print(
            "DEBUG QUESTIONABLE FIELDS:",
            user_queryable_fields
        )

        print(
            "DEBUG CONVERSATION STATE:",
            conversation_state
        )

        missing = []

        for field in user_queryable_fields:

            value = conversation_state.get(field)

            if value is None:

                missing.append(field)

            elif str(value).strip() == "":

                missing.append(field)

        return missing

    # =========================================================
    # REMOVE REDUNDANT FIELDS
    # =========================================================

    def _remove_redundant_fields(
        self,
        conversation_state,
        matching_records,
        fields
    ):
        """
        Remove fields that do not actually help
        distinguish the current matching records.

        Example:

            124 Escape records

            category:
                Passenger Car

            product:
                Serpentine
                V-Ribbed Belt
                ...

        Product may distinguish the records.

        Category may not.

        Therefore category should not be asked
        merely because it exists in the schema.
        """

        useful_fields = []

        if not matching_records:
            return useful_fields

        for field in fields:

            # ---------------------------------------------
            # Already known -> never ask
            # ---------------------------------------------

            if conversation_state.get(field) is not None:
                continue

            values = set()

            for record in matching_records:

                value = record.get(field)

                if value is None:
                    continue

                if str(value).strip() == "":
                    continue

                values.add(
                    self._normalize(value)
                )

            # ---------------------------------------------
            # No information in this field
            # ---------------------------------------------
            print(
                "DEBUG FIELD CHECK:",
                field,
                "DISTINCT VALUES:",
                len(values),
                values
            )
            
            if len(values) == 0:
                continue

            # ---------------------------------------------
            # One unique value does NOT help distinguish
            # records.
            # ---------------------------------------------

            if len(values) == 1:
                continue

            useful_fields.append(
                (
                    field,
                    len(values)
                )
            )

        # -------------------------------------------------
        # Prefer fields with fewer distinct values.
        #
        # Why?
        #
        # If:
        #
        # engine -> 2 values
        # product -> 15 values
        #
        # engine is a better discriminator.
        # -------------------------------------------------

        useful_fields.sort(
            key=lambda item: item[1]
        )

        return [
            field
            for field, _ in useful_fields
        ]

    # =========================================================
    # GET FIELD OPTIONS
    # =========================================================

    def _get_field_options(
        self,
        field,
        matching_records
    ):

        values = []

        seen = set()

        for record in matching_records:

            value = record.get(field)

            if value is None:
                continue

            value_text = str(value).strip()

            if not value_text:
                continue

            normalized = (
                self._normalize(value_text)
            )

            if normalized in seen:
                continue

            seen.add(normalized)

            values.append(value)

        return sorted(
            values,
            key=lambda value: str(value)
        )

    # =========================================================
    # CALCULATE FIELD INFORMATION
    # =========================================================
    def _build_field_analysis(
        self,
        conversation_state,
        matching_records,
        available_fields
    ):
        """
        Determine which missing fields actually
        contain useful information.
        """

        missing_fields = (
            self._get_missing_fields(
                conversation_state,
                available_fields
            )
        )
        print(
            "DEBUG MISSING FIELDS:",
            missing_fields
        )

        useful_fields = (
            self._remove_redundant_fields(
                conversation_state,
                matching_records,
                missing_fields
            )
        )
        print(
            "DEBUG USEFUL FIELDS:",
            useful_fields
        )

        analysis = []

        for field in useful_fields:

            options = self._get_field_options(
                field,
                matching_records
            )
            
            print(
                "DEBUG FIELD OPTIONS:",
                field,
                options
            )

            if not options:
                continue

            analysis.append(
                {
                    "field": field,
                    "option_count": len(options),
                    "options": options
                }
            )

        return analysis

    # =========================================================
    # BUILD AI PROMPT
    # =========================================================

    def _build_prompt(
        self,
        conversation_state,
        matching_records,
        available_fields,
        field_analysis,
        fallback_records=None,
        fallback_level=None
    ):
        fallback_records = (
            fallback_records or []
        )

        fallback_level = (
            fallback_level or None
        )
        
        state_text = json.dumps(
            conversation_state,
            indent=2,
            default=str
        )

        fields_text = json.dumps(
            available_fields,
            indent=2
        )

        analysis_text = json.dumps(
            field_analysis,
            indent=2,
            default=str
        )

        # -----------------------------------------------------
        # IMPORTANT
        #
        # Do NOT send all 100 records to Qwen.
        #
        # Engine has already analyzed the records.
        # AI only needs the useful field/options.
        # -----------------------------------------------------

        return f"""
You are the natural-language conversation layer
for a generic product catalog.

The database and application code have already
determined which information is useful.

Your job is ONLY to formulate the response naturally.

==================================================
CURRENT CONVERSATION STATE
==================================================

{state_text}

==================================================
AVAILABLE CANONICAL FIELDS
==================================================

{fields_text}

==================================================
DATABASE-DETERMINED NEXT FIELD OPTIONS
==================================================

{analysis_text}

==================================================
FALLBACK CATALOG INFORMATION
==================================================

Fallback level:
{fallback_level}

Fallback records:

{json.dumps(
    fallback_records,
    indent=2,
    default=str
)}

==================================================
FALLBACK RESPONSE RULES
==================================================

If fallback catalog information is present:

1. Clearly explain that the user's exact requested
   combination was not found.

2. If fallback level is:

   same_year_other_products

   Explain that the requested product is not
   available for the requested year, but other
   products are available for the same vehicle
   and same year.

3. If fallback level is:

   same_model_other_years

   Explain that the requested product is not
   available for the requested year, and show
   other products available for the same vehicle
   in other years.

4. Use ONLY the supplied fallback records.

5. Do NOT invent products.

6. Do NOT invent years.

7. Do NOT claim that a product from another year
   matches the requested year.

8. Do NOT invent compatibility.

9. Do NOT add products that are not present in the
   fallback records.

10. Keep the response natural and concise.

==================================================
STRICT RULES
==================================================

1. NEVER invent a database value.

2. NEVER invent a year.

3. NEVER invent an engine.

4. NEVER invent an OEM.

5. NEVER invent a model.

6. NEVER invent a product.

7. NEVER assume information that is not present
   in CURRENT CONVERSATION STATE.

8. NEVER ask for a field that already has a value.

9. ONLY ask about the field supplied by
   DATABASE-DETERMINED NEXT FIELD OPTIONS.

10. ONLY use options supplied by the database.

11. Do not add extra options.

12. Do not mention an unrelated field.

13. Do not assume a fixed sequence such as:

       OEM -> model -> year -> engine

14. The database determines the next field.

15. You determine only the natural wording.

16. If there is exactly one database record,
    return SHOW_PRODUCT.

17. If there are multiple records but no useful
    missing field can distinguish them,
    return SHOW_PRODUCTS.

18. If there are zero records,
    return NOT_FOUND.

==================================================
NATURAL CONVERSATIONAL AI BEHAVIOR
==================================================

You are a natural conversational AI assistant.

Your response must feel like a real conversation with
an intelligent assistant such as ChatGPT or Gemini.

Do NOT use a fixed response pattern.

Do NOT repeatedly start responses with phrases such as:

"I found several matches..."
"I found multiple matches..."
"I found several matches for the part number..."

These are only examples of possible wording.
They are NOT templates.

Every response must be generated based on the
CURRENT CONVERSATION STATE, the user's latest input,
and the DATABASE-DETERMINED INFORMATION.

==================================================
CONVERSATION AWARENESS
==================================================

First understand what the user has already told you.

Use the CURRENT CONVERSATION STATE as the source of
previously established information.

If previous information is relevant to the current
question, naturally refer to it.

If it is not relevant, do not mention it.

Do not repeat information unnecessarily.

Do not mention a part number simply because one exists
in the conversation state.

Do not mention OEM, model, engine, year, product,
category, or any other field unless it is useful to
the current conversation.

Never invent information.

Only use values present in the CURRENT CONVERSATION STATE
or supplied by the DATABASE-DETERMINED NEXT FIELD OPTIONS.

==================================================
UNDERSTAND THE USER'S INTENT
==================================================

Respond according to what the user is currently trying
to accomplish.

Consider:

- what the user just said
- what information is already known
- what information is still missing
- what the database found
- what information the database says is useful next

Do not blindly follow a predefined conversational sequence.

The conversation may begin with any field.

The user may provide one field, several fields, an
abbreviation, a correction, or a follow-up answer.

Adapt naturally to the current situation.

==================================================
DATABASE CONTROLS THE INFORMATION
==================================================

The database/application has already determined:

- whether more information is needed
- which field should be asked next
- which values are valid options

You must NOT change that decision.

You must NOT ask about another field.

You must NOT create additional options.

Your responsibility is only to communicate the
database decision naturally.

==================================================
NATURAL QUESTION GENERATION
==================================================

When multiple records remain and the database provides
a next field:

Generate ONE natural conversational question.

The question should feel appropriate to the current
conversation rather than following a reusable template.

You may:

- acknowledge the user's previous answer
- briefly describe what has been narrowed down
- explain why the next information is useful
- directly ask the next question

Choose whichever style sounds most natural for the
current situation.

Do not always use an introductory sentence.

Sometimes a direct question is more natural.

Sometimes a short acknowledgement followed by a
question is more natural.

Sometimes a brief explanation followed by a question
is more natural.

Decide based on the current conversation.

==================================================
MESSAGE AND QUESTION
==================================================

"message" and "question" serve different purposes.

MESSAGE:
A short conversational response or context.

QUESTION:
The actual question that asks for the
DATABASE-DETERMINED NEXT FIELD.

The message must NOT simply repeat the question.

The message is optional in natural conversation,
but when present it must add useful conversational
context.

Do not force a message merely to follow a template.

If a short natural acknowledgement is appropriate,
use one.

If the question itself is sufficient, keep the
message concise.

==================================================
EXAMPLES OF BEHAVIOR
==================================================

These examples demonstrate behavior only.
Do NOT copy their wording literally.

Example 1:

Current state:
OEM = Ford

Database next field:
Year

Natural response could be:

message:
"I have the Ford matches narrowed down."

question:
"Which year is your vehicle?"

--------------------------------------------------

Example 2:

Current state:
OEM = Ford
Year = 2004

Database next field:
Model

Natural response could be:

message:
"That helps narrow it down."

question:
"Which model are you looking for?"

--------------------------------------------------

Example 3:

Current state:
OEM = Toyota
Model = 4 Runner
Product = Serpentine

Database next field:
Year

Natural response could be:

message:
"Got it — we're looking at the Serpentine options
for the Toyota 4 Runner."

question:
"Which year do you need?"

--------------------------------------------------

Example 4:

Current state:
Part Number = 6PK2240
Product = Serpentine
OEM = Toyota
Model = 4 Runner

Database next field:
Year

Natural response could be:

message:
"The Serpentine match for your Toyota 4 Runner is
almost narrowed down."

question:
"Which year should I check?"

--------------------------------------------------

Example 5:

The user provides several details in one message.

Do not artificially repeat every detail.

Use only the information that makes the next
question clearer.

--------------------------------------------------

Example 6:

If the current context is already obvious, a direct
question is acceptable:

message:
""

question:
"Which year are you looking for?"

Do not add unnecessary filler.

==================================================
IMPORTANT
==================================================

The examples above are NOT templates.

Do not repeatedly use:

"I found several matches..."
"To narrow it down..."
"Which ... are you looking for?"

unless that wording genuinely fits the current
conversation.

Think about the conversation first, then formulate
the response.

The response should feel generated specifically for
this user and this turn.

Never invent facts merely to make the conversation
sound natural.

Naturalness must come from the available context,
not from invented information.

Ask ONLY ONE question.

The question MUST correspond to the database-selected
field.

Use ONLY database-provided options.

==================================================
JSON OUTPUT
==================================================

For ASK_QUESTION:

{{
    "action": "ASK_QUESTION",
    "field": "actual_database_selected_field",
    "question": "naturally generated question",
    "options": ["actual database values"],
    "message": "short natural conversational context",
    "records": []
}}

==================================================
JSON ONLY
==================================================

For a question:

{{
    "action": "ASK_QUESTION",
    "field": "actual_field",
    "question": "natural question",
    "options": ["actual database values"],
    "message": "A short, natural explanation of what was found and why the user is being asked this question.",
    "records": []
}}

IMPORTANT FOR ASK_QUESTION:

- "message" MUST NOT be empty.
- "message" must contain a short, natural conversational explanation.
- The message should use only facts available from the conversation state and database-provided options.
- The message should explain that multiple matches were found when multiple records remain.
- The message should naturally lead into the question.
- Do NOT simply repeat the question inside the message.
- Do NOT invent any catalog information.
- Do NOT mention values that are not provided by the database.

For one result:

{{
    "action": "SHOW_PRODUCT",
    "field": null,
    "question": "",
    "options": [],
    "message": "natural response",
    "records": []
}}

For multiple results:

{{
    "action": "SHOW_PRODUCTS",
    "field": null,
    "question": "",
    "options": [],
    "message": "natural response",
    "records": []
}}

For no result:

{{
    "action": "NOT_FOUND",
    "field": null,
    "question": "",
    "options": [],
    "message": "natural response",
    "records": []
}}
"""

    # =========================================================
    # ANALYZE
    # =========================================================

    def analyze(
        self,
        conversation_state,
        matching_records=None,
        fallback_records=None,
        fallback_level=None
    ):

        matching_records = (
            matching_records or []
        )
        fallback_records = (
            fallback_records or []
        )

        fallback_level = (
            fallback_level or None
        )

        # -----------------------------------------------------
        # GET AVAILABLE FIELDS
        # -----------------------------------------------------

        available_fields = []

        if self.database_layer:

            available_fields = (
                self.database_layer
                .get_available_fields()
            )
        # =====================================================
        # CASE 1 — NO EXACT RECORDS
        # =====================================================

        if not matching_records:

            # -------------------------------------------------
            # NO FALLBACK
            #
            # Keep existing NOT_FOUND behaviour.
            # -------------------------------------------------

            if not fallback_records:

                return {
                    "action": "not_found",
                    "status": "not_found",
                    "field": None,
                    "question": "",
                    "options": [],
                    "message": (
                        "I couldn't find a matching "
                        "product in the catalog."
                    ),
                    "records_found": 0,
                    "records": []
                }

            # -------------------------------------------------
            # FALLBACK RECORDS EXIST
            #
            # Let Qwen formulate the natural response.
            # Python provides only factual DB records.
            # -------------------------------------------------

            fallback_prompt = self._build_prompt(
                conversation_state=conversation_state,
                matching_records=[],
                available_fields=available_fields,
                field_analysis=[],
                fallback_records=fallback_records,
                fallback_level=fallback_level
            )

            try:

                response = chat(
                     messages=[
                        {
                            "role": "system",
                            "content": fallback_prompt
                        }
                    ],
                    format="json",
                    options={
                        "temperature": 0.7
                    }
                )

                result = json.loads(
                    response.message.content
                )

                return {
                    "action": "show_products",
                    "status": "fallback_found",
                    "field": None,
                    "question": "",
                    "options": [],
                    "message": result.get(
                        "message",
                        "The requested product was not found, "
                        "but other products are available."
                    ),
                    "records_found": 0,
                    "fallback_records_found": len(
                        fallback_records
                    ),
                    "fallback_level": fallback_level,
                    "records": fallback_records,
                    "fallback": True
                }

            except Exception:

                # -------------------------------------------------
                # AI failure fallback
                #
                # Still return real DB records.
                # -------------------------------------------------

                if (
                    fallback_level
                    == "same_year_other_products"
                ):

                    message = (
                        "The requested product was not "
                        "found for the requested year, "
                        "but other products are available "
                        "for the same vehicle and year."
                    )

                else:

                    message = (
                        "The requested product was not "
                        "found for the requested year, "
                        "but other products are available "
                        "for the same vehicle."
                    )

                return {
                    "action": "show_products",
                    "status": "fallback_found",
                    "field": None,
                    "question": "",
                    "options": [],
                    "message": message,
                    "records_found": 0,
                    "fallback_records_found": len(
                        fallback_records
                    ),
                    "fallback_level": fallback_level,
                    "records": fallback_records,
                    "fallback": True
                }
        

        # =====================================================
        # CASE 2 — EXACTLY ONE RECORD
        # =====================================================

        if len(matching_records) == 1:

            return {
                "action": "show_product",
                "status": "found",
                "field": None,
                "question": "",
                "options": [],
                "message": (
                    "I found a matching product."
                ),
                "records_found": 1,
                "records": matching_records
            }

        # =====================================================
        # CASE 3 — MULTIPLE RECORDS
        # =====================================================

        field_analysis = (
            self._build_field_analysis(
                conversation_state=conversation_state,
                matching_records=matching_records,
                available_fields=available_fields
            )
        )

        # -----------------------------------------------------
        # No useful discriminator
        # -----------------------------------------------------

        if not field_analysis:

            return {
                "action": "show_products",
                "status": "found",
                "field": None,
                "question": "",
                "options": [],
                "message": (
                    "I found multiple matching "
                    "products."
                ),
                "records_found": len(
                    matching_records
                ),
                "records": matching_records
            }

        # -----------------------------------------------------
        # First field = strongest discriminator
        # -----------------------------------------------------

        selected = field_analysis[0]

        selected_field = (
            selected["field"]
        )

        selected_options = (
            selected["options"]
        )

        # -----------------------------------------------------
        # Send only selected information to Qwen
        # -----------------------------------------------------

        prompt = self._build_prompt(
            conversation_state=conversation_state,
            matching_records=matching_records,
            available_fields=available_fields,
            field_analysis=[
                selected
            ]
        )

        # =====================================================
        # CALL QWEN
        # =====================================================

        try:

            response = chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": prompt
                    }
                ],
                format="json",
                options={
                    "temperature": 0.7
                }
            )

            result = json.loads(
                response.message.content
            )
            print(
                "DEBUG QWEN QUESTION ENGINE RESULT:",
                result
            )

        except Exception:

            # -------------------------------------------------
            # Fallback without AI
            # -------------------------------------------------

            return {
                "action": "ask_question",
                "status": "needs_information",
                "field": selected_field,
                "question": (
                    f"Which {selected_field} "
                    f"are you looking for?"
                ),
                "options": selected_options,
                "records_found": len(
                    matching_records
                ),
                "records": []
            }

        # =====================================================
        # VALIDATE AI OUTPUT
        # =====================================================

        action = result.get(
            "action",
            "ASK_QUESTION"
        )

        # -----------------------------------------------------
        # DATABASE HAS ALREADY IDENTIFIED A USEFUL NEXT FIELD
        #
        # If multiple records still remain and a useful field
        # exists, the AI MUST ask the user instead of prematurely
        # showing all products.
        #
        # The AI controls HOW to ask.
        # Python/database controls WHETHER a question is needed.
        # -----------------------------------------------------

        if (
            len(matching_records) > 1
            and field_analysis
        ):

            action = "ASK_QUESTION"

            # ---------------------------------------------
            # AI is NOT allowed to change field
            # ---------------------------------------------

            field = selected_field

            question = result.get(
                "question"
            )

            if not question:

                question = (
                    f"Which {field} "
                    f"are you looking for?"
                )

            # ---------------------------------------------
            # AI is NOT allowed to invent options
            # ---------------------------------------------

            options = selected_options
            
            # ---------------------------------------------
            # AI natural conversational message
            #
            # Qwen decides HOW to communicate.
            # ---------------------------------------------

            message = result.get(
                "message",
                ""
            )

            return {
                "action": "ask_question",
                "status": "needs_information",
                "field": field,
                "question": question,
                "options": options,
                "message": message,
                "records_found": len(
                    matching_records
                ),
                "records": []
            }

        # =====================================================
        # SHOW PRODUCT
        # =====================================================

        if action == "SHOW_PRODUCT":

            return {
                "action": "show_product",
                "status": "found",
                "field": None,
                "question": "",
                "options": [],
                "message": result.get(
                    "message",
                    "I found the matching product."
                ),
                "records_found": len(
                    matching_records
                ),
                "records": matching_records
            }

        # =====================================================
        # SHOW PRODUCTS
        # =====================================================

        if action == "SHOW_PRODUCTS":

            return {
                "action": "show_products",
                "status": "found",
                "field": None,
                "question": "",
                "options": [],
                "message": result.get(
                    "message",
                    "I found multiple matching products."
                ),
                "records_found": len(
                    matching_records
                ),
                "records": matching_records
            }

        # =====================================================
        # UNKNOWN AI ACTION
        # =====================================================

        return {
            "action": "ask_question",
            "status": "needs_information",
            "field": selected_field,
            "question": (
                f"Which {selected_field} "
                f"are you looking for?"
            ),
            "options": selected_options,
            "records_found": len(
                matching_records
            ),
            "records": []
        }