-- =========================================================
-- LifeLine Database
-- Migration V2
-- Emergency Requests, Donor Matching and Notifications
-- =========================================================


-- =========================================================
-- 1. EMERGENCY REQUESTS
-- =========================================================

CREATE TABLE emergency_requests (
    id BIGSERIAL PRIMARY KEY,

    -- Hospital / blood bank making the request
    facility_id BIGINT NOT NULL,

    -- Specific authorized staff member who created it
    created_by BIGINT NOT NULL,

    required_blood_type VARCHAR(3) NOT NULL
        CHECK (
            required_blood_type IN (
                'A+', 'A-',
                'B+', 'B-',
                'AB+', 'AB-',
                'O+', 'O-', 'ANY'
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

    urgency VARCHAR(20) NOT NULL
        CHECK (
            urgency IN (
                'URGENT',
                'CRITICAL'
            )
        ),

    -- Maximum geographic search distance
    radius_km DECIMAL(6,2) NOT NULL DEFAULT 25
        CHECK (radius_km > 0),

    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (
            status IN (
                'OPEN',
                'MATCHING',
                'ACTIVE',
                'FULFILLED',
                'CANCELLED',
                'EXPIRED'
            )
        ),

    notes TEXT,

    expires_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fulfilled_at TIMESTAMP,

    CONSTRAINT fk_emergency_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(id),

    CONSTRAINT fk_emergency_staff
        FOREIGN KEY (created_by)
        REFERENCES staff_profiles(user_id)
);


-- =========================================================
-- 2. REQUEST MATCHES
-- =========================================================
-- Stores which donors were selected by the matching system
-- for each emergency request.
-- =========================================================

CREATE TABLE request_matches (
    id BIGSERIAL PRIMARY KEY,

    request_id BIGINT NOT NULL,

    -- References donor_profiles instead of generic users
    -- so only actual donors can be matched.
    donor_id BIGINT NOT NULL,

    distance_km DECIMAL(7,2)
        CHECK (
            distance_km IS NULL
            OR distance_km >= 0
        ),

    match_score DECIMAL(7,2),

    notification_status VARCHAR(20)
        NOT NULL DEFAULT 'PENDING'
        CHECK (
            notification_status IN (
                'PENDING',
                'SENT',
                'VIEWED',
                'FAILED'
            )
        ),

    response_status VARCHAR(20)
        NOT NULL DEFAULT 'PENDING'
        CHECK (
            response_status IN (
                'PENDING',
                'ACCEPTED',
                'DECLINED',
                'EXPIRED'
            )
        ),

    matched_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    notified_at TIMESTAMP,

    viewed_at TIMESTAMP,

    responded_at TIMESTAMP,

    CONSTRAINT fk_match_request
        FOREIGN KEY (request_id)
        REFERENCES emergency_requests(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_match_donor
        FOREIGN KEY (donor_id)
        REFERENCES donor_profiles(user_id)
        ON DELETE CASCADE,

    -- Prevent one donor being matched twice
    -- to the same emergency
    CONSTRAINT uq_request_donor
        UNIQUE (request_id, donor_id)
);


-- =========================================================
-- 3. NOTIFICATIONS
-- =========================================================

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL,

    emergency_request_id BIGINT,

    request_match_id BIGINT,

    notification_type VARCHAR(30) NOT NULL
        CHECK (
            notification_type IN (
                'EMERGENCY_ALERT',
                'REQUEST_UPDATE',
                'REQUEST_FULFILLED',
                'SYSTEM'
            )
        ),

    title VARCHAR(150) NOT NULL,

    message TEXT NOT NULL,

    delivery_channel VARCHAR(20)
        NOT NULL DEFAULT 'IN_APP'
        CHECK (
            delivery_channel IN (
                'IN_APP',
                'SMS',
                'PUSH'
            )
        ),

    delivery_status VARCHAR(20)
        NOT NULL DEFAULT 'PENDING'
        CHECK (
            delivery_status IN (
                'PENDING',
                'SENT',
                'FAILED'
            )
        ),

    retry_count INTEGER NOT NULL DEFAULT 0
        CHECK (retry_count >= 0),

    is_read BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    sent_at TIMESTAMP,

    read_at TIMESTAMP,

    CONSTRAINT fk_notification_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_notification_request
        FOREIGN KEY (emergency_request_id)
        REFERENCES emergency_requests(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_notification_match
        FOREIGN KEY (request_match_id)
        REFERENCES request_matches(id)
        ON DELETE CASCADE
);


-- =========================================================
-- INDEXES
-- =========================================================
-- These improve commonly used LifeLine queries.
-- =========================================================

CREATE INDEX idx_emergency_status
    ON emergency_requests(status);

CREATE INDEX idx_emergency_blood_component
    ON emergency_requests(
        required_blood_type,
        component_type
    );

CREATE INDEX idx_emergency_created_at
    ON emergency_requests(created_at);

CREATE INDEX idx_request_matches_request
    ON request_matches(request_id);

CREATE INDEX idx_request_matches_donor
    ON request_matches(donor_id);

CREATE INDEX idx_request_matches_response
    ON request_matches(
        request_id,
        response_status
    );

CREATE INDEX idx_notifications_user
    ON notifications(user_id);

CREATE INDEX idx_notifications_user_read
    ON notifications(
        user_id,
        is_read
    );