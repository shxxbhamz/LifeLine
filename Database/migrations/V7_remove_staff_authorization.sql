-- =========================================================
-- LifeLine Database
-- Migration V7
-- Remove unused staff authorization workflow
-- =========================================================

ALTER TABLE staff_profiles
DROP COLUMN IF EXISTS authorization_status;