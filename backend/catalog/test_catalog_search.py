from backend.catalog.catalog_search import CatalogSearch


def print_records(title, records):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print("Records Found:", len(records))

    for record in records:

        print(
            f"\nSupplier      : {record.get('supplier_company')}"
            f"\nOEM           : {record.get('oem')}"
            f"\nSegment       : {record.get('segment')}"
            f"\nModel         : {record.get('model')}"
            f"\nVariant       : {record.get('variant_type')}"
            f"\nYear          : {record.get('year')}"
            f"\nFuel          : {record.get('fuel_type')}"
            f"\nProduct       : {record.get('product')}"
            f"\nPart Number   : {record.get('part_number')}"
            f"\nDescription   : {record.get('product_description')}"
            f"\nMRP           : {record.get('mrp')}"
            f"\nUnit          : {record.get('unit')}"
            f"\nStatus        : {record.get('status')}"
        )


def main():

    search = CatalogSearch()

    # -------------------------------------------------
    # TEST 1
    # Bajaj + Pulsar + Starter Motor
    # -------------------------------------------------

    results = search.search_product(
        oem="Bajaj",
        model="Pulsar",
        product="Starter Motor"
    )

    print_records(
        "TEST 1 - Bajaj Pulsar Starter Motor",
        results
    )

    # -------------------------------------------------
    # TEST 2
    # Bajaj + Pulsar + Brake Pad
    # Multiple suppliers
    # -------------------------------------------------

    results = search.search_product(
        oem="Bajaj",
        model="Pulsar",
        product="Brake Pad"
    )

    print_records(
        "TEST 2 - Bajaj Pulsar Brake Pad - Multiple Suppliers",
        results
    )

    # -------------------------------------------------
    # TEST 3
    # Product not requested here.
    # Find all products for Bajaj Pulsar.
    # -------------------------------------------------

    products = search.get_available_products(
        oem="Bajaj",
        model="Pulsar"
    )

    print("\n" + "=" * 60)
    print("TEST 3 - All Products for Bajaj Pulsar")
    print("=" * 60)

    print(products)

    # -------------------------------------------------
    # TEST 4
    # Ashok Leyland 2165 + Ball Bearing
    # Expected: no exact result
    # -------------------------------------------------

    results = search.search_product(
        oem="Ashok Leyland",
        model="2165",
        product="Ball Bearing"
    )

    print_records(
        "TEST 4 - Ashok Leyland 2165 Ball Bearing",
        results
    )

    # -------------------------------------------------
    # TEST 5
    # Fallback:
    # If Ball Bearing does not exist,
    # find other products for Ashok Leyland 2165.
    # -------------------------------------------------

    fallback_products = search.get_available_products(
        oem="Ashok Leyland",
        model="2165"
    )

    print("\n" + "=" * 60)
    print("TEST 5 - Alternative Products for Ashok Leyland 2165")
    print("=" * 60)

    print(fallback_products)

    # -------------------------------------------------
    # TEST 6
    # Find all suppliers for Bajaj Pulsar Brake Pad
    # -------------------------------------------------

    suppliers = search.get_suppliers_for_product(
        oem="Bajaj",
        model="Pulsar",
        product="Brake Pad"
    )

    print("\n" + "=" * 60)
    print("TEST 6 - Suppliers for Bajaj Pulsar Brake Pad")
    print("=" * 60)

    print(suppliers)


if __name__ == "__main__":
    main()