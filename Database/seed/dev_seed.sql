-- =====================================================
-- LifeLine Development Seed Data (corrected for V1-V7)
-- For local testing only
-- =====================================================

-- FACILITY
INSERT INTO facilities (
    name,
    facility_type,
    phone,
    country,
    street_address,
    city,
    province,
    postal_code,
    latitude,
    longitude
)
VALUES (
    'LifeLine Demo Hospital',
    'HOSPITAL',
    '306-555-0100',
    'Canada',
    '123 Demo Street',
    'Regina',
    'Saskatchewan',
    'S4P 0A1',
    50.4452,
    -104.6189
)
ON CONFLICT (name, postal_code) DO NOTHING;

-- DONOR USER
INSERT INTO users (
    username,
    email,
    password_hash,
    first_name,
    last_name,
    role,
    account_status,
    terms_accepted_at
)
VALUES (
    'dofrostbyte',
    'donor@example.com',
    'TEST_PASSWORD_HASH',
    'Alex',
    'Donor',
    'DONOR',
    'ACTIVE',
    CURRENT_TIMESTAMP
)
ON CONFLICT (username) DO NOTHING;

-- DONOR PROFILE
INSERT INTO donor_profiles (
    user_id,
    phone,
    date_of_birth,
    blood_type,
    street_address,
    city,
    province,
    postal_code,
    latitude,
    longitude,
    emergency_available,
    country
)
SELECT
    id,
    '306-555-0200',
    DATE '2000-01-01',
    'O+',
    '456 Donor Avenue',
    'Regina',
    'Saskatchewan',
    'S4P 0A1',
    50.4500,
    -104.6100,
    TRUE,
    'Canada'
FROM users
WHERE username = 'dofrostbyte'
ON CONFLICT (user_id) DO NOTHING;

-- HOSPITAL STAFF USER
INSERT INTO users (
    username,
    email,
    password_hash,
    first_name,
    last_name,
    role,
    account_status,
    terms_accepted_at
)
VALUES (
    'stteststaff',
    'staff@example.com',
    'TEST_PASSWORD_HASH',
    'Test',
    'Staff',
    'HOSPITAL_STAFF',
    'ACTIVE',
    CURRENT_TIMESTAMP
)
ON CONFLICT (username) DO NOTHING;

-- STAFF PROFILE
-- authorization_declared_at records the self-declaration checkbox timestamp.
INSERT INTO staff_profiles (
    user_id,
    facility_id,
    authorization_declared_at
)
SELECT
    u.id,
    f.id,
    CURRENT_TIMESTAMP
FROM users u
JOIN facilities f
    ON f.name = 'LifeLine Demo Hospital'
   AND f.postal_code = 'S4P 0A1'
WHERE u.username = 'stteststaff'
ON CONFLICT (user_id) DO NOTHING;
