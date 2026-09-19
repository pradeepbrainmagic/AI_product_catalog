"""
Conversation Pipeline Integration Test

Flow:

User Message
    ↓
QwenCatalogEngine
    ↓
Entity Pipeline
    ↓
ConversationState
    ↓
DynamicQuestionEngine
    ↓
DatabaseLayer
    ↓
SchemaMapper
    ↓
MySQL

This test uses the actual database and Qwen model.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

from backend.database.catalog_database import CatalogDatabase
from backend.database.database_layer import DatabaseLayer
from backend.conversation.conversation_manager import ConversationManager


# ============================================================
# DATABASE SETUP
# ============================================================

def create_database_layer():
    """
    Create CatalogDatabase and connect it to DatabaseLayer.
    """

    catalog_db = CatalogDatabase()

    connection = catalog_db._get_connection()

    database_layer = DatabaseLayer(
        db_connection=connection
    )

    return catalog_db, connection, database_layer


# ============================================================
# PRINT RESPONSE
# ============================================================

def print_response(response):
    """
    Print conversation response in a readable format.
    """

    print("\n" + "=" * 70)

    print("USER:")
    print(response.get("user_message"))

    print("\nEXTRACTED DATA:")
    print(response.get("extracted_data"))

    print("\nRESOLVED DATA:")
    print(response.get("resolved_data"))

    print("\nRESOLUTION DETAILS:")
    print(response.get("resolution_details"))

    print("\nCONVERSATION STATE:")
    print(response.get("conversation_state"))

    print("\nENGINE RESULT:")
    print(response.get("result"))

    print("=" * 70)


# ============================================================
# SINGLE MESSAGE TEST
# ============================================================

def test_message(manager, message):
    """
    Send one message to ConversationManager
    and print the complete pipeline result.
    """

    print("\n")
    print("#" * 70)
    print(f"TEST MESSAGE: {message}")
    print("#" * 70)

    try:

        response = manager.process_message(
            message
        )

        print_response(response)

        return response

    except Exception as error:

        print("\n❌ ERROR")
        print(type(error).__name__)
        print(str(error))

        return None


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("DYNAMIC PRODUCT CATALOG CONVERSATION TEST")
    print("=" * 70)

    connection = None

    try:

        # ----------------------------------------------------
        # Create database layer
        # ----------------------------------------------------

        catalog_db, connection, database_layer = (
            create_database_layer()
        )

        print("\n✅ Database connection created.")

        # ----------------------------------------------------
        # Test database connection
        # ----------------------------------------------------

        if catalog_db.test_connection():

            print("✅ MySQL connection successful.")

        else:

            print("❌ MySQL connection failed.")
            return

        # ----------------------------------------------------
        # Show schema fields
        # ----------------------------------------------------

        available_fields = (
            database_layer.get_available_fields()
        )

        print("\nAVAILABLE CANONICAL FIELDS:")
        print(available_fields)

        # ----------------------------------------------------
        # Show record count
        # ----------------------------------------------------

        record_count = database_layer.count()

        print("\nTOTAL PRODUCTS:")
        print(record_count)

        # ----------------------------------------------------
        # Create ConversationManager
        # ----------------------------------------------------

        manager = ConversationManager(
            catalog_search=None,
            database_layer=database_layer
        )

        print("\n✅ ConversationManager created.")

        # ====================================================
        # TEST 1
        # ====================================================

        test_message(
            manager,
            "BMW"
        )

        # ====================================================
        # TEST 2
        # ====================================================

        test_message(
            manager,
            "BMW X1"
        )

        # ====================================================
        # TEST 3
        # ====================================================

        test_message(
            manager,
            "BMW X1 2023"
        )

        # ====================================================
        # TEST 4
        # PART NUMBER
        # ====================================================

        manager.reset()

        test_message(
            manager,
            "K060434"
        )

        # ====================================================
        # TEST 5
        # MULTIPLE RECORDS / QUESTION
        # ====================================================

        manager.reset()

        response = test_message(
            manager,
            "BMW X1"
        )

        # ----------------------------------------------------
        # If the engine asks a question, automatically test
        # the first available option.
        # ----------------------------------------------------

        if response:

            result = response.get(
                "result",
                {}
            )

            if result.get("action") == "ask_question":

                options = result.get(
                    "options",
                    []
                )

                field = result.get(
                    "field"
                )

                print("\n")
                print("-" * 70)
                print("DYNAMIC QUESTION DETECTED")
                print("-" * 70)

                print("FIELD:")
                print(field)

                print("OPTIONS:")
                print(options)

                # ------------------------------------------------
                # Test short answer using previous question context
                # ------------------------------------------------

                if options:

                    selected_option = options[0]

                    print("\nTESTING SHORT ANSWER:")
                    print(selected_option)

                    test_message(
                        manager,
                        str(selected_option)
                    )

        # ====================================================
        # TEST 6
        # SPELLING / FUZZY INPUT
        # ====================================================

        manager.reset()

        test_message(
            manager,
            "BWM"
        )

        # ====================================================
        # TEST 7
        # NON-EXISTING PRODUCT
        # ====================================================

        manager.reset()

        test_message(
            manager,
            "ThisProductDoesNotExist123"
        )

        # ====================================================
        # TEST 8
        # RESET
        # ====================================================

        print("\n")
        print("=" * 70)
        print("TESTING CONVERSATION RESET")
        print("=" * 70)

        manager.reset()

        print(
            "STATE AFTER RESET:"
        )

        print(
            manager.state.get_all()
        )

        print("\n✅ Reset test completed.")

        # ====================================================
        # FINAL
        # ====================================================

        print("\n")
        print("=" * 70)
        print("ALL TEST CASES EXECUTED")
        print("=" * 70)

    except Exception as error:

        print("\n")
        print("=" * 70)
        print("❌ TEST FAILED")
        print("=" * 70)

        print(
            type(error).__name__
        )

        print(
            str(error)
        )

    finally:

        # ----------------------------------------------------
        # Close the persistent DatabaseLayer connection
        # ----------------------------------------------------

        if connection is not None:

            try:
                connection.close()

                print(
                    "\nDatabase connection closed."
                )

            except Exception:
                pass


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()