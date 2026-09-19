from backend.catalog.catalog_adapter import CatalogAdapter


class CatalogSearch:
    """
    Generic catalog search engine.

    This class does not know anything about a particular company.
    It searches whatever catalog is provided through CatalogAdapter.
    """

    def __init__(self, catalog_adapter=None):

        self.catalog = catalog_adapter or CatalogAdapter()

    def search(self, filters):
        """
        Search catalog using only the information available
        in the filters.

        Example:

        {
            "oem": "Bajaj",
            "model": "Pulsar",
            "product": "Starter Motor"
        }
        """

        records = self.catalog.get_all_records()

        results = []

        for record in records:

            matched = True

            for field, value in filters.items():

                # Ignore empty values
                if value is None or value == "":
                    continue

                record_value = record.get(field)

                if record_value is None:
                    matched = False
                    break

                if str(record_value).strip().lower() != str(value).strip().lower():
                    matched = False
                    break

            if matched:
                results.append(record)

        return results

    def search_product(self, oem=None, model=None, product=None,
                       segment=None, variant_type=None,
                       year=None, fuel_type=None):
        """
        Search for the requested product using the information
        currently available.
        """

        filters = {
            "oem": oem,
            "segment": segment,
            "model": model,
            "variant_type": variant_type,
            "year": year,
            "fuel_type": fuel_type,
            "product": product
        }

        # Remove empty values
        filters = {
            key: value
            for key, value in filters.items()
            if value is not None and value != ""
        }

        return self.search(filters)

    def find_available_products(self, oem=None, model=None,
                                segment=None, variant_type=None,
                                year=None, fuel_type=None):
        """
        Find all products available for the given vehicle/application.

        IMPORTANT:
        Product filter is intentionally NOT included.

        This is used when the requested product is unavailable.
        """

        filters = {
            "oem": oem,
            "segment": segment,
            "model": model,
            "variant_type": variant_type,
            "year": year,
            "fuel_type": fuel_type
        }

        filters = {
            key: value
            for key, value in filters.items()
            if value is not None and value != ""
        }

        results = self.search(filters)

        return results

    def get_unique_values(self, records, field):
        """
        Get unique values from search results.

        Example:
        get_unique_values(results, "model")
        """

        values = set()

        for record in records:

            value = record.get(field)

            if value is not None:
                values.add(value)

        return sorted(values, key=str)

    def get_available_models(self, oem=None, product=None,
                             segment=None):
        """
        Find models available for the current context.
        """

        results = self.search_product(
            oem=oem,
            segment=segment,
            product=product
        )

        return self.get_unique_values(results, "model")

    def get_available_years(self, oem=None, model=None,
                            product=None, segment=None,
                            variant_type=None, fuel_type=None):
        """
        Find years available for the current context.
        """

        results = self.search_product(
            oem=oem,
            segment=segment,
            model=model,
            variant_type=variant_type,
            fuel_type=fuel_type,
            product=product
        )

        return self.get_unique_values(results, "year")

    def get_available_variants(self, oem=None, model=None,
                               product=None, segment=None,
                               year=None, fuel_type=None):
        """
        Find variant types available for the current context.
        """

        results = self.search_product(
            oem=oem,
            segment=segment,
            model=model,
            year=year,
            fuel_type=fuel_type,
            product=product
        )

        return self.get_unique_values(results, "variant_type")

    def get_available_fuel_types(self, oem=None, model=None,
                                 product=None, segment=None,
                                 variant_type=None, year=None):
        """
        Find fuel types available for the current context.
        """

        results = self.search_product(
            oem=oem,
            segment=segment,
            model=model,
            variant_type=variant_type,
            year=year,
            fuel_type=None,
            product=product
        )

        return self.get_unique_values(results, "fuel_type")

    def get_available_products(self, oem=None, model=None,
                               segment=None, variant_type=None,
                               year=None, fuel_type=None):
        """
        Get unique products available for a vehicle/application.
        """

        results = self.find_available_products(
            oem=oem,
            model=model,
            segment=segment,
            variant_type=variant_type,
            year=year,
            fuel_type=fuel_type
        )

        return self.get_unique_values(results, "product")

    def get_suppliers_for_product(self, oem=None, model=None,
                                  product=None, segment=None,
                                  variant_type=None, year=None,
                                  fuel_type=None):
        """
        Find all supplier companies supplying the requested product.
        """

        results = self.search_product(
            oem=oem,
            model=model,
            product=product,
            segment=segment,
            variant_type=variant_type,
            year=year,
            fuel_type=fuel_type
        )

        return self.get_unique_values(
            results,
            "supplier_company"
        )