from backend.catalog.catalog_adapter import CatalogAdapter


def main():

    catalog = CatalogAdapter()

    print("\n==============================")
    print("CATALOG ADAPTER TEST")
    print("==============================")

    print("\nTotal Records:")
    print(catalog.get_record_count())

    print("\nOEMs:")
    print(catalog.get_field_values("oem"))

    print("\nSegments:")
    print(catalog.get_field_values("segment"))

    print("\nProducts:")
    print(catalog.get_field_values("product"))

    print("\nModels:")
    print(catalog.get_field_values("model"))


if __name__ == "__main__":
    main()