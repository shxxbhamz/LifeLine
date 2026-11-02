-- =========================================================
-- LifeLine Database
-- Migration V10
-- Link Emergency Screening Sessions to Request Matches
-- =========================================================


-- =========================================================
-- 1. ADD REQUEST MATCH REFERENCE
-- =========================================================
-- Emergency screenings happen before an emergency donation
-- appointment exists, so they must be linked directly to the
-- donor's request_matches row.
-- =========================================================

ALTER TABLE eligibility_screenings
ADD COLUMN request_match_id BIGINT;


-- =========================================================
-- 2. FOREIGN KEY
-- =========================================================

ALTER TABLE eligibility_screenings
ADD CONSTRAINT fk_screening_request_match
FOREIGN KEY (request_match_id)
REFERENCES request_matches(id)
ON DELETE CASCADE;


-- =========================================================
-- 3. EMERGENCY SCREENING CONSISTENCY
-- =========================================================
-- EMERGENCY screenings must belong to a request match.
-- Other screening types must not use request_match_id.
-- =========================================================

ALTER TABLE eligibility_screenings
ADD CONSTRAINT chk_screening_request_match
CHECK (
    (
        screening_type = 'EMERGENCY'
        AND request_match_id IS NOT NULL
    )
    OR
    (
        screening_type <> 'EMERGENCY'
        AND request_match_id IS NULL
    )
);


-- =========================================================
-- 4. INDEX
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_screenings_request_match
ON eligibility_screenings(request_match_id);

-- =========================================================
-- 5. PREVENT DUPLICATE ACTIVE EMERGENCY SCREENINGS
-- =========================================================
-- A donor may have multiple historical screening attempts,
-- but only one IN_PROGRESS emergency screening should exist
-- for a specific request match at a time.
-- =========================================================

CREATE UNIQUE INDEX IF NOT EXISTS
    uq_active_emergency_screening_per_match
ON eligibility_screenings(request_match_id)
WHERE
    screening_type = 'EMERGENCY'
    AND status = 'IN_PROGRESS';