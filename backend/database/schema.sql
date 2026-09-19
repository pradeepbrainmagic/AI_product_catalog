-- ============================================================
-- LUCAS TVS PRODUCT CATALOG DATABASE SCHEMA
-- ============================================================

-- ------------------------------------------------------------
-- 1. OEM MASTER
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS oem_master (
    oem_id INT PRIMARY KEY,
    oem_customer VARCHAR(255) NOT NULL,
    oem_image VARCHAR(500),
    oem_priority INT
);


-- ------------------------------------------------------------
-- 2. VEHICLE APPLICATION
-- One row = one vehicle/model/application
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS vehicle_application (
    app_id INT AUTO_INCREMENT PRIMARY KEY,

    oem_id INT NOT NULL,

    segment VARCHAR(100),
    make VARCHAR(255),
    model VARCHAR(255),
    engine VARCHAR(255),

    CONSTRAINT fk_application_oem
        FOREIGN KEY (oem_id)
        REFERENCES oem_master(oem_id)
);


-- ------------------------------------------------------------
-- 3. VEHICLE PRODUCT MAPPING
-- Connects a vehicle/application with its products
-- and corresponding part numbers.
--
-- IMPORTANT:
-- Starter Motor, Alternator, Wiper Motor etc.
-- are stored as rows, NOT separate columns.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS vehicle_product_mapping (
    mapping_id INT AUTO_INCREMENT PRIMARY KEY,

    app_id INT NOT NULL,

    product_name VARCHAR(255) NOT NULL,
    part_no VARCHAR(255),

    CONSTRAINT fk_mapping_application
        FOREIGN KEY (app_id)
        REFERENCES vehicle_application(app_id)
);


-- ------------------------------------------------------------
-- 4. PRODUCT PART DETAILS
-- Complete details of an individual part number
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS product_part_details (
    id INT PRIMARY KEY,

    oem_id INT,
    app_id INT,
    pro_id INT,
    pro_mode VARCHAR(255),

    engine_type VARCHAR(255),
    pro_type VARCHAR(255),
    pro_status VARCHAR(100),
    pro_supresed VARCHAR(100),

    part_no VARCHAR(255) NOT NULL,

    part_volt VARCHAR(100),
    part_output VARCHAR(100),

    plant VARCHAR(255),
    Uos VARCHAR(100),
    Mrp DECIMAL(12,2),

    Oem_partno VARCHAR(255),
    Ubittype VARCHAR(100),

    Pro_image VARCHAR(500),
    pro_exp_image VARCHAR(500),

    decription TEXT,

    Full_Unit_No VARCHAR(255),
    Appname VARCHAR(255),
    Productname VARCHAR(255),
    OEname VARCHAR(255),

    expoledview VARCHAR(500),

    OldMrp DECIMAL(12,2),
    HSNCode VARCHAR(50),
    GST DECIMAL(5,2),

    CONSTRAINT fk_part_oem
        FOREIGN KEY (oem_id)
        REFERENCES oem_master(oem_id),

    CONSTRAINT fk_part_application
        FOREIGN KEY (app_id)
        REFERENCES vehicle_application(app_id)
);