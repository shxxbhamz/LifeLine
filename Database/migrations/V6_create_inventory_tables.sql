-- =========================================================
-- LifeLine Database
-- Migration V6
-- Blood / Plasma / Platelet Inventory Management
-- =========================================================


-- =========================================================
-- 1. BLOOD INVENTORY
-- =========================================================

CREATE TABLE blood_inventory (
    id BIGSERIAL PRIMARY KEY,

    facility_id BIGINT NOT NULL,

    blood_type VARCHAR(3) NOT NULL
        CHECK (
            blood_type IN (
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

    units_available INTEGER NOT NULL DEFAULT 0
        CHECK (units_available >= 0),

    low_threshold INTEGER NOT NULL DEFAULT 5
        CHECK (low_threshold >= 0),

    critical_threshold INTEGER NOT NULL DEFAULT 2
        CHECK (critical_threshold >= 0),

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_inventory_facility
        FOREIGN KEY (facility_id)
        REFERENCES facilities(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_inventory_facility_blood_component
        UNIQUE (
            facility_id,
            blood_type,
            component_type
        ),

    CONSTRAINT chk_inventory_thresholds
        CHECK (
            critical_threshold <= low_threshold
        )
);


-- =========================================================
-- 2. INVENTORY TRANSACTION HISTORY
-- =========================================================

CREATE TABLE inventory_transactions (
    id BIGSERIAL PRIMARY KEY,

    inventory_id BIGINT NOT NULL,

    changed_by BIGINT,

    transaction_type VARCHAR(30) NOT NULL
        CHECK (
            transaction_type IN (
                'DONATION_RECEIVED',
                'EMERGENCY_DISPATCH',
                'MANUAL_ADJUSTMENT',
                'EXPIRED_DISCARDED',
                'OTHER'
            )
        ),

    -- Positive value = stock added
    -- Negative value = stock removed
    units_change INTEGER NOT NULL
        CHECK (units_change <> 0),

    reason VARCHAR(255),

    donation_id BIGINT,

    emergency_request_id BIGINT,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_inventory_transaction_inventory
        FOREIGN KEY (inventory_id)
        REFERENCES blood_inventory(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_inventory_transaction_user
        FOREIGN KEY (changed_by)
        REFERENCES users(id),

    CONSTRAINT fk_inventory_transaction_donation
        FOREIGN KEY (donation_id)
        REFERENCES donations(id),

    CONSTRAINT fk_inventory_transaction_emergency
        FOREIGN KEY (emergency_request_id)
        REFERENCES emergency_requests(id)
);


-- =========================================================
-- 3. DONATION QUANTITY
-- =========================================================
-- Used for progress such as "1 of 3 units collected."
-- =========================================================

ALTER TABLE donations
ADD COLUMN IF NOT EXISTS quantity_units INTEGER
    NOT NULL DEFAULT 1
    CHECK (quantity_units > 0);


-- =========================================================
-- 4. INVENTORY STATUS VIEW
-- =========================================================
-- NORMAL / LOW / CRITICAL is calculated rather than
-- permanently stored.
-- =========================================================

CREATE VIEW inventory_status_view AS
SELECT
    bi.id,
    bi.facility_id,
    f.name AS facility_name,
    bi.blood_type,
    bi.component_type,
    bi.units_available,
    bi.low_threshold,
    bi.critical_threshold,

    CASE
        WHEN bi.units_available <= bi.critical_threshold
            THEN 'CRITICAL'

        WHEN bi.units_available <= bi.low_threshold
            THEN 'LOW'

        ELSE 'NORMAL'
    END AS inventory_status,

    bi.updated_at

FROM blood_inventory bi

JOIN facilities f
    ON bi.facility_id = f.id;


-- =========================================================
-- 5. PERFORMANCE INDEXES
-- =========================================================

CREATE INDEX idx_inventory_facility
    ON blood_inventory(facility_id);


CREATE INDEX idx_inventory_lookup
    ON blood_inventory(
        facility_id,
        blood_type,
        component_type
    );


CREATE INDEX idx_inventory_transactions_inventory
    ON inventory_transactions(inventory_id);


CREATE INDEX idx_inventory_transactions_created
    ON inventory_transactions(created_at);


CREATE INDEX IF NOT EXISTS idx_donor_matching
    ON donor_profiles(
        blood_type,
        emergency_available
    );


CREATE INDEX IF NOT EXISTS idx_screening_latest
    ON eligibility_screenings(
        donor_id,
        completed_at DESC
    );