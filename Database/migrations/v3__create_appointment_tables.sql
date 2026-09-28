-- =========================================================
-- LifeLine Database
-- Migration V3
-- Facility Hours, Appointments and Donation History
-- =========================================================


-- =========================================================
-- 1. FACILITY HOURS
-- =========================================================
-- Allows the backend to determine when a hospital/blood
-- bank normally accepts donation appointments.
--
-- day_of_week:
-- 0 = Sunday
-- 1 = Monday
-- 2 = Tuesday
-- 3 = Wednesday
-- 4 = Thursday
-- 5 = Friday
-- 6 = Saturday
-- =========================================================

CREATE TABLE facility_hours (
    id BIGSERIAL PRIMARY KEY,

    facility_id BIGINT NOT NULL,

    day_of_week SMALLINT NOT NULL
        CHECK (day_of_week BETWEEN 0 AND 6),

    open_time TIME,
    close_time TIME,

    is_closed BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_hours_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_facility_day
        UNIQUE (facility_id, day_of_week),

    CONSTRAINT chk_facility_hours
        CHECK (
            (
                is_closed = TRUE
                AND open_time IS NULL
                AND close_time IS NULL
            )
            OR
            (
                is_closed = FALSE
                AND open_time IS NOT NULL
                AND close_time IS NOT NULL
                AND close_time > open_time
            )
        )
);


-- =========================================================
-- 2. APPOINTMENTS
-- =========================================================

CREATE TABLE appointments (
    id BIGSERIAL PRIMARY KEY,

    -- The donor attending the appointment
    donor_id BIGINT NOT NULL,

    -- Hospital or blood bank where donation occurs
    facility_id BIGINT NOT NULL,

    -- NULL for normal appointments.
    -- Set when appointment comes from an emergency match.
    request_match_id BIGINT,

    donation_type VARCHAR(30) NOT NULL
        CHECK (
            donation_type IN (
                'WHOLE_BLOOD',
                'RED_BLOOD_CELLS',
                'PLASMA',
                'PLATELETS'
            )
        ),

    appointment_source VARCHAR(20) NOT NULL
        DEFAULT 'REGULAR'
        CHECK (
            appointment_source IN (
                'REGULAR',
                'EMERGENCY'
            )
        ),

    scheduled_at TIMESTAMP NOT NULL,

    status VARCHAR(20) NOT NULL
        DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'CONFIRMED',
                'COMPLETED',
                'CANCELLED',
                'NO_SHOW'
            )
        ),

    -- Staff member who confirmed appointment
    confirmed_by BIGINT,

    notes TEXT,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    cancelled_at TIMESTAMP,

    CONSTRAINT fk_appointment_donor
        FOREIGN KEY (donor_id)
        REFERENCES donor_profiles(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_appointment_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(id),

    CONSTRAINT fk_appointment_match
        FOREIGN KEY (request_match_id)
        REFERENCES request_matches(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_appointment_confirmed_by
        FOREIGN KEY (confirmed_by)
        REFERENCES staff_profiles(user_id),

    -- A donor cannot have two appointments
    -- at exactly the same time.
    CONSTRAINT uq_donor_appointment_time
        UNIQUE (donor_id, scheduled_at),

    -- One emergency match cannot generate
    -- multiple appointments.
    CONSTRAINT uq_request_match_appointment
        UNIQUE (request_match_id),

    -- Emergency appointments require a match.
    -- Regular appointments must not have one.
    CONSTRAINT chk_appointment_source
        CHECK (
            (
                appointment_source = 'REGULAR'
                AND request_match_id IS NULL
            )
            OR
            (
                appointment_source = 'EMERGENCY'
                AND request_match_id IS NOT NULL
            )
        )
);


-- =========================================================
-- 3. DONATIONS
-- =========================================================
-- A donation record is created after an appointment
-- is successfully completed.
-- =========================================================

CREATE TABLE donations (
    id BIGSERIAL PRIMARY KEY,

    appointment_id BIGINT NOT NULL UNIQUE,

    actual_component_type VARCHAR(30) NOT NULL
        CHECK (
            actual_component_type IN (
                'WHOLE_BLOOD',
                'RED_BLOOD_CELLS',
                'PLASMA',
                'PLATELETS'
            )
        ),

    -- Staff member recording the completed donation
    recorded_by BIGINT,

    completed_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    notes TEXT,

    CONSTRAINT fk_donation_appointment
        FOREIGN KEY (appointment_id)
        REFERENCES appointments(id),

    CONSTRAINT fk_donation_recorded_by
        FOREIGN KEY (recorded_by)
        REFERENCES staff_profiles(user_id)
);


-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_appointments_donor
    ON appointments(donor_id);

CREATE INDEX idx_appointments_facility
    ON appointments(facility_id);

CREATE INDEX idx_appointments_scheduled
    ON appointments(scheduled_at);

CREATE INDEX idx_appointments_facility_status
    ON appointments(
        facility_id,
        status
    );

CREATE INDEX idx_appointments_donor_status
    ON appointments(
        donor_id,
        status
    );

CREATE INDEX idx_donations_completed
    ON donations(completed_at);