class SchemaMapper:
    """
    Generic database schema mapper.

    Converts database-specific column names into
    standard canonical fields used by the AI system.

    Dataset-specific configuration should be changed
    ONLY in this file when a new dataset is introduced.
    """

    # =========================================================
    # DATABASE TABLE
    # =========================================================

    TABLE_NAME = "tbl_product"
    # Metadata table
    METADATA_TABLE_NAME = "catalog_field_metadata"

    # =========================================================
    # DATABASE COLUMN → CANONICAL FIELD
    # =========================================================

    COLUMN_MAPPING = {

        "Id": "id",

        "OEMName": "oem",
        "VehicleModel": "model",
        "EngineName": "engine",
        "Year": "year",

        "PartNumber": "part_number",
        "GatesPartNumber": "gates_part_number",

        "ProductType": "product",
        "RoutingGuide": "routing_guide",

        "Fenner": "fenner",
        "Category": "category",

        "Images": "image",
        "Status": "status",

        "DescId": "description_id"
    }

    # =========================================================
    # GET TABLE NAME
    # =========================================================

    @classmethod
    def get_table_name(cls):
        """
        Return the database table name.
        """

        return cls.TABLE_NAME
    # =========================================================
    # GET METADATA TABLE NAME
    # =========================================================

    @classmethod
    def get_metadata_table_name(cls):
        """
        Return the metadata table name.
        """

        return cls.METADATA_TABLE_NAME

    # =========================================================
    # MAP ONE DATABASE RECORD
    # =========================================================

    @classmethod
    def map_record(cls, record):
        """
        Convert one database record into canonical format.
        """

        mapped_record = {}

        for database_field, canonical_field in cls.COLUMN_MAPPING.items():

            if database_field in record:

                mapped_record[canonical_field] = record[
                    database_field
                ]

        return mapped_record

    # =========================================================
    # MAP MULTIPLE RECORDS
    # =========================================================

    @classmethod
    def map_records(cls, records):
        """
        Convert multiple database records
        into canonical records.
        """

        return [
            cls.map_record(record)
            for record in records
        ]

    # =========================================================
    # GET CANONICAL FIELD
    # =========================================================

    @classmethod
    def get_canonical_field(cls, database_field):
        """
        Return canonical field name for a database column.
        """

        return cls.COLUMN_MAPPING.get(database_field)

    # =========================================================
    # GET DATABASE FIELD
    # =========================================================

    @classmethod
    def get_database_field(cls, canonical_field):
        """
        Return database column name for a canonical field.
        """

        for database_field, canonical in cls.COLUMN_MAPPING.items():

            if canonical == canonical_field:
                return database_field

        return None

    # =========================================================
    # GET ALL CANONICAL FIELDS
    # =========================================================

    @classmethod
    def get_canonical_fields(cls):
        """
        Return all canonical fields supported
        by the current dataset.
        """

        return list(
            cls.COLUMN_MAPPING.values()
        )

    # =========================================================
    # GET SEARCHABLE FIELDS
    # =========================================================

    @classmethod
    def get_searchable_fields(cls):
        """
        Return canonical fields that can be used
        by the AI for catalog search and filtering.

        No dataset-specific field names are hardcoded here.
        """

        return [
            field
            for field in cls.COLUMN_MAPPING.values()
            if field not in {
                "id",
                "image",
                "description_id"
            }
        ]

    # =========================================================
    # GET ALL DATABASE COLUMNS
    # =========================================================

    @classmethod
    def get_database_columns(cls):
        """
        Return all database column names understood
        by this mapper.
        """

        return list(
            cls.COLUMN_MAPPING.keys()
        )

    # =========================================================
    # VALIDATE CANONICAL FIELD
    # =========================================================

    @classmethod
    def is_valid_canonical_field(cls, field):
        """
        Check whether a canonical field exists
        in the current dataset mapping.
        """

        return field in cls.COLUMN_MAPPING.values()

    # =========================================================
    # VALIDATE DATABASE COLUMN
    # =========================================================

    @classmethod
    def is_valid_database_column(cls, field):
        """
        Check whether a database column exists
        in the current dataset mapping.
        """

        return field in cls.COLUMN_MAPPING

    # =========================================================
    # GET FIELD MAPPING
    # =========================================================

    @classmethod
    def get_mapping(cls):
        """
        Return a copy of the complete
        database → canonical mapping.
        """

        return dict(cls.COLUMN_MAPPING)