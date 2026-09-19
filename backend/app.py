import os
import mysql.connector
from dotenv import load_dotenv
from pathlib import Path



from backend.catalog.catalog_search import CatalogSearch
from backend.catalog.catalog_adapter import CatalogAdapter

from backend.database.database_layer import DatabaseLayer

from backend.conversation.conversation_manager import (
    ConversationManager
)


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# DATABASE CONNECTION
# =========================================================

def create_database_connection():

    connection = mysql.connector.connect(
        host=os.getenv("CATALOG_DB_HOST"),
        user=os.getenv("CATALOG_DB_USER"),
        password=os.getenv("CATALOG_DB_PASSWORD"),
        database=os.getenv("CATALOG_DB_NAME")
    )

    return connection


# =========================================================
# DISPLAY AI RESPONSE
# =========================================================

def display_response(response):

    print("\n" + "=" * 70)

    result = response.get("result", {})

    status = result.get("status")
    action = result.get("action")

    # -----------------------------------------------------
    # NO MATCH
    # -----------------------------------------------------

    if status == "not_found":

        print("AI:")
        print(
            result.get(
                "message",
                "No matching product found."
            )
        )

        return

    # -----------------------------------------------------
    # QUESTION
    # -----------------------------------------------------

    if action == "ask_question":

        print("AI:")
        print(
            result.get(
                "question",
                "I need some more information."
            )
        )

        print()

        options = result.get("options", [])

        if options:

            print("Available options:")

            for index, option in enumerate(
                options,
                start=1
            ):
                print(
                    f"  {index}. {option}"
                )

        print(
            f"\nRecords found: "
            f"{result.get('records_found', 0)}"
        )

        return

    # -----------------------------------------------------
    # ONE PRODUCT
    # -----------------------------------------------------

    if action == "show_product":

        print("AI:")
        print(
            result.get(
                "message",
                "I found the matching product."
            )
        )

        records = result.get(
            "records",
            []
        )

        if records:

            print("\nPRODUCT DETAILS")
            print("-" * 70)

            for record in records:

                for field, value in record.items():

                    if value is None:
                        continue

                    print(
                        f"{field}: {value}"
                    )

        return

    # -----------------------------------------------------
    # MULTIPLE PRODUCTS
    # -----------------------------------------------------

    if action == "show_products":

        print("AI:")
        print(
            result.get(
                "message",
                "I found multiple matching products."
            )
        )

        records = result.get(
            "records",
            []
        )

        print(
            f"\nTotal products: {len(records)}"
        )

        print("-" * 70)

        for index, record in enumerate(
            records,
            start=1
        ):

            print(
                f"\nProduct {index}"
            )

            for field, value in record.items():

                if value is None:
                    continue

                print(
                    f"  {field}: {value}"
                )

        return

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    print("AI:")
    print(
        result.get(
            "message",
            "I could not determine the next step."
        )
    )


# =========================================================
# MAIN INTERACTIVE CONVERSATION
# =========================================================

def main():

    print("\n")
    print("=" * 70)
    print("        AI PRODUCT CATALOG CONVERSATION")
    print("=" * 70)

    connection = None

    try:

        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        connection = create_database_connection()

        print("\n✅ Database connection successful.")

        # -------------------------------------------------
        # DATABASE LAYER
        # -------------------------------------------------

        database_layer = DatabaseLayer(
            db_connection=connection
        )

        # -------------------------------------------------
        # CATALOG SEARCH
        # -------------------------------------------------

        catalog_adapter = CatalogAdapter()

        catalog_search = CatalogSearch(
            catalog_adapter=catalog_adapter
        )

        # -------------------------------------------------
        # CONVERSATION MANAGER
        # -------------------------------------------------

        conversation_manager = ConversationManager(
            catalog_search=catalog_search,
            database_layer=database_layer
        )

        print("✅ ConversationManager created.")

        # -------------------------------------------------
        # SHOW AVAILABLE FIELDS
        # -------------------------------------------------

        available_fields = (
            database_layer.get_available_fields()
        )

        print("\nAVAILABLE CANONICAL FIELDS:")

        print(
            available_fields
        )

        print("\n")
        print("-" * 70)
        print("Start chatting with the AI.")
        print("Type 'reset' to start a new conversation.")
        print("Type 'exit' to stop.")
        print("-" * 70)

        # -------------------------------------------------
        # CONVERSATION LOOP
        # -------------------------------------------------

        while True:

            try:

                user_message = input(
                    "\nYou: "
                ).strip()

            except KeyboardInterrupt:

                print(
                    "\n\nConversation stopped."
                )

                break

            # -------------------------------------------------
            # EMPTY MESSAGE
            # -------------------------------------------------

            if not user_message:

                print(
                    "AI: Please enter something."
                )

                continue

            # -------------------------------------------------
            # EXIT
            # -------------------------------------------------

            if user_message.lower() in {
                "exit",
                "quit",
                "q"
            }:

                print(
                    "\nAI: Goodbye!"
                )

                break

            # -------------------------------------------------
            # RESET
            # -------------------------------------------------

            if user_message.lower() == "reset":

                conversation_manager.reset()

                print(
                    "\nAI: Conversation reset. "
                    "What product are you looking for?"
                )

                continue

            # -------------------------------------------------
            # PROCESS MESSAGE
            # -------------------------------------------------

            try:

                response = (
                    conversation_manager.process_message(
                        user_message
                    )
                )

                display_response(
                    response
                )

            except Exception as e:

                print("\n❌ Error:")
                print(str(e))

                # Don't terminate the complete
                # conversation for one bad message.

                continue

    except Exception as e:

        print("\n❌ Application startup failed:")
        print(str(e))

    finally:

        if connection:

            try:

                connection.close()

                print(
                    "\n✅ Database connection closed."
                )

            except Exception:
                pass


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()