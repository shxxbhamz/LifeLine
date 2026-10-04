-- =========================================================
-- LifeLine Database
-- Migration V8 - Final schema cleanup before backend integration
-- =========================================================

-- 1) Emergency-request idempotency.
-- Backend should generate one unique key per form submission.
ALTER TABLE emergency_requests
ADD COLUMN idempotency_key VARCHAR(64);

ALTER TABLE emergency_requests
ADD CONSTRAINT uq_emergency_idempotency_key
UNIQUE (idempotency_key);


-- 2) LifeLine's current notification plan is email-only.
-- Remove the old channel check, normalize existing development rows,
-- and make EMAIL the database default.
ALTER TABLE notifications
DROP CONSTRAINT IF EXISTS notifications_delivery_channel_check;

UPDATE notifications
SET delivery_channel = 'EMAIL'
WHERE delivery_channel <> 'EMAIL';

ALTER TABLE notifications
ALTER COLUMN delivery_channel SET DEFAULT 'EMAIL';

ALTER TABLE notifications
ADD CONSTRAINT notifications_delivery_channel_check
CHECK (delivery_channel IN ('EMAIL'));


-- 3) Tighten screening completion consistency.
-- Repair any old completed development records first.
UPDATE eligibility_screenings
SET completed_at = COALESCE(completed_at, started_at)
WHERE status = 'COMPLETED';

ALTER TABLE eligibility_screenings
DROP CONSTRAINT IF EXISTS chk_screening_completion;

ALTER TABLE eligibility_screenings
ADD CONSTRAINT chk_screening_completion
CHECK (
    (status = 'IN_PROGRESS' AND completed_at IS NULL)
    OR
    (status = 'COMPLETED' AND completed_at IS NOT NULL)
    OR
    (status = 'EXPIRED')
);


-- 4) Only hospital/blood-bank staff should be recorded as the
-- human actor changing inventory. NULL remains available for
-- automated/system transactions.
ALTER TABLE inventory_transactions
DROP CONSTRAINT IF EXISTS fk_inventory_transaction_user;

ALTER TABLE inventory_transactions
ADD CONSTRAINT fk_inventory_transaction_staff
FOREIGN KEY (changed_by)
REFERENCES staff_profiles(user_id);
