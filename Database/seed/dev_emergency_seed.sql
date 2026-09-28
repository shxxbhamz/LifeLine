-- =========================================================
-- LifeLine Emergency Development Data
-- =========================================================


-- Create a demo emergency request
INSERT INTO emergency_requests (
    facility_id,
    created_by,
    required_blood_type,
    component_type,
    units_required,
    urgency,
    radius_km,
    status,
    notes
)
SELECT
    f.id,
    u.id,
    'O+',
    'RED_BLOOD_CELLS',
    3,
    'CRITICAL',
    25,
    'ACTIVE',
    'Development test emergency'
FROM facilities f
JOIN staff_profiles sp
    ON sp.facility_id = f.id
JOIN users u
    ON u.id = sp.user_id
WHERE u.username = 'stteststaff'
LIMIT 1;