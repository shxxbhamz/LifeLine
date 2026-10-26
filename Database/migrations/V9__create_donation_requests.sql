-- =========================================================
-- LifeLine Database
-- Migration V9
-- Normal Donation Requests / Facility Restock Requests
-- =========================================================


-- =========================================================
-- 1. DONATION REQUESTS
-- =========================================================
-- Used when a hospital or blood bank wants donors to
-- replenish normal inventory.
--
-- This is separate from emergency_requests.
-- =========================================================

CREATE TABLE IF NOT EXISTS donation_requests (
    id BIGSERIAL PRIMARY KEY,

    -- Facility requesting donations
    facility_id BIGINT NOT NULL,

    -- Staff member who created the request
    created_by BIGINT NOT NULL,

    required_blood_type VARCHAR(3) NOT NULL
        CHECK (
            required_blood_type IN (
                'A+', 'A-',
                'B+', 'B-',
                'AB+', 'AB-',
                'O+', 'O-'
            )
        ),

    component_type VARCHAR(30) NOT NULL
        CHECK (
            component_type IN (
                'WHOLE_BLOOD',
                'RED_BLOOD_CELLS',
                'PLASMA',
                'PLATELETS'
            )
        ),

    units_required INTEGER NOT NULL
        CHECK (units_required > 0),

    status VARCHAR(20) NOT NULL
        DEFAULT 'OPEN'
        CHECK (
            status IN (
                'OPEN',
                'FULFILLED',
                'CANCELLED',
                'EXPIRED'
            )
        ),

    notes TEXT,

    expires_at TIMESTAMP,

    -- Protect against accidental duplicate form submissions
    idempotency_key VARCHAR(64) UNIQUE,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    fulfilled_at TIMESTAMP,

    CONSTRAINT fk_donation_request_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_donation_request_staff
        FOREIGN KEY (created_by)
        REFERENCES staff_profiles(user_id)
);


-- =========================================================
-- 2. LINK APPOINTMENTS TO DONATION REQUESTS
-- =========================================================

ALTER TABLE appointments
ADD COLUMN IF NOT EXISTS donation_request_id BIGINT;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_appointment_donation_request'
    ) THEN
        ALTER TABLE appointments
        ADD CONSTRAINT fk_appointment_donation_request
            FOREIGN KEY (donation_request_id)
            REFERENCES donation_requests(id)
            ON DELETE SET NULL;
    END IF;
END
$$;


-- =========================================================
-- 3. EXPAND APPOINTMENT SOURCE
-- =========================================================
-- REGULAR          = donor books normally
-- DONATION_REQUEST = donor responds to facility request
-- EMERGENCY        = donor responds to emergency match
-- =========================================================

ALTER TABLE appointments
DROP CONSTRAINT IF EXISTS chk_appointment_source;


ALTER TABLE appointments
DROP CONSTRAINT IF EXISTS appointments_appointment_source_check;


ALTER TABLE appointments
ADD CONSTRAINT chk_appointment_source
CHECK (
    (
        appointment_source = 'REGULAR'
        AND request_match_id IS NULL
        AND donation_request_id IS NULL
    )
    OR
    (
        appointment_source = 'DONATION_REQUEST'
        AND request_match_id IS NULL
        AND donation_request_id IS NOT NULL
    )
    OR
    (
        appointment_source = 'EMERGENCY'
        AND request_match_id IS NOT NULL
        AND donation_request_id IS NULL
    )
);


-- =========================================================
-- 4. INDEXES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_donation_requests_facility
    ON donation_requests(facility_id);


CREATE INDEX IF NOT EXISTS idx_donation_requests_status
    ON donation_requests(status);


CREATE INDEX IF NOT EXISTS idx_donation_requests_blood_component
    ON donation_requests(
        required_blood_type,
        component_type
    );


CREATE INDEX IF NOT EXISTS idx_appointments_donation_request
    ON appointments(donation_request_id);