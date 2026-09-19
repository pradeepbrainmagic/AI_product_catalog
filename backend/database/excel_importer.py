import pandas as pd
import mysql.connector
from pathlib import Path


# =========================================================
# CONFIGURATION
# =========================================================

EXCEL_FILE = Path(
    r"D:\Brain magic project 1\Part Details.xlsx"
)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Kavi@2",
    "database": "ai_catalog"
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    return mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"]
    )


# =========================================================
# VALUE CLEANING
# =========================================================

def clean_value(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def clean_int(value):

    if pd.isna(value):
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def clean_decimal(value):

    if pd.isna(value):
        return None

    try:
        value = str(value).replace(",", "").replace("₹", "").strip()

        return float(value)

    except (ValueError, TypeError):
        return None


# =========================================================
# READ EXCEL
# =========================================================

def load_excel():

    print("\n" + "=" * 60)
    print("READING EXCEL")
    print("=" * 60)

    excel = pd.ExcelFile(EXCEL_FILE)

    print("\nAvailable Sheets:")
    print(excel.sheet_names)

    # -----------------------------------------------------
    # OEM SHEET
    # -----------------------------------------------------

    oem_sheet = None

    for sheet in excel.sheet_names:

        if "oem" in sheet.lower():
            oem_sheet = sheet
            break

    if oem_sheet is None:
        raise Exception("OEM sheet not found.")

    # -----------------------------------------------------
    # SHEET 4 / VEHICLE APPLICATION
    # -----------------------------------------------------

    application_sheet = None

    for sheet in excel.sheet_names:

        if sheet.lower().strip() == "sheet4":
            application_sheet = sheet
            break

    if application_sheet is None:
        raise Exception("Sheet4 not found.")

    # -----------------------------------------------------
    # PART DETAILS SHEET
    # -----------------------------------------------------

    parts_sheet = None

    for sheet in excel.sheet_names:

        sheet_name = sheet.lower().replace(" ", "")

        if "partdetails" in sheet_name:
            parts_sheet = sheet
            break

    if parts_sheet is None:
        raise Exception("Parts Details sheet not found.")

    print("\nUsing sheets:")

    print("OEM              :", oem_sheet)
    print("Vehicle          :", application_sheet)
    print("Part Details     :", parts_sheet)

    # -----------------------------------------------------
    # LOAD DATA
    # -----------------------------------------------------

    oem_df = pd.read_excel(
        EXCEL_FILE,
        sheet_name=oem_sheet
    )

    application_df = pd.read_excel(
        EXCEL_FILE,
        sheet_name=application_sheet
    )

    parts_df = pd.read_excel(
        EXCEL_FILE,
        sheet_name=parts_sheet
    )

    print("\nRows loaded:")

    print("OEM              :", len(oem_df))
    print("Vehicle          :", len(application_df))
    print("Part Details     :", len(parts_df))

    return (
        oem_df,
        application_df,
        parts_df
    )


# =========================================================
# 1. IMPORT OEM MASTER
# =========================================================

def import_oem_master(cursor, oem_df):

    print("\n" + "-" * 60)
    print("IMPORTING OEM MASTER")
    print("-" * 60)

    sql = """
        INSERT INTO oem_master
        (
            oem_id,
            oem_customer,
            oem_image,
            oem_priority
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE

            oem_customer = VALUES(oem_customer),
            oem_image = VALUES(oem_image),
            oem_priority = VALUES(oem_priority)
    """

    count = 0

    for _, row in oem_df.iterrows():

        oem_id = clean_int(
            row.get("Oem_Id")
        )

        oem_customer = clean_value(
            row.get("Oem_Customer")
        )

        oem_image = clean_value(
            row.get("Oem_Image")
        )

        oem_priority = clean_int(
            row.get("Oem_Priority")
        )

        if oem_id is None or oem_customer is None:
            continue

        cursor.execute(
            sql,
            (
                oem_id,
                oem_customer,
                oem_image,
                oem_priority
            )
        )

        count += 1

    print(
        f"OEM records imported: {count}"
    )


# =========================================================
# 2. IMPORT VEHICLE APPLICATION
# =========================================================

def import_vehicle_application(
    cursor,
    application_df,
    oem_df
):

    print("\n" + "-" * 60)
    print("IMPORTING VEHICLE APPLICATION")
    print("-" * 60)

    # -----------------------------------------------------
    # Build OEM lookup
    # -----------------------------------------------------

    oem_lookup = {}

    for _, row in oem_df.iterrows():

        oem_id = clean_int(
            row.get("Oem_Id")
        )

        oem_customer = clean_value(
            row.get("Oem_Customer")
        )

        if oem_id is not None and oem_customer:

            oem_lookup[
                oem_customer.lower()
            ] = oem_id

    # -----------------------------------------------------
    # SQL
    # -----------------------------------------------------

    sql = """
        INSERT INTO vehicle_application
        (
            app_id,
            segment,
            oem_id,
            model,
            engine
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE

            segment = VALUES(segment),
            oem_id = VALUES(oem_id),
            model = VALUES(model),
            engine = VALUES(engine)
    """

    count = 0

    for _, row in application_df.iterrows():

        app_id = clean_int(
            row.get("id")
        )

        segment = clean_value(
            row.get("segment")
        )

        make = clean_value(
            row.get("make")
        )

        model = clean_value(
            row.get("model")
        )

        engine = clean_value(
            row.get("engine")
        )

        if app_id is None:
            continue

        if not make:
            print(
                f"WARNING: OEM missing for app_id {app_id}"
            )
            continue

        oem_id = oem_lookup.get(
            make.lower()
        )

        if oem_id is None:

            print(
                f"WARNING: OEM '{make}' not found "
                f"for app_id {app_id}"
            )

            continue

        cursor.execute(
            sql,
            (
                app_id,
                segment,
                oem_id,
                model,
                engine
            )
        )

        count += 1

    print(
        f"Vehicle application records imported: {count}"
    )


# =========================================================
# 3. IMPORT VEHICLE PRODUCT MAPPING
# =========================================================

def import_vehicle_product_mapping(
    cursor,
    application_df
):

    print("\n" + "-" * 60)
    print("IMPORTING VEHICLE PRODUCT MAPPING")
    print("-" * 60)

    # -----------------------------------------------------
    # Product columns from Sheet4
    # -----------------------------------------------------

    product_columns = [
        "starter_motor",
        "alternator",
        "wipermotor_system",
        "wiper_motor",
        "wipingsystem",
        "rearwiper",
        "distributor",
        "ignition_coil",
        "blower_motor",
        "cam_sensor"
    ]

    sql = """
        INSERT INTO vehicle_product_mapping
        (
            app_id,
            product_name,
            part_number
        )
        VALUES
        (
            %s,
            %s,
            %s
        )
    """

    count = 0

    for _, row in application_df.iterrows():

        app_id = clean_int(
            row.get("id")
        )

        if app_id is None:
            continue

        for product_column in product_columns:

            part_number = clean_value(
                row.get(product_column)
            )

            # No part number = no mapping
            if not part_number:
                continue

            # Convert column name into readable product name
            product_name = product_column.replace(
                "_",
                " "
            ).title()

            cursor.execute(
                sql,
                (
                    app_id,
                    product_name,
                    part_number
                )
            )

            count += 1

    print(
        f"Vehicle product mappings imported: {count}"
    )


# =========================================================
# 4. IMPORT PRODUCT PART DETAILS
# =========================================================

def import_product_part_details(
    cursor,
    parts_df
):

    print("\n" + "-" * 60)
    print("IMPORTING PRODUCT PART DETAILS")
    print("-" * 60)

    sql = """
        INSERT INTO product_part_details
        (
            part_number,
            pro_status,
            product_name,
            part_volt,
            part_output,
            oe_name,
            oem_partnum,
            app_name,
            description,
            hsn_code,
            gst,
            uos,
            mrp
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        ON DUPLICATE KEY UPDATE

            pro_status = VALUES(pro_status),
            product_name = VALUES(product_name),
            part_volt = VALUES(part_volt),
            part_output = VALUES(part_output),
            oe_name = VALUES(oe_name),
            oem_partnum = VALUES(oem_partnum),
            app_name = VALUES(app_name),
            description = VALUES(description),
            hsn_code = VALUES(hsn_code),
            gst = VALUES(gst),
            uos = VALUES(uos),
            mrp = VALUES(mrp)
    """

    count = 0

    for _, row in parts_df.iterrows():

        part_number = clean_value(
            row.get("part_no")
        )

        if not part_number:
            continue

        pro_status = clean_value(
            row.get("pro_status")
        )

        product_name = clean_value(
            row.get("Productname")
        )

        part_volt = clean_value(
            row.get("part_volt")
        )

        part_output = clean_value(
            row.get("part_output")
        )

        oe_name = clean_value(
            row.get("OEname")
        )

        oem_partnum = clean_value(
            row.get("Oem_partno")
        )

        app_name = clean_value(
            row.get("Appname")
        )

        description = clean_value(
            row.get("decription")
        )

        hsn_code = clean_value(
            row.get("HSNCode")
        )

        gst = clean_decimal(
            row.get("GST")
        )

        uos = clean_value(
            row.get("Uos")
        )

        mrp = clean_decimal(
            row.get("Mrp")
        )

        cursor.execute(
            sql,
            (
                part_number,
                pro_status,
                product_name,
                part_volt,
                part_output,
                oe_name,
                oem_partnum,
                app_name,
                description,
                hsn_code,
                gst,
                uos,
                mrp
            )
        )

        count += 1

    print(
        f"Product part records imported: {count}"
    )


# =========================================================
# VERIFY COUNTS
# =========================================================

def verify_database(cursor):

    print("\n" + "=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)

    tables = [
        "oem_master",
        "vehicle_application",
        "vehicle_product_mapping",
        "product_part_details"
    ]

    for table in tables:

        cursor.execute(
            f"SELECT COUNT(*) FROM {table}"
        )

        count = cursor.fetchone()[0]

        print(
            f"{table:<30} : {count}"
        )


# =========================================================
# MAIN IMPORT
# =========================================================

def import_excel():

    connection = None

    try:

        # -------------------------------------------------
        # LOAD EXCEL
        # -------------------------------------------------

        (
            oem_df,
            application_df,
            parts_df
        ) = load_excel()

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        connection = get_connection()

        cursor = connection.cursor()

        print("\nDatabase connected successfully.")

        # -------------------------------------------------
        # STEP 1
        # -------------------------------------------------

        import_oem_master(
            cursor,
            oem_df
        )

        # -------------------------------------------------
        # STEP 2
        # -------------------------------------------------

        import_vehicle_application(
            cursor,
            application_df,
            oem_df
        )

        # -------------------------------------------------
        # STEP 3
        # -------------------------------------------------

        import_vehicle_product_mapping(
            cursor,
            application_df
        )

        # -------------------------------------------------
        # STEP 4
        # -------------------------------------------------

        import_product_part_details(
            cursor,
            parts_df
        )

        # -------------------------------------------------
        # COMMIT
        # -------------------------------------------------

        connection.commit()

        # -------------------------------------------------
        # VERIFY
        # -------------------------------------------------

        verify_database(cursor)

        print("\n" + "=" * 60)
        print("EXCEL IMPORT COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:

        if connection:
            connection.rollback()

        print("\n" + "=" * 60)
        print("IMPORT FAILED")
        print("=" * 60)

        print("ERROR:", e)

        raise

    finally:

        if connection:
            connection.close()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    import_excel()