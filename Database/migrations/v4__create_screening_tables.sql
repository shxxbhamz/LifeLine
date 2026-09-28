-- =========================================================
-- LifeLine Database
-- Migration V4
-- Donor Preliminary Eligibility Screening
-- =========================================================


-- =========================================================
-- 1. SCREENING QUESTIONS
-- =========================================================
-- Stores the questionnaire itself.
-- Keeping questions in the database allows the frontend
-- questionnaire to change without redesigning the schema.
-- =========================================================

CREATE TABLE screening_questions (
    id BIGSERIAL PRIMARY KEY,

    question_code VARCHAR(50) NOT NULL UNIQUE,

    question_text TEXT NOT NULL,

    answer_type VARCHAR(20) NOT NULL
        CHECK (
            answer_type IN (
                'BOOLEAN',
                'TEXT',
                'DATE',
                'NUMBER'
            )
        ),

    is_required BOOLEAN NOT NULL DEFAULT TRUE,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    display_order INTEGER NOT NULL
        CHECK (display_order >= 0),

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 2. ELIGIBILITY SCREENINGS
-- =========================================================
-- One row represents one questionnaire attempt/session.
-- =========================================================

CREATE TABLE eligibility_screenings (
    id BIGSERIAL PRIMARY KEY,

    donor_id BIGINT NOT NULL,

    -- Why the screening was started.
    screening_type VARCHAR(30) NOT NULL
        DEFAULT 'GENERAL'
        CHECK (
            screening_type IN (
                'GENERAL',
                'PRE_APPOINTMENT',
                'EMERGENCY'
            )
        ),

    -- Optional connection to an appointment.
    appointment_id BIGINT,

    status VARCHAR(20) NOT NULL
        DEFAULT 'IN_PROGRESS'
        CHECK (
            status IN (
                'IN_PROGRESS',
                'COMPLETED',
                'EXPIRED'
            )
        ),

    -- This is only a preliminary system result.
    preliminary_result VARCHAR(30) NOT NULL
        DEFAULT 'PENDING'
        CHECK (
            preliminary_result IN (
                'PENDING',
                'PRELIMINARY_ELIGIBLE',
                'REVIEW_REQUIRED',
                'TEMPORARILY_INELIGIBLE'
            )
        ),

    -- Helps us know which backend rule set evaluated it.
    rules_version VARCHAR(30)
        NOT NULL DEFAULT 'V1',

    started_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMP,

    valid_until TIMESTAMP,

    CONSTRAINT fk_screening_donor
        FOREIGN KEY (donor_id)
        REFERENCES donor_profiles(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_screening_appointment
        FOREIGN KEY (appointment_id)
        REFERENCES appointments(id)
        ON DELETE SET NULL,

    CONSTRAINT chk_screening_completion
        CHECK (
            (
                status = 'IN_PROGRESS'
                AND completed_at IS NULL
            )
            OR
            (
                status IN ('COMPLETED', 'EXPIRED')
            )
        )
);


-- =========================================================
-- 3. SCREENING ANSWERS
-- =========================================================
-- Stores each donor response.
-- =========================================================

CREATE TABLE screening_answers (
    id BIGSERIAL PRIMARY KEY,

    screening_id BIGINT NOT NULL,

    question_id BIGINT NOT NULL,

    -- Stored as text so different question types can be
    -- represented. Backend validates according to
    -- screening_questions.answer_type.
    answer_value VARCHAR(255) NOT NULL,

    -- Backend may flag an answer for staff review.
    is_flagged BOOLEAN NOT NULL DEFAULT FALSE,

    flag_reason VARCHAR(255),

    answered_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_answer_screening
        FOREIGN KEY (screening_id)
        REFERENCES eligibility_screenings(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_answer_question
        FOREIGN KEY (question_id)
        REFERENCES screening_questions(id),

    -- Prevent answering the same question twice
    -- within one screening.
    CONSTRAINT uq_screening_question
        UNIQUE (screening_id, question_id),

    CONSTRAINT chk_flag_reason
        CHECK (
            is_flagged = TRUE
            OR flag_reason IS NULL
        )
);


-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_screenings_donor
    ON eligibility_screenings(donor_id);

CREATE INDEX idx_screenings_donor_status
    ON eligibility_screenings(
        donor_id,
        status
    );

CREATE INDEX idx_screenings_result
    ON eligibility_screenings(
        preliminary_result
    );

CREATE INDEX idx_screenings_appointment
    ON eligibility_screenings(
        appointment_id
    );

CREATE INDEX idx_screening_answers_screening
    ON screening_answers(
        screening_id
    );

CREATE INDEX idx_screening_questions_active
    ON screening_questions(
        is_active,
        display_order
    );