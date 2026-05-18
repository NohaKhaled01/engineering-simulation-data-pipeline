Show TABLES;

## Create Variants table:
CREATE TABLE variant (
    variant_id INT AUTO_INCREMENT PRIMARY KEY,
    Azure_Epic_ID INT,
    Title VARCHAR(255),
    variant_abbreviation VARCHAR(50),
    engine_type VARCHAR(50),
    engine_capacity VARCHAR(50),
    model_year INT,
    model_id_1 VARCHAR(50),
    model_id_2 VARCHAR(50),
    start_date DATE,
    end_date DATE
);

## Create Syncs table:
CREATE TABLE sync (
    sync_id INT AUTO_INCREMENT PRIMARY KEY,
    variant_id INT,
    FOREIGN KEY (variant_id) REFERENCES variant(variant_id),
    sync_title VARCHAR(255),
    sync_name VARCHAR(50),
    sync_add_name VARCHAR(50),
    text_description VARCHAR(5000),
    start_date DATE,
    close_date DATE,
    Azure_Sync_ID INT,
    Azure_Epic_ID INT
);

## Create Requests table:
CREATE TABLE request (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    sync_id INT,
    FOREIGN KEY (sync_id) REFERENCES sync(sync_id),
    Request_Name VARCHAR(1000),
    State VARCHAR(50),
    start_date DATE,
    close_date DATE,
    exhaust_run bool,
    components_run bool,
    battery_run bool,
    TRA_run bool,
    other_run_type bool,
    request_description text,    
    Azure_Story_ID INT,
    Azure_Feature_Parent INT
);

## Create Components table:
CREATE TABLE components (
    component_id INT AUTO_INCREMENT PRIMARY KEY,
    variant_id INT,
    FOREIGN KEY (variant_id) REFERENCES variant(variant_id),
    source_project_name VARCHAR(100),
    component_name VARCHAR(100)
);

## Create Components Materials table:
CREATE TABLE components_materials (
    material_id INT AUTO_INCREMENT PRIMARY KEY,
    component_id INT,
    FOREIGN KEY (component_id) REFERENCES components(component_id),
    component_name VARCHAR(100),
    solid_name VARCHAR(100),
    solid_material VARCHAR(100)
);

## Create Exhaust table:
CREATE TABLE exhausts (
    exhaust_id INT AUTO_INCREMENT PRIMARY KEY,
    sync_id INT,
    FOREIGN KEY (sync_id) REFERENCES sync(sync_id),
    project_name VARCHAR(100),
    has_manifold bool,
    has_turbine bool,
    has_rear_CAT bool,
    has_muffler bool,
    has_resonator bool,
    has_dual_turbine bool,
    has_flex_joint bool,
    has_dual_end bool,
    has_y_joint bool,
    has_SCR_or_DPF_or_GPF bool
);

## Create Exhaust Materials table:
CREATE TABLE exhausts_materials (
    material_id INT AUTO_INCREMENT PRIMARY KEY,
    exhaust_id INT,
    FOREIGN KEY (exhaust_id) REFERENCES exhausts(exhaust_id),
    project_name VARCHAR(100),
    segment_name VARCHAR(100),
    segment_region_name VARCHAR(100),
    segment_region_material VARCHAR(100)
);

## Create Exhaust Meshes table:
CREATE TABLE exhausts_meshes (
    mesh_id INT AUTO_INCREMENT PRIMARY KEY,
    exhaust_id INT,
    FOREIGN KEY (exhaust_id) REFERENCES exhausts(exhaust_id),
    project_name VARCHAR(100),
    segment_name VARCHAR(100),
    mesh_file_name VARCHAR(100)
);


-- Testing Stuff:
SELECT 
	c.component_id as comp_id_comp, cm.component_id as comp_id_mat, v.variant_id as var_id_v, 
    c.component_name as comp_name_comp, cm.solid_name as solid_name, cm.solid_material as solid_material, c.project_name
FROM components as c
JOIN variant as v
ON c.variant_id = v.variant_id
JOIN components_materials as cm
ON c.component_id = cm.component_id
WHERE c.component_name LIKE '%comp%'
;

SELECT *
FROM variant
WHERE Title LIKE 'JL%'
;


SELECT v.variant_id, v.variant_abbreviation, s.sync_id, s.sync_title, s.sync_name, exh.exhaust_id, exh.project_name
FROM variant as v
JOIN sync as s
ON v.variant_id = s.variant_id
JOIN exhausts as exh
ON s.sync_id = exh.sync_id
;

SELECT s.sync_id, s.sync_title, s.sync_name, exh.exhaust_id, exh.project_name, exh.has_turbine
FROM sync as s
JOIN exhausts as exh
ON s.sync_id = exh.sync_id
WHERE project_name LIKE 'D2%'
;

SELECT 
	variant.variant_abbreviation, sync.sync_title, sync.sync_name,
    exh.*
FROM variant
JOIN sync
ON variant.variant_id = sync.variant_id
JOIN exhausts as exh
ON sync.sync_id = exh.sync_id
WHERE variant.variant_abbreviation = 'JL'
;