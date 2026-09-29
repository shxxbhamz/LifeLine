-- =====================================================
-- LifeLine Database
-- V5 - Add country to donor profiles
-- =====================================================

ALTER TABLE donor_profiles
ADD COLUMN country VARCHAR(80) NOT NULL DEFAULT 'Canada';