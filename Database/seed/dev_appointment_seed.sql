-- =========================================================
-- LifeLine Appointment Development Seed Data (date-safe)
-- =========================================================

-- Facility hours: Monday-Saturday 8AM-6PM, Sunday closed
INSERT INTO facility_hours (
    facility_id, day_of_week, open_time, close_time, is_closed
)
SELECT id, day, TIME '08:00', TIME '18:00', FALSE
FROM facilities
CROSS JOIN generate_series(1, 6) AS day
WHERE name = 'LifeLine Demo Hospital'
ON CONFLICT (facility_id, day_of_week) DO NOTHING;

INSERT INTO facility_hours (
    facility_id, day_of_week, open_time, close_time, is_closed
)
SELECT id, 0, NULL, NULL, TRUE
FROM facilities
WHERE name = 'LifeLine Demo Hospital'
ON CONFLICT (facility_id, day_of_week) DO NOTHING;

-- Upcoming appointment: always 7 days from the day seed is run
INSERT INTO appointments (
    donor_id, facility_id, donation_type, appointment_source, scheduled_at, status
)
SELECT
    u.id,
    f.id,
    'WHOLE_BLOOD',
    'REGULAR',
    (CURRENT_DATE + 7) + TIME '10:30',
    'CONFIRMED'
FROM users u
CROSS JOIN facilities f
WHERE u.username = 'dofrostbyte'
  AND f.name = 'LifeLine Demo Hospital'
ON CONFLICT (donor_id, scheduled_at) DO NOTHING;

-- Completed appointment: 30 days ago
INSERT INTO appointments (
    donor_id, facility_id, donation_type, appointment_source, scheduled_at, status
)
SELECT
    u.id,
    f.id,
    'PLATELETS',
    'REGULAR',
    (CURRENT_DATE - 30) + TIME '14:15',
    'COMPLETED'
FROM users u
CROSS JOIN facilities f
WHERE u.username = 'dofrostbyte'
  AND f.name = 'LifeLine Demo Hospital'
ON CONFLICT (donor_id, scheduled_at) DO NOTHING;

-- Donation record for the completed appointment
INSERT INTO donations (
    appointment_id, actual_component_type, recorded_by, completed_at, notes
)
SELECT
    a.id,
    'PLATELETS',
    staff.id,
    (CURRENT_DATE - 30) + TIME '14:45',
    'Development test donation'
FROM appointments a
JOIN users donor ON donor.id = a.donor_id
JOIN users staff ON staff.username = 'stteststaff'
WHERE donor.username = 'dofrostbyte'
  AND a.scheduled_at = (CURRENT_DATE - 30) + TIME '14:15'
ON CONFLICT (appointment_id) DO NOTHING;
