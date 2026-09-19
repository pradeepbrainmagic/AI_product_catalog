from backend.database.catalog_database import CatalogDatabase


class CatalogAdapter:
    """
    Generic interface for accessing product catalog data.

    The adapter hides database column names from
    the AI/search layer.

    Database:
        MySQL
        ai_catalog
        tbl_product
    """

    def __init__(self, database=None):

        self.database = database or CatalogDatabase()

        self.records = None

    def _normalize_record(self, record):
        """
        Convert database column names into generic
        application-level field names.

        Original database fields are also preserved.
        """

        return {
            # -------------------------------------------------
            # Original database values
            # -------------------------------------------------

            "id": record.get("Id"),

            "OEMName": record.get("OEMName"),
            "VehicleModel": record.get("VehicleModel"),
            "EngineName": record.get("EngineName"),
            "Year": record.get("Year"),
            "PartNumber": record.get("PartNumber"),
            "GatesPartNumber": record.get("GatesPartNumber"),
            "ProductType": record.get("ProductType"),
            "RoutingGuide": record.get("RoutingGuide"),
            "Fenner": record.get("Fenner"),
            "Category": record.get("Category"),
            "Images": record.get("Images"),
            "DescId": record.get("DescId"),
            "Status": record.get("Status"),

            # -------------------------------------------------
            # Generic application fields
            # -------------------------------------------------

            "oem": record.get("OEMName"),
            "model": record.get("VehicleModel"),
            "engine": record.get("EngineName"),
            "year": record.get("Year"),

            "product": record.get("ProductType"),

            "part_number": record.get("PartNumber"),

            "gates_part_number": record.get("GatesPartNumber"),

            "routing_guide": record.get("RoutingGuide"),

            "fenner": record.get("Fenner"),

            "category": record.get("Category"),

            "image": record.get("Images"),

            "status": record.get("Status"),

            # Compatibility fields
            "segment": None,
            "variant_type": None,
            "fuel_type": None,
            "supplier_company": None
        }

    def _load_catalog(self):
        """
        Load all catalog records from MySQL.
        """

        database_records = self.database.get_all_products()

        return [
            self._normalize_record(record)
            for record in database_records
        ]

    def get_all_records(self):
        """
        Return all catalog records.

        Data is loaded from MySQL.
        """

        if self.records is None:
            self.records = self._load_catalog()

        return self.records

    def get_field_values(self, field_name):
        """
        Return unique values for a particular field.

        Example:
            get_field_values("oem")
        """

        values = set()

        for record in self.get_all_records():

            value = record.get(field_name)

            if value is not None and value != "":
                values.add(value)

        return sorted(values, key=str)

    def get_record_count(self):
        """
        Return total number of catalog records.
        """

        return self.database.get_product_count()