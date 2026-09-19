from backend.conversation.conversation_state import ConversationState


def main():

    state = ConversationState()

    print("\n==============================")
    print("CONVERSATION STATE TEST")
    print("==============================")

    # First user message
    first_input = {
        "oem": "Bajaj",
        "segment": None,
        "model": None,
        "variant_type": None,
        "year": None,
        "fuel_type": None,
        "product": "Starter Motor",
        "part_number": None
    }

    state.update(first_input)

    print("\nAfter First Message:")
    print(state.get_all())

    print("\nMissing Fields:")
    print(state.missing_fields())

    # Second user message
    second_input = {
        "oem": None,
        "segment": None,
        "model": "Pulsar",
        "variant_type": None,
        "year": None,
        "fuel_type": None,
        "product": None,
        "part_number": None
    }

    state.update(second_input)

    print("\nAfter Second Message:")
    print(state.get_all())

    print("\nMissing Fields:")
    print(state.missing_fields())


if __name__ == "__main__":
    main()