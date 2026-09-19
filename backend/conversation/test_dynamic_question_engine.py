from backend.conversation.conversation_state import ConversationState
from backend.conversation.dynamic_question_engine import DynamicQuestionEngine


def run_test(title, data):

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    state = ConversationState()

    state.update(data)

    engine = DynamicQuestionEngine()

    result = engine.analyze(state)

    print("\nOriginal State:")
    print(state.get_all())

    print("\nEngine Result:")
    print(result)


def main():

    # ---------------------------------------------------------
    # TEST 1
    # Bajaj + Starter Motor
    # ---------------------------------------------------------

    run_test(
        "TEST 1 - Bajaj Starter Motor",
        {
            "oem": "Bajaj",
            "product": "Starter Motor"
        }
    )

    # ---------------------------------------------------------
    # TEST 2
    # Bajaj + Pulsar + Starter Motor
    # ---------------------------------------------------------

    run_test(
        "TEST 2 - Bajaj Pulsar Starter Motor",
        {
            "oem": "Bajaj",
            "model": "Pulsar",
            "product": "Starter Motor"
        }
    )

    # ---------------------------------------------------------
    # TEST 3
    # Complete unique record
    # ---------------------------------------------------------

    run_test(
        "TEST 3 - Complete Product",
        {
            "oem": "Bajaj",
            "model": "Pulsar",
            "variant_type": "ABS",
            "year": 2023,
            "fuel_type": "Petrol",
            "product": "Starter Motor"
        }
    )

    # ---------------------------------------------------------
    # TEST 4
    # Requested product unavailable
    # ---------------------------------------------------------

    run_test(
        "TEST 4 - Product Not Available",
        {
            "oem": "Ashok Leyland",
            "model": "2165",
            "product": "Ball Bearing"
        }
    )


if __name__ == "__main__":
    main()