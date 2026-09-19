from backend.database.schema_mapper import SchemaMapper


class DatabaseLayer:
    """
    Generic database access layer.

    Responsibilities:
    1. Read records from the database.
    2. Convert database records into canonical fields.
    3. Search using canonical fields.
    4. Dynamically discover available values.
    5. Read field behaviour from metadata.
    6. Provide candidate values to the conversation layer.

    IMPORTANT:

    This class does NOT hardcode:
        - OEM
        - model
        - year
        - engine
        - product
        - category
        - part number
        - any dataset-specific field

    Field behaviour is controlled by catalog_field_metadata.
    """

    def __init__(self, db_connection):

        self.connection = db_connection

    # =========================================================
    # TABLE NAME
    # =========================================================

    def _get_table_name(self):

        return SchemaMapper.get_table_name()

    # =========================================================
    # METADATA TABLE
    # =========================================================

    def _get_metadata_table_name(self):

        return SchemaMapper.get_metadata_table_name()

    # =========================================================
    # GET ALL DATABASE RECORDS
    # =========================================================

    def get_all_records(self):

        table_name = self._get_table_name()

        query = (
            f"SELECT * "
            f"FROM `{table_name}`"
        )

        cursor = self.connection.cursor(
            dictionary=True
        )

        try:

            cursor.execute(query)

            records = cursor.fetchall()

        finally:

            cursor.close()

        return records

    # =========================================================
    # GET ALL CANONICAL RECORDS
    # =========================================================

    def get_all_canonical_records(self):

        records = self.get_all_records()

        return SchemaMapper.map_records(records)

    # =========================================================
    # GET FIELD METADATA
    # =========================================================

    def get_field_metadata(self):

        """
        Read field behaviour dynamically from
        catalog_field_metadata.

        Example metadata:

            database_column
            canonical_field
            user_queryable
            searchable
            displayable
            identifier
        """

        metadata_table = (
            self._get_metadata_table_name()
        )

        query = (
            f"SELECT * "
            f"FROM `{metadata_table}`"
        )

        cursor = self.connection.cursor(
            dictionary=True
        )

        try:

            cursor.execute(query)

            rows = cursor.fetchall()

        finally:

            cursor.close()

        return rows

    # =========================================================
    # GET METADATA FOR ONE FIELD
    # =========================================================

    def get_field_metadata_for(
        self,
        canonical_field
    ):

        if not canonical_field:
            return None

        metadata = self.get_field_metadata()

        for row in metadata:

            if (
                row.get("canonical_field")
                == canonical_field
            ):

                return row

        return None

    # =========================================================
    # GET SEARCHABLE FIELDS
    # =========================================================

    def get_searchable_fields(self):

        """
        Return fields marked searchable=1.

        This is different from user_queryable.

        searchable:
            User can provide this field as input.

        user_queryable:
            AI is allowed to ASK the user for this field.
        """

        metadata = self.get_field_metadata()

        fields = []

        for row in metadata:

            canonical_field = (
                row.get("canonical_field")
            )

            searchable = (
                row.get("searchable")
            )

            if (
                canonical_field
                and searchable
            ):

                fields.append(
                    canonical_field
                )

        return fields

    # =========================================================
    # GET USER QUERYABLE FIELDS
    # =========================================================

    def get_user_queryable_fields(self):

        """
        Return fields that AI is allowed to ask
        the user to provide.

        Controlled completely by metadata.

        No field names are hardcoded.

        Therefore if metadata says:

            part_number -> user_queryable = 0

        AI will never ask:

            "What is the part number?"

        But part_number can still remain searchable.
        """

        metadata = self.get_field_metadata()

        fields = []

        for row in metadata:

            canonical_field = (
                row.get("canonical_field")
            )

            user_queryable = (
                row.get("user_queryable")
            )

            if (
                canonical_field
                and user_queryable
            ):

                fields.append(
                    canonical_field
                )

        return fields

    # =========================================================
    # GET DISPLAYABLE FIELDS
    # =========================================================

    def get_displayable_fields(self):

        """
        Return fields marked displayable=1.
        """

        metadata = self.get_field_metadata()

        fields = []

        for row in metadata:

            canonical_field = (
                row.get("canonical_field")
            )

            displayable = (
                row.get("displayable")
            )

            if (
                canonical_field
                and displayable
            ):

                fields.append(
                    canonical_field
                )

        return fields

    # =========================================================
    # GET IDENTIFIER FIELDS
    # =========================================================

    def get_identifier_fields(self):

        """
        Return fields marked identifier=1.

        These fields can be used for direct lookup,
        but should not automatically become questions.
        """

        metadata = self.get_field_metadata()

        fields = []

        for row in metadata:

            canonical_field = (
                row.get("canonical_field")
            )

            identifier = (
                row.get("identifier")
            )

            if (
                canonical_field
                and identifier
            ):

                fields.append(
                    canonical_field
                )

        return fields

    # =========================================================
    # SEARCH
    # =========================================================

    def search(self, filters=None):

        """
        Generic catalog search.

        Supports:

            1. Exact database match
            2. Normalized match
            3. Partial match
            4. Fuzzy match

        Searchability is controlled by metadata.
        """

        filters = filters or {}

        active_filters = {
            field: value
            for field, value in filters.items()
            if value is not None
            and str(value).strip() != ""
        }

        if not active_filters:

            return (
                self.get_all_canonical_records()
            )

        # -----------------------------------------------------
        # DATABASE FIELD MAPPING
        # -----------------------------------------------------

        database_filters = {}

        for canonical_field, value in (
            active_filters.items()
        ):

            database_field = (
                SchemaMapper.get_database_field(
                    canonical_field
                )
            )

            if database_field is None:
                continue

            database_filters[
                database_field
            ] = value

        # -----------------------------------------------------
        # EXACT DATABASE SEARCH
        # -----------------------------------------------------

        if database_filters:

            table_name = (
                self._get_table_name()
            )

            conditions = []
            values = []

            for field, value in (
                database_filters.items()
            ):

                conditions.append(
                    f"TRIM(`{field}`) = TRIM(%s)"
                )

                values.append(value)

            query = (
                f"SELECT * "
                f"FROM `{table_name}` "
                f"WHERE "
                + " AND ".join(conditions)
            )

            cursor = self.connection.cursor(
                dictionary=True
            )

            try:

                cursor.execute(
                    query,
                    tuple(values)
                )

                records = cursor.fetchall()

            finally:

                cursor.close()

            if records:

                print(
                    "DEBUG EXACT SQL MATCH RECORDS:",
                    len(records)
                )
                return (
                    SchemaMapper.map_records(
                        records
                    )
                )

        # -----------------------------------------------------
        # FALLBACK ROBUST SEARCH
        # -----------------------------------------------------

        all_records = (
            self.get_all_canonical_records()
        )
        print(
            "DEBUG ALL CANONICAL RECORDS:",
            len(all_records)
        )

        import re
        from rapidfuzz import fuzz

        def normalize(value):

            if value is None:
                return ""

            value = (
                str(value)
                .lower()
                .strip()
            )

            value = re.sub(
                r"[^a-z0-9\s]",
                " ",
                value
            )

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            return value.strip()

        candidate_records = all_records

        for field, user_value in (
            active_filters.items()
        ):

            user_normalized = normalize(
                user_value
            )

            if not user_normalized:
                continue

            matched_records = []

            for record in candidate_records:

                record_value = (
                    record.get(field)
                )

                if record_value is None:
                    continue

                record_normalized = normalize(
                    record_value
                )

                # -----------------------------------------
                # Exact normalized
                # -----------------------------------------

                if (
                    record_normalized
                    == user_normalized
                ):

                    matched_records.append(
                        record
                    )

                    continue

                # -----------------------------------------
                # Partial
                # -----------------------------------------

                if (
                    user_normalized
                    in record_normalized
                    or
                    record_normalized
                    in user_normalized
                ):

                    matched_records.append(
                        record
                    )

                    continue

                # -----------------------------------------
                # Fuzzy
                # -----------------------------------------

                score = fuzz.WRatio(
                    user_normalized,
                    record_normalized
                )

                if score >= 85:

                    matched_records.append(
                        record
                    )

            candidate_records = (
                matched_records
            )
            
            print(
                "DEBUG MATCHED RECORDS FOR",
                field,
                ":",
                len(candidate_records)
            )

            if not candidate_records:

                return []

        return candidate_records

    # =========================================================
    # COUNT
    # =========================================================

    def count(self, filters=None):

        filters = filters or {}

        database_filters = {}

        for canonical_field, value in (
            filters.items()
        ):

            if (
                value is None
                or value == ""
            ):
                continue

            database_field = (
                SchemaMapper.get_database_field(
                    canonical_field
                )
            )

            if database_field is None:
                continue

            database_filters[
                database_field
            ] = value

        table_name = (
            self._get_table_name()
        )

        query = (
            f"SELECT COUNT(*) "
            f"FROM `{table_name}`"
        )

        conditions = []
        values = []

        for database_field, value in (
            database_filters.items()
        ):

            conditions.append(
                f"`{database_field}` = %s"
            )

            values.append(value)

        if conditions:

            query += (
                " WHERE "
                + " AND ".join(conditions)
            )

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                query,
                tuple(values)
            )

            result = cursor.fetchone()

        finally:

            cursor.close()

        return result[0]

    # =========================================================
    # GET UNIQUE VALUES
    # =========================================================

    def get_unique_values(
        self,
        field,
        filters=None
    ):

        database_field = (
            SchemaMapper.get_database_field(
                field
            )
        )

        if database_field is None:

            return []

        table_name = (
            self._get_table_name()
        )

        query = (
            f"SELECT DISTINCT "
            f"`{database_field}` "
            f"FROM `{table_name}`"
        )

        filters = filters or {}

        conditions = []
        values = []

        for canonical_field, value in (
            filters.items()
        ):

            if (
                value is None
                or value == ""
            ):
                continue

            filter_database_field = (
                SchemaMapper.get_database_field(
                    canonical_field
                )
            )

            if filter_database_field is None:
                continue

            conditions.append(
                f"`{filter_database_field}` = %s"
            )

            values.append(value)

        if conditions:

            query += (
                " WHERE "
                + " AND ".join(conditions)
            )

        query += (
            f" ORDER BY `{database_field}`"
        )

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                query,
                tuple(values)
            )

            rows = cursor.fetchall()

        finally:

            cursor.close()

        return [
            row[0]
            for row in rows
            if row[0] is not None
            and str(row[0]).strip() != ""
        ]

    # =========================================================
    # GET ENTITY CANDIDATES
    # =========================================================

    def get_entity_candidates(
        self,
        filters=None
    ):

        """
        Return candidate values for entity resolution.

        IMPORTANT:

        Candidates are based on SEARCHABLE fields,
        not user-queryable fields.

        Therefore direct user input such as:

            K060448

        can still be resolved as part_number.

        But QuestionEngine will separately use
        user_queryable fields when deciding what to ask.
        """

        filters = filters or {}

        fields = (
            self.get_searchable_fields()
        )

        candidates = {}

        active_filters = {
            field: value
            for field, value in filters.items()
            if value is not None
            and str(value).strip() != ""
        }

        try:

            records = self.search(
                active_filters
            )

        except Exception:

            records = []

        # -----------------------------------------------------
        # If current filter set has no exact/fuzzy match,
        # use full catalog for entity discovery.
        # -----------------------------------------------------

        if not records:

            records = (
                self.get_all_canonical_records()
            )

        # -----------------------------------------------------
        # Extract candidates
        # -----------------------------------------------------

        for field in fields:

            values = set()

            for record in records:

                value = record.get(field)

                if (
                    value is not None
                    and str(value).strip() != ""
                ):

                    values.add(value)

            if values:

                candidates[field] = sorted(
                    values,
                    key=str
                )

        return candidates

    # =========================================================
    # GET DISTINCT VALUES FOR MULTIPLE FIELDS
    # =========================================================

    def get_distinct_values_for_fields(
        self,
        fields,
        filters=None
    ):

        filters = filters or {}

        result = {}

        for field in fields:

            values = (
                self.get_unique_values(
                    field=field,
                    filters=filters
                )
            )

            if values:

                result[field] = values

        return result

    # =========================================================
    # GET MATCHING RECORDS
    # =========================================================

    def get_matching_records(
        self,
        filters=None
    ):

        return self.search(
            filters or {}
        )
    # =========================================================
    # GET FALLBACK RECORDS
    # =========================================================

    def get_fallback_records(
        self,
        filters=None
    ):
        """
        Return fallback catalog records when the complete
        requested combination has no matching records.

        Fallback priority:

        LEVEL 1
            Keep the requested year and vehicle information.
            Remove the requested product-type filter.

        LEVEL 2
            If same-year alternatives do not exist,
            remove the year and search the same remaining
            vehicle/product constraints across other years.

        LEVEL 3
            If no fallback records exist, return [].

        No catalog values are hardcoded.
        Field behaviour is discovered from metadata.
        """

        filters = filters or {}

        active_filters = {
            field: value
            for field, value in filters.items()
            if value is not None
            and str(value).strip() != ""
        }

        if not active_filters:
            return {
                "records": [],
                "fallback_level": None
            }

        # -----------------------------------------------------
        # STEP 1
        #
        # Identify metadata dynamically.
        # -----------------------------------------------------

        metadata = []

        try:

            metadata = (
                self.get_field_metadata()
            )

        except Exception:

            metadata = []

        identifier_fields = set()

        product_fields = set()

        year_fields = set()

        for row in metadata:

            if not isinstance(row, dict):
                continue

            canonical_field = (
                row.get(
                    "canonical_field"
                )
            )

            if not canonical_field:
                continue

            field_name = str(
                canonical_field
            ).strip().lower()

            # ---------------------------------------------
            # Identifier fields
            #
            # ID / Part Number / Fenner etc.
            #
            # These should remain strict lookup fields.
            # ---------------------------------------------

            if row.get("identifier"):

                identifier_fields.add(
                    canonical_field
                )

            # ---------------------------------------------
            # Year field
            #
            # Identified from field metadata name.
            # No actual year value is hardcoded.
            # ---------------------------------------------

            database_column = str(
                row.get(
                    "database_column"
                ) or ""
            ).strip().lower()

            display_name = str(
                row.get(
                    "display_name"
                )
                or row.get(
                    "label"
                )
                or ""
            ).strip().lower()

            if (
                field_name == "year"
                or database_column == "year"
                or display_name == "year"
            ):

                year_fields.add(
                    canonical_field
                )

            # ---------------------------------------------
            # Product-related fields
            #
            # Determined from metadata field naming.
            #
            # Example:
            # producttype
            # product_type
            # product
            # ---------------------------------------------

            searchable_text = " ".join(
                [
                    field_name,
                    database_column,
                    display_name
                ]
            )

            if (
                "product" in searchable_text
                or "producttype" in searchable_text
                or "product type" in searchable_text
            ):

                if canonical_field not in identifier_fields:

                    product_fields.add(
                        canonical_field
                    )

        # -----------------------------------------------------
        # STEP 2
        #
        # Find product filters actually supplied by the user.
        # -----------------------------------------------------

        requested_product_fields = [
            field
            for field in active_filters
            if field in product_fields
        ]

        # -----------------------------------------------------
        # LEVEL 1
        #
        # Same vehicle + SAME YEAR
        #
        # Remove only the requested product field.
        #
        # Example:
        #
        # Ford + KA + 2005 + Product A
        #
        # becomes:
        #
        # Ford + KA + 2005
        # -----------------------------------------------------

        level_1_filters = dict(
            active_filters
        )

        for field in requested_product_fields:

            level_1_filters.pop(
                field,
                None
            )

        # Only perform Level 1 when a product filter was
        # actually present.
        if requested_product_fields:

            try:

                level_1_records = self.search(
                    level_1_filters
                )

            except Exception:

                level_1_records = []

            if level_1_records:

                return {
                    "records": level_1_records,
                    "fallback_level": "same_year_other_products"
                }

        # -----------------------------------------------------
        # LEVEL 2
        #
        # Same vehicle/model across other years.
        #
        # Remove the requested product field AND year.
        # -----------------------------------------------------

        level_2_filters = dict(
            level_1_filters
        )

        for field in year_fields:

            level_2_filters.pop(
                field,
                None
            )

        if level_2_filters:

            try:

                level_2_records = self.search(
                    level_2_filters
                )

            except Exception:

                level_2_records = []

            if level_2_records:

                return {
                    "records": level_2_records,
                    "fallback_level": "same_model_other_years"
                }

        # -----------------------------------------------------
        # NO FALLBACK
        # -----------------------------------------------------

        return {
            "records": [],
            "fallback_level": None
        }
    # =========================================================
    # GET RECORD BY ID
    # =========================================================

    def get_by_id(
        self,
        record_id
    ):

        database_field = (
            SchemaMapper.get_database_field(
                "id"
            )
        )

        if database_field is None:

            return None

        table_name = (
            self._get_table_name()
        )

        query = (
            f"SELECT * "
            f"FROM `{table_name}` "
            f"WHERE `{database_field}` = %s "
            f"LIMIT 1"
        )

        cursor = self.connection.cursor(
            dictionary=True
        )

        try:

            cursor.execute(
                query,
                (record_id,)
            )

            record = cursor.fetchone()

        finally:

            cursor.close()

        if record is None:

            return None

        return SchemaMapper.map_record(
            record
        )

    # =========================================================
    # GET AVAILABLE FIELDS
    # =========================================================

    def get_available_fields(self):

        """
        Fields available to the AI extraction layer.

        These are SEARCHABLE fields because a user
        may provide any searchable catalog identifier
        directly.
        """

        return self.get_searchable_fields()

    # =========================================================
    # GET USER-ASKABLE FIELDS
    # =========================================================

    def get_questionable_fields(self):

        """
        Fields the conversation engine is allowed
        to ask the user.

        Controlled entirely by metadata.
        """

        return (
            self.get_user_queryable_fields()
        )

    # =========================================================
    # DISCOVER ENTITIES FROM USER MESSAGE
    # =========================================================
    def discover_entities_from_text(
        self,
        user_message,
        score_cutoff=82,
        preferred_fields=None
    ):

        from rapidfuzz import process, fuzz
        import re

        if not user_message:
            return {}

        text = str(user_message).strip()

        if not text:
            return {}

        fields = self.get_searchable_fields()

        if not fields:
            return {}

        # ---------------------------------------------------------
        # If Qwen already identified fields, discovery should only
        # inspect those fields.
        #
        # If Qwen identified nothing, keep the existing behavior
        # and inspect all searchable fields.
        # ---------------------------------------------------------

        if preferred_fields:
            fields = [
                field
                for field in fields
                if field in preferred_fields
            ]

            if not fields:
                return {}

        discovered = {}

        normalized_text = re.sub(
            r"[^a-zA-Z0-9\s]",
            " ",
            text
        ).lower().strip()

        normalized_text = re.sub(
            r"\s+",
            " ",
            normalized_text
        )

        tokens = re.findall(
            r"[a-zA-Z0-9]+",
            text
        )

        # =====================================================
        # BUILD NORMALIZED DATABASE VALUES
        # =====================================================

        field_values = {}

        for field in fields:

            try:

                values = self.get_unique_values(
                    field=field
                )

            except Exception:

                continue

            valid_values = [
                value
                for value in values
                if value is not None
                and str(value).strip()
            ]

            if not valid_values:
                continue

            normalized_values = {}

            for value in valid_values:

                normalized_value = re.sub(
                    r"[^a-zA-Z0-9\s]",
                    " ",
                    str(value)
                ).lower().strip()

                normalized_value = re.sub(
                    r"\s+",
                    " ",
                    normalized_value
                )

                if normalized_value:

                    normalized_values[
                        normalized_value
                    ] = value

            if normalized_values:

                field_values[field] = normalized_values

        if not field_values:
            return {}

        # =====================================================
        # EXACT FULL-TEXT MATCH
        # =====================================================
        #
        # Example:
        #
        # 2021
        # Freightliner
        # Cherokee
        #
        # If the complete user message exactly matches a DB
        # value, prefer that field and do not fuzzy-match the
        # same message into unrelated fields.
        #
        # =====================================================

        exact_fields = []

        for field, normalized_values in field_values.items():

            if normalized_text in normalized_values:

                exact_fields.append(
                    (
                        field,
                        normalized_values[
                            normalized_text
                        ]
                    )
                )

        if exact_fields:

            # If more than one field contains the exact same
            # catalog value, keep all exact matches.
            #
            # Do NOT add fuzzy matches from other fields.

            for field, value in exact_fields:

                discovered[field] = {
                    "value": value,
                    "confidence": 100,
                    "method": "exact"
                }

            return discovered

        # =====================================================
        # TOKEN-BASED DISCOVERY
        # =====================================================
        #
        # Each meaningful token is resolved independently.
        #
        # IMPORTANT:
        #
        # If a token has an exact DB match in one or more fields,
        # fuzzy matching for that token is NOT performed against
        # unrelated fields.
        #
        # This prevents:
        #
        # Freightliner -> OEM Freightliner
        # Freightliner -> Model TL       ❌
        # Freightliner -> Engine RE      ❌
        #
        # =====================================================

        token_exact_fields = {}

        for token in tokens:

            token_normalized = re.sub(
                r"[^a-zA-Z0-9]",
                "",
                token
            ).lower()

            if len(token_normalized) < 2:
                continue

            if token_normalized.isdigit():
                continue

            exact_matches = []

            for field, normalized_values in field_values.items():

                if token_normalized in normalized_values:

                    exact_matches.append(
                        (
                            field,
                            normalized_values[
                                token_normalized
                            ]
                        )
                    )

            if exact_matches:

                token_exact_fields[
                    token_normalized
                ] = exact_matches

        # -----------------------------------------------------
        # Add exact token matches
        # -----------------------------------------------------

        for token_normalized, matches in token_exact_fields.items():

            for field, value in matches:

                discovered[field] = {
                    "value": value,
                    "confidence": 100,
                    "method": "token_exact"
                }

        # =====================================================
        # TOKEN FUZZY
        # =====================================================
        #
        # Only run fuzzy matching when that token has NO exact
        # match anywhere in the catalog.
        #
        # This preserves spelling mistakes / partial words while
        # preventing unrelated cross-field matches when an exact
        # value already exists.
        #
        # =====================================================

        for token in tokens:

            token_normalized = re.sub(
                r"[^a-zA-Z0-9]",
                "",
                token
            ).lower()

            if len(token_normalized) < 3:
                continue

            if token_normalized.isdigit():
                continue

            # Exact match already identified for this token.
            if token_normalized in token_exact_fields:
                continue

            fuzzy_matches = []

            for field, normalized_values in field_values.items():

                try:

                    results = process.extract(
                        token_normalized,
                        list(
                            normalized_values.keys()
                        ),
                        scorer=fuzz.WRatio,
                        limit=1,
                        score_cutoff=score_cutoff
                    )

                except Exception:

                    continue

                if not results:
                    continue

                matched_text, score, _ = results[0]

                fuzzy_matches.append(
                    (
                        field,
                        normalized_values[
                            matched_text
                        ],
                        score
                    )
                )

            if not fuzzy_matches:
                continue

            # -------------------------------------------------
            # IMPORTANT
            #
            # If multiple fields produce fuzzy matches, only
            # accept the strongest match when it is clearly
            # stronger than the others.
            # -------------------------------------------------

            fuzzy_matches.sort(
                key=lambda item: item[2],
                reverse=True
            )

            best_field, best_value, best_score = (
                fuzzy_matches[0]
            )
            
            # -------------------------------------------------
            # GENERIC FUZZY VALIDATION
            #
            # WRatio can give a high score when a short catalog
            # value is matched against an unrelated natural-
            # language word.
            #
            # Example:
            #     details -> LS
            #
            # Keep genuine spelling / partial matches such as:
            #     Frod  -> Ford
            #     Volks -> Volkswagen
            #
            # Do not change WRatio, cutoff, or fuzzy algorithm.
            # -------------------------------------------------

            best_match_ratio = fuzz.ratio(
                token_normalized,
                re.sub(
                    r"[^a-zA-Z0-9]",
                    "",
                    str(best_value)
                ).lower()
            )

            if (
                best_score - best_match_ratio
                >= 30
            ):
                continue
            
            if len(fuzzy_matches) > 1:

                second_score = fuzzy_matches[1][2]

                # Do not make an arbitrary field decision when
                # multiple fields are equally plausible.
                if (
                    best_score - second_score
                    < 5
                ):
                    continue

            discovered[best_field] = {
                "value": best_value,
                "confidence": round(
                    best_score,
                    2
                ),
                "method": "token_fuzzy"
            }

        # =====================================================
        # FULL TEXT FUZZY
        # =====================================================

        if (
            not discovered
            and not normalized_text.isdigit()
            and len(normalized_text) >= 3
        ):

            fuzzy_matches = []

            for field, normalized_values in field_values.items():

                try:

                    results = process.extract(
                        normalized_text,
                        list(
                            normalized_values.keys()
                        ),
                        scorer=fuzz.WRatio,
                        limit=1,
                        score_cutoff=score_cutoff
                    )

                except Exception:

                    continue

                if not results:
                    continue

                matched_text, score, _ = results[0]

                fuzzy_matches.append(
                    (
                        field,
                        normalized_values[
                            matched_text
                        ],
                        score
                    )
                )

            if fuzzy_matches:

                fuzzy_matches.sort(
                    key=lambda item: item[2],
                    reverse=True
                )

                best_field, best_value, best_score = (
                    fuzzy_matches[0]
                )

                if len(fuzzy_matches) == 1:

                    discovered[best_field] = {
                        "value": best_value,
                        "confidence": round(
                            best_score,
                            2
                        ),
                        "method": "fuzzy"
                    }

                else:

                    second_score = fuzzy_matches[1][2]

                    if (
                        best_score - second_score
                        >= 5
                    ):

                        discovered[best_field] = {
                            "value": best_value,
                            "confidence": round(
                                best_score,
                                2
                            ),
                            "method": "fuzzy"
                        }
        print("DEBUG DISCOVERY RESULT:", discovered)
        return discovered