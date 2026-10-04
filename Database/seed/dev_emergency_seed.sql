-- =========================================================
-- LifeLine Emergency Development Data (corrected for V8)
-- =========================================================

INSERT INTO emergency_requests (
    facility_id,
    created_by,
    required_blood_type,
    component_type,
    units_required,
    urgency,
    radius_km,
    status,
    notes,
    idempotency_key
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
    'Development test emergency',
    'DEV-EMERGENCY-001'
FROM facilities f
JOIN staff_profiles sp
    ON sp.facility_id = f.id
JOIN users u
    ON u.id = sp.user_id
WHERE u.username = 'stteststaff'
  AND NOT EXISTS (
      SELECT 1
      FROM emergency_requests er
      WHERE er.idempotency_key = 'DEV-EMERGENCY-001'
  )
LIMIT 1;
