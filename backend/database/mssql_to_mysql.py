import re
from pathlib import Path


# =========================================================
# CONFIGURATION
# =========================================================

SOURCE_FILE = Path(
    r"D:\Brain magic project 1\product_catalog_ai\data\jkftbl_product.sql"
)

OUTPUT_FILE = Path(
    r"D:\Brain magic project 1\product_catalog_ai\data\mysql_product_import.sql"
)

FAILED_FILE = Path(
    r"D:\Brain magic project 1\product_catalog_ai\data\conversion_failed.sql"
)


# =========================================================
# CONVERT MSSQL INSERT → MYSQL INSERT
# =========================================================

def convert_insert(statement):

    match = re.search(
        r"INSERT\s+\[dbo\]\.\[tbl_Product\]\s*"
        r"\((.*?)\)\s*VALUES\s*\((.*)\)",
        statement,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return None

    columns = match.group(1)
    values = match.group(2)

    # Remove [ColumnName] brackets
    columns = re.sub(
        r"\[([^\]]+)\]",
        r"\1",
        columns
    )

    # Remove SQL Server Unicode prefix N
    values = re.sub(
        r"\bN'",
        "'",
        values
    )

    mysql_statement = (
        "INSERT INTO tbl_product "
        f"({columns}) "
        f"VALUES ({values});"
    )

    return mysql_statement


# =========================================================
# MAIN
# =========================================================

def convert_file():

    print("\n" + "=" * 60)
    print("MSSQL → MYSQL CONVERTER")
    print("=" * 60)

    print("\nSource:")
    print(SOURCE_FILE)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source SQL file not found:\n{SOURCE_FILE}"
        )

    content = SOURCE_FILE.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    print("\nSource file loaded.")

    # -----------------------------------------------------
    # Split using GO
    # -----------------------------------------------------

    statements = re.split(
        r"^\s*GO\s*$",
        content,
        flags=re.IGNORECASE | re.MULTILINE
    )

    converted = []
    failed = []

    total_inserts = 0
    converted_inserts = 0

    # -----------------------------------------------------
    # Process statements
    # -----------------------------------------------------

    for statement in statements:

        if not re.search(
            r"INSERT\s+\[dbo\]\.\[tbl_Product\]",
            statement,
            re.IGNORECASE
        ):
            continue

        total_inserts += 1

        mysql_statement = convert_insert(
            statement.strip()
        )

        if mysql_statement:

            converted.append(mysql_statement)
            converted_inserts += 1

        else:

            failed.append(
                statement.strip()
            )

    # -----------------------------------------------------
    # Write successful conversions
    # -----------------------------------------------------

    header = """-- =========================================================
-- MYSQL PRODUCT IMPORT
-- Converted from MSSQL tbl_Product
-- =========================================================

USE ai_catalog;

"""

    OUTPUT_FILE.write_text(
        header + "\n".join(converted) + "\n",
        encoding="utf-8"
    )

    # -----------------------------------------------------
    # Write failed conversions
    # -----------------------------------------------------

    if failed:

        failed_header = """-- =========================================================
-- FAILED MSSQL INSERT STATEMENTS
-- These statements need manual inspection
-- =========================================================

"""

        FAILED_FILE.write_text(
            failed_header + "\n\n".join(failed) + "\n",
            encoding="utf-8"
        )

    else:

        FAILED_FILE.write_text(
            "-- No failed INSERT statements.\n",
            encoding="utf-8"
        )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print("\n" + "=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)

    print(f"\nTotal INSERT statements found : {total_inserts}")
    print(f"Successfully converted        : {converted_inserts}")
    print(f"Failed conversions            : {len(failed)}")

    print("\nMySQL output:")
    print(OUTPUT_FILE)

    print("\nFailed statements:")
    print(FAILED_FILE)

    print("\n" + "=" * 60)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    convert_file()