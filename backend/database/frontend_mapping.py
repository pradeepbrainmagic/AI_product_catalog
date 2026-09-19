class FrontendMapper:
    """
    Converts canonical catalog fields into
    frontend display fields.
    """

    FRONTEND_MAPPING = {
        "image": "Image",
        "fenner": "Part Number",
        "engine": "Engine",
        "oem": "OEM",
        "model": "Model",
        "year": "Year",
        "product": "ProductType",
        "part_number": "Competitor PartNo",
        "category": "Category",
        "gates_part_number": "GatesPartNumber",
        "status": "Status",
        "routing_guide": "Routing Guide"
    }

    @classmethod
    def map_record(cls, canonical_record):
        """
        Convert canonical database record
        into frontend display format.
        """

        frontend_record = {}

        for canonical_field, frontend_field in cls.FRONTEND_MAPPING.items():

            if canonical_field in canonical_record:
                frontend_record[frontend_field] = canonical_record[
                    canonical_field
                ]

        return frontend_record

    @classmethod
    def map_records(cls, records):
        """
        Convert multiple records.
        """

        return [
            cls.map_record(record)
            for record in records
        ]