from backend.conversation.conversation_manager import ConversationManager
from backend.catalog.catalog_search import CatalogSearch

# ---------------------------------------------------------
# TEMPORARY CANDIDATES
# ---------------------------------------------------------

CANDIDATES = {

    "oem": [
        "Bajaj",
        "Ashok Leyland",
        "Tata Motors",
        "Mahindra"
    ],

    "segment": [
        "Two Wheeler",
        "Light Commercial Vehicle",
        "Heavy Commercial Vehicle"
    ],

    "model": [
        "Pulsar",
        "Discover",
        "Platina",
        "2165",
        "LPO124",
        "Dost"
    ],

    "variant_type": [
        "Standard",
        "ABS"
    ],

    "fuel_type": [
        "Petrol",
        "Diesel"
    ],

    "product": [
        "Starter Motor",
        "Brake Pad",
        "Clutch Plate",
        "Gear"
    ],

    "part_number": []
}


def main():

    catalog_search = CatalogSearch()

    manager = ConversationManager(
        candidates=CANDIDATES,
        catalog_search=catalog_search
    )

    print("\n" + "=" * 70)
    print("PRODUCT CATALOG CONVERSATION TEST")
    print("=" * 70)

    # -----------------------------------------------------
    # MESSAGE 1
    # -----------------------------------------------------

    result = manager.process_message(
       "I need a starter motor for Pulsar"
    )

    print("\nUSER:")
    print("I need a starter motor for Pulsar")

    print("\nAI RESULT:")
    print(result)

    # -----------------------------------------------------
    # MESSAGE 2
    # -----------------------------------------------------

    result = manager.process_message(
        "Pulsar"
    )

    print("\nUSER:")
    print("Pulsar")

    print("\nAI RESULT:")
    print(result)

    # -----------------------------------------------------
    # MESSAGE 3
    # -----------------------------------------------------

    result = manager.process_message(
        "ABS"
    )

    print("\nUSER:")
    print("ABS")

    print("\nAI RESULT:")
    print(result)


if __name__ == "__main__":
    main()