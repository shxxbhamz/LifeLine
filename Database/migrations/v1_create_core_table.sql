-- =========================================================
-- LifeLine Database
-- Migration V1
-- Core user and facility tables
-- =========================================================


-- =========================
-- USERS
-- =========================

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,

    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60) NOT NULL,

    role VARCHAR(20) NOT NULL
        CHECK (role IN ('DONOR', 'HOSPITAL_STAFF')),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =========================
-- FACILITIES
-- =========================

CREATE TABLE facilities (
    id BIGSERIAL PRIMARY KEY,

    name VARCHAR(150) NOT NULL,

    facility_type VARCHAR(30) NOT NULL
        CHECK (
            facility_type IN (
                'HOSPITAL',
                'BLOOD_BANK'
            )
        ),

    address VARCHAR(255),
    city VARCHAR(100),
    province VARCHAR(50),
    postal_code VARCHAR(10),

    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),

    phone VARCHAR(20),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =========================
-- DONOR PROFILES
-- =========================

CREATE TABLE donor_profiles (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL UNIQUE,

    blood_type VARCHAR(3) NOT NULL
        CHECK (
            blood_type IN (
                'A+', 'A-',
                'B+', 'B-',
                'AB+', 'AB-',
                'O+', 'O-'
            )
        ),

    phone VARCHAR(20),

    city VARCHAR(100),
    postal_code VARCHAR(10),

    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),

    last_donation_date DATE,
    next_eligible_date DATE,

    emergency_available BOOLEAN NOT NULL DEFAULT TRUE,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- =========================
-- STAFF PROFILES
-- =========================

CREATE TABLE staff_profiles (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL UNIQUE,
    facility_id BIGINT NOT NULL,

    position VARCHAR(100),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (facility_id)
        REFERENCES facilities(id)
);