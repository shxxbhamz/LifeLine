-- =====================================================
-- LifeLine Development Seed Data
-- For local testing only
-- =====================================================


-- -------------------------
-- FACILITIES
-- -------------------------

INSERT INTO facilities (
    name,
    facility_type,
    address,
    city,
    province,
    postal_code,
    latitude,
    longitude,
    phone
)
VALUES (
    'LifeLine Demo Hospital',
    'HOSPITAL',
    '123 Demo Street',
    'Regina',
    'Saskatchewan',
    'S4P 0A1',
    50.4452,
    -104.6189,
    '306-555-0100'
);


-- -------------------------
-- DONOR USER
-- -------------------------

INSERT INTO users (
    username,
    email,
    password_hash,
    first_name,
    last_name,
    role
)
VALUES (
    'dofrostbyte',
    'donor@example.com',
    'TEST_PASSWORD_HASH',
    'Alex',
    'Donor',
    'DONOR'
);


-- -------------------------
-- DONOR PROFILE
-- -------------------------

INSERT INTO donor_profiles (
    user_id,
    blood_type,
    phone,
    city,
    postal_code,
    latitude,
    longitude,
    emergency_available
)
SELECT
    id,
    'O+',
    '306-555-0200',
    'Regina',
    'S4P 0A1',
    50.4500,
    -104.6100,
    TRUE
FROM users
WHERE username = 'dofrostbyte';


-- -------------------------
-- HOSPITAL STAFF USER
-- -------------------------

INSERT INTO users (
    username,
    email,
    password_hash,
    first_name,
    last_name,
    role
)
VALUES (
    'stteststaff',
    'staff@example.com',
    'TEST_PASSWORD_HASH',
    'Test',
    'Staff',
    'HOSPITAL_STAFF'
);


-- -------------------------
-- STAFF PROFILE
-- -------------------------

INSERT INTO staff_profiles (
    user_id,
    facility_id,
    position
)
SELECT
    u.id,
    f.id,
    'Blood Bank Coordinator'
FROM users u
JOIN facilities f
    ON f.name = 'LifeLine Demo Hospital'
WHERE u.username = 'stteststaff';