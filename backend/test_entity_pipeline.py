from backend.entity_pipeline import resolve_extracted_entities


CANDIDATES = {

    "oem": [
        "Bajaj",
        "Honda",
        "TVS Motors",
        "Ashok Leyland",
        "Tata Motors",
        "Mahindra"
    ],

    "segment": [
        "Two Wheeler",
        "Three Wheeler",
        "Light Commercial Vehicle",
        "Heavy Commercial Vehicle"
    ],

    "model": [
        "Pulsar",
        "Discover",
        "Platina",
        "Apache",
        "Activa"
    ],

    "variant_type": [
        "Standard",
        "ABS",
        "Deluxe"
    ],

    "fuel_type": [
        "Petrol",
        "Diesel"
    ],

    "product": [
        "Starter Motor",
        "Brake Pad",
        "Gear",
        "Ball Bearing",
        "Clutch Plate"
    ],

    "part_number": [
        "PN1001",
        "PN1002",
        "PN1003"
    ]
}


EXTRACTED_DATA = {
    "oem": "Bajaj",
    "segment": None,
    "model": "pulser",
    "variant_type": None,
    "year": None,
    "fuel_type": None,
    "product": "starter motar",
    "part_number": None
}


result = resolve_extracted_entities(
    EXTRACTED_DATA,
    CANDIDATES
)


print("\n==============================")
print("RESOLVED DATA")
print("==============================")

print(result["resolved_data"])


print("\n==============================")
print("RESOLUTION DETAILS")
print("==============================")

for field, details in result["resolution_details"].items():

    print(f"\n{field}")
    print(details)