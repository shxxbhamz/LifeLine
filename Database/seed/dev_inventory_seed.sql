-- =========================================================
-- LifeLine Inventory Development Seed Data
-- =========================================================


-- Create inventory for all blood groups/components
-- at the demo hospital.

INSERT INTO blood_inventory (
    facility_id,
    blood_type,
    component_type,
    units_available,
    low_threshold,
    critical_threshold
)

SELECT
    f.id,
    bt.blood_type,
    ct.component_type,
    10,
    5,
    2

FROM facilities f

CROSS JOIN (
    VALUES
        ('A+'),
        ('A-'),
        ('B+'),
        ('B-'),
        ('AB+'),
        ('AB-'),
        ('O+'),
        ('O-')
) AS bt(blood_type)

CROSS JOIN (
    VALUES
        ('WHOLE_BLOOD'),
        ('RED_BLOOD_CELLS'),
        ('PLASMA'),
        ('PLATELETS')
) AS ct(component_type)

WHERE f.name = 'LifeLine Demo Hospital'

ON CONFLICT (
    facility_id,
    blood_type,
    component_type
)
DO NOTHING;


-- O- Whole Blood → Critical

UPDATE blood_inventory
SET
    units_available = 2,
    updated_at = CURRENT_TIMESTAMP
WHERE facility_id = (
    SELECT id
    FROM facilities
    WHERE name = 'LifeLine Demo Hospital'
    LIMIT 1
)
AND blood_type = 'O-'
AND component_type = 'WHOLE_BLOOD';


-- A- Plasma → Low

UPDATE blood_inventory
SET
    units_available = 4,
    updated_at = CURRENT_TIMESTAMP
WHERE facility_id = (
    SELECT id
    FROM facilities
    WHERE name = 'LifeLine Demo Hospital'
    LIMIT 1
)
AND blood_type = 'A-'
AND component_type = 'PLASMA';


-- B- Platelets → Critical

UPDATE blood_inventory
SET
    units_available = 1,
    updated_at = CURRENT_TIMESTAMP
WHERE facility_id = (
    SELECT id
    FROM facilities
    WHERE name = 'LifeLine Demo Hospital'
    LIMIT 1
)
AND blood_type = 'B-'
AND component_type = 'PLATELETS';