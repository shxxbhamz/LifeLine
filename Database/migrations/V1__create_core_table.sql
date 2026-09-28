-- =====================================================
-- LifeLine Database
-- V1 - Core Tables
-- =====================================================


-- USERS
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,

    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60) NOT NULL,

    role VARCHAR(20) NOT NULL
        CHECK (
            role IN (
                'DONOR',
                'HOSPITAL_STAFF'
            )
        ),

    account_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (
            account_status IN (
                'ACTIVE',
                'PENDING',
                'SUSPENDED'
            )
        ),

    terms_accepted_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- FACILITIES
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

    phone VARCHAR(20) NOT NULL,

    country VARCHAR(80) NOT NULL,

    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    province VARCHAR(50) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,

    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (name, postal_code)
);


-- DONOR PROFILES
CREATE TABLE donor_profiles (
    user_id BIGINT PRIMARY KEY,

    phone VARCHAR(20) NOT NULL,

    date_of_birth DATE NOT NULL,

    blood_type VARCHAR(3) NOT NULL
        CHECK (
            blood_type IN (
                'A+', 'A-',
                'B+', 'B-',
                'AB+', 'AB-',
                'O+', 'O-'
            )
        ),

    street_address VARCHAR(255) NOT NULL,

    city VARCHAR(100) NOT NULL,
    province VARCHAR(50) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,

    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),

    last_donation_date DATE,
    next_eligible_date DATE,

    emergency_available BOOLEAN NOT NULL DEFAULT TRUE,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- STAFF PROFILES
CREATE TABLE staff_profiles (
    user_id BIGINT PRIMARY KEY,

    facility_id BIGINT NOT NULL,

    authorization_status VARCHAR(20)
        NOT NULL DEFAULT 'PENDING'
        CHECK (
            authorization_status IN (
                'PENDING',
                'VERIFIED',
                'REJECTED'
            )
        ),

    authorization_declared_at TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (facility_id)
        REFERENCES facilities(id)
);
