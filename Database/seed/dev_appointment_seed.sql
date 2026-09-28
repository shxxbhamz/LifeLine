-- =========================================================
-- LifeLine Appointment Development Seed Data
-- =========================================================


-- =========================================================
-- FACILITY HOURS
-- Demo hospital: Monday-Saturday 8AM-6PM
-- Sunday closed
-- =========================================================

INSERT INTO facility_hours (
    facility_id,
    day_of_week,
    open_time,
    close_time,
    is_closed
)
SELECT
    id,
    day,
    TIME '08:00',
    TIME '18:00',
    FALSE
FROM facilities
CROSS JOIN generate_series(1, 6) AS day
WHERE name = 'LifeLine Demo Hospital'
ON CONFLICT (facility_id, day_of_week)
DO NOTHING;


INSERT INTO facility_hours (
    facility_id,
    day_of_week,
    open_time,
    close_time,
    is_closed
)
SELECT
    id,
    0,
    NULL,
    NULL,
    TRUE
FROM facilities
WHERE name = 'LifeLine Demo Hospital'
ON CONFLICT (facility_id, day_of_week)
DO NOTHING;


-- =========================================================
-- UPCOMING REGULAR APPOINTMENT
-- =========================================================

INSERT INTO appointments (
    donor_id,
    facility_id,
    donation_type,
    appointment_source,
    scheduled_at,
    status
)
SELECT
    u.id,
    f.id,
    'WHOLE_BLOOD',
    'REGULAR',
    TIMESTAMP '2026-10-02 10:30:00',
    'CONFIRMED'
FROM users u
CROSS JOIN facilities f
WHERE u.username = 'dofrostbyte'
  AND f.name = 'LifeLine Demo Hospital'
ON CONFLICT (donor_id, scheduled_at)
DO NOTHING;


-- =========================================================
-- OLD COMPLETED APPOINTMENT
-- Used to test donation history
-- =========================================================

INSERT INTO appointments (
    donor_id,
    facility_id,
    donation_type,
    appointment_source,
    scheduled_at,
    status
)
SELECT
    u.id,
    f.id,
    'PLATELETS',
    'REGULAR',
    TIMESTAMP '2026-09-10 14:15:00',
    'COMPLETED'
FROM users u
CROSS JOIN facilities f
WHERE u.username = 'dofrostbyte'
  AND f.name = 'LifeLine Demo Hospital'
ON CONFLICT (donor_id, scheduled_at)
DO NOTHING;


-- =========================================================
-- COMPLETED DONATION RECORD
-- =========================================================

INSERT INTO donations (
    appointment_id,
    actual_component_type,
    recorded_by,
    completed_at,
    notes
)
SELECT
    a.id,
    'PLATELETS',
    staff.id,
    TIMESTAMP '2026-09-10 14:45:00',
    'Development test donation'
FROM appointments a
JOIN users donor
    ON donor.id = a.donor_id
JOIN users staff
    ON staff.username = 'stteststaff'
WHERE donor.username = 'dofrostbyte'
  AND a.scheduled_at =
      TIMESTAMP '2026-09-10 14:15:00'
ON CONFLICT (appointment_id)
DO NOTHING;