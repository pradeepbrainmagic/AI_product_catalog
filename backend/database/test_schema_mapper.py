from backend.database.schema_mapper import SchemaMapper


def main():

    print("\n" + "=" * 60)
    print("SCHEMA MAPPER TEST")
    print("=" * 60)

    # ---------------------------------------------------------
    # TEST DATABASE RECORD
    # ---------------------------------------------------------

    database_record = {
        "Id": 14963,
        "OEMName": "Volkswagen",
        "VehicleModel": "Passat",
        "EngineName": "4-Cyl. 2.0 L",
        "Year": "2022",
        "PartNumber": "K060434",
        "GatesPartNumber": "TD434K6",
        "ProductType": "Automotive V-Ribbed Belt (Standard)",
        "RoutingGuide": "",
        "Fenner": "6PK1100",
        "Category": "Passenger Cars & Light Trucks",
        "Images": "6pk.jpg",
        "DescId": 2,
        "Status": ""
    }

    # ---------------------------------------------------------
    # MAP RECORD
    # ---------------------------------------------------------

    mapped_record = SchemaMapper.map_record(
        database_record
    )

    print("\nDATABASE RECORD:")
    print(database_record)

    print("\nCANONICAL RECORD:")
    print(mapped_record)

    # ---------------------------------------------------------
    # FIELD TEST
    # ---------------------------------------------------------

    print("\nFIELD MAPPING:")

    print(
        "OEMName ->",
        SchemaMapper.get_canonical_field("OEMName")
    )

    print(
        "VehicleModel ->",
        SchemaMapper.get_canonical_field("VehicleModel")
    )

    print(
        "PartNumber ->",
        SchemaMapper.get_canonical_field("PartNumber")
    )

    print(
        "ProductType ->",
        SchemaMapper.get_canonical_field("ProductType")
    )

    print(
        "oem ->",
        SchemaMapper.get_database_field("oem")
    )

    print(
        "product ->",
        SchemaMapper.get_database_field("product")
    )

    print("\nSUPPORTED CANONICAL FIELDS:")
    print(SchemaMapper.get_canonical_fields())


if __name__ == "__main__":
    main()