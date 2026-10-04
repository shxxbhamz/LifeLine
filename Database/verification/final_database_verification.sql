-- =========================================================
-- LifeLine Final Database Verification (V1-V7)
-- Run in pgAdmin against lifeline_db AFTER all migrations.
-- =========================================================

-- 1) Confirm database
SELECT current_database() AS database_name;

-- 2) Confirm base tables (expected: 15)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

SELECT COUNT(*) AS base_table_count
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE';

-- 3) Confirm views (expected inventory_status_view)
SELECT table_name AS view_name
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;

-- 4) Confirm V5/V6/V7 changes
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'donor_profiles'
  AND column_name = 'country';

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'donations'
  AND column_name = 'quantity_units';

-- authorization_status should be gone after V7
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'staff_profiles'
  AND column_name = 'authorization_status';

-- authorization_declared_at intentionally remains as self-declaration timestamp
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'staff_profiles'
  AND column_name = 'authorization_declared_at';

-- 5) Orphan / foreign-key sanity checks. Every bad_rows result should be 0.
SELECT COUNT(*) AS bad_rows_donor_without_user
FROM donor_profiles dp
LEFT JOIN users u ON u.id = dp.user_id
WHERE u.id IS NULL;

SELECT COUNT(*) AS bad_rows_staff_without_user_or_facility
FROM staff_profiles sp
LEFT JOIN users u ON u.id = sp.user_id
LEFT JOIN facilities f ON f.id = sp.facility_id
WHERE u.id IS NULL OR f.id IS NULL;

SELECT COUNT(*) AS bad_rows_emergency_without_facility_or_staff
FROM emergency_requests er
LEFT JOIN facilities f ON f.id = er.facility_id
LEFT JOIN staff_profiles sp ON sp.user_id = er.created_by
WHERE f.id IS NULL OR sp.user_id IS NULL;

SELECT COUNT(*) AS bad_rows_match_without_request_or_donor
FROM request_matches rm
LEFT JOIN emergency_requests er ON er.id = rm.request_id
LEFT JOIN donor_profiles dp ON dp.user_id = rm.donor_id
WHERE er.id IS NULL OR dp.user_id IS NULL;

SELECT COUNT(*) AS bad_rows_appointment_without_donor_or_facility
FROM appointments a
LEFT JOIN donor_profiles dp ON dp.user_id = a.donor_id
LEFT JOIN facilities f ON f.id = a.facility_id
WHERE dp.user_id IS NULL OR f.id IS NULL;

SELECT COUNT(*) AS bad_rows_donation_without_appointment
FROM donations d
LEFT JOIN appointments a ON a.id = d.appointment_id
WHERE a.id IS NULL;

SELECT COUNT(*) AS bad_rows_screening_without_donor
FROM eligibility_screenings es
LEFT JOIN donor_profiles dp ON dp.user_id = es.donor_id
WHERE dp.user_id IS NULL;

SELECT COUNT(*) AS bad_rows_answer_without_screening_or_question
FROM screening_answers sa
LEFT JOIN eligibility_screenings es ON es.id = sa.screening_id
LEFT JOIN screening_questions sq ON sq.id = sa.question_id
WHERE es.id IS NULL OR sq.id IS NULL;

SELECT COUNT(*) AS bad_rows_inventory_without_facility
FROM blood_inventory bi
LEFT JOIN facilities f ON f.id = bi.facility_id
WHERE f.id IS NULL;

SELECT COUNT(*) AS bad_rows_inventory_transaction_without_inventory
FROM inventory_transactions it
LEFT JOIN blood_inventory bi ON bi.id = it.inventory_id
WHERE bi.id IS NULL;

-- 6) Logical data checks. Every bad_rows result should be 0.
SELECT COUNT(*) AS bad_rows_inventory_values
FROM blood_inventory
WHERE units_available < 0
   OR low_threshold < 0
   OR critical_threshold < 0
   OR critical_threshold > low_threshold;

SELECT COUNT(*) AS bad_rows_completed_screening_without_timestamp
FROM eligibility_screenings
WHERE status = 'COMPLETED'
  AND completed_at IS NULL;

SELECT COUNT(*) AS bad_rows_regular_appointment_with_emergency_match
FROM appointments
WHERE appointment_source = 'REGULAR'
  AND request_match_id IS NOT NULL;

SELECT COUNT(*) AS bad_rows_emergency_appointment_without_match
FROM appointments
WHERE appointment_source = 'EMERGENCY'
  AND request_match_id IS NULL;

SELECT request_id, donor_id, COUNT(*) AS duplicate_count
FROM request_matches
GROUP BY request_id, donor_id
HAVING COUNT(*) > 1;

SELECT donor_id, scheduled_at, COUNT(*) AS duplicate_count
FROM appointments
GROUP BY donor_id, scheduled_at
HAVING COUNT(*) > 1;

-- 7) Inventory view smoke test
SELECT
    facility_name,
    blood_type,
    component_type,
    units_available,
    inventory_status
FROM inventory_status_view
ORDER BY facility_name, blood_type, component_type;

-- 8) Matching-data smoke test
SELECT
    u.username,
    dp.blood_type,
    dp.emergency_available,
    dp.city,
    dp.province,
    dp.country,
    es.preliminary_result,
    es.completed_at AS latest_screening_completed_at
FROM users u
JOIN donor_profiles dp ON dp.user_id = u.id
LEFT JOIN LATERAL (
    SELECT preliminary_result, completed_at
    FROM eligibility_screenings
    WHERE donor_id = dp.user_id
      AND status = 'COMPLETED'
    ORDER BY completed_at DESC NULLS LAST
    LIMIT 1
) es ON TRUE
WHERE u.role = 'DONOR'
ORDER BY u.username;

-- 9) Emergency workflow smoke test
SELECT
    er.id AS request_id,
    f.name AS facility,
    creator.username AS created_by,
    er.required_blood_type,
    er.component_type,
    er.units_required,
    er.urgency,
    er.status,
    COUNT(rm.id) AS matched_donors,
    COUNT(*) FILTER (WHERE rm.response_status = 'ACCEPTED') AS accepted_donors
FROM emergency_requests er
JOIN facilities f ON f.id = er.facility_id
JOIN users creator ON creator.id = er.created_by
LEFT JOIN request_matches rm ON rm.request_id = er.id
GROUP BY er.id, f.name, creator.username
ORDER BY er.created_at DESC;

-- 10) Appointment / donation smoke test
SELECT
    a.id AS appointment_id,
    donor.username AS donor,
    f.name AS facility,
    a.donation_type,
    a.appointment_source,
    a.scheduled_at,
    a.status,
    d.id AS donation_id,
    d.actual_component_type,
    d.quantity_units,
    d.completed_at
FROM appointments a
JOIN users donor ON donor.id = a.donor_id
JOIN facilities f ON f.id = a.facility_id
LEFT JOIN donations d ON d.appointment_id = a.id
ORDER BY a.scheduled_at DESC;
