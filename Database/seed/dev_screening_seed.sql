-- =========================================================
-- LifeLine Screening Development Seed Data
-- =========================================================


-- =========================================================
-- DEMO SCREENING QUESTIONS
-- =========================================================
-- These are demonstration questions only.
-- Final medical eligibility is not determined by LifeLine.
-- =========================================================

INSERT INTO screening_questions (
    question_code,
    question_text,
    answer_type,
    is_required,
    display_order
)
VALUES

(
    'FEELING_WELL',
    'Are you feeling well today?',
    'BOOLEAN',
    TRUE,
    1
),

(
    'RECENT_DONATION',
    'Have you made a recent blood, plasma, or platelet donation?',
    'BOOLEAN',
    TRUE,
    2
),

(
    'RECENT_TRAVEL',
    'Have you travelled recently in a way that may require additional eligibility review?',
    'BOOLEAN',
    TRUE,
    3
),

(
    'RECENT_PROCEDURE',
    'Have you recently had a medical or dental procedure that may require additional review?',
    'BOOLEAN',
    TRUE,
    4
),

(
    'ADDITIONAL_INFORMATION',
    'Is there any additional information you would like staff to review?',
    'TEXT',
    FALSE,
    5
)

ON CONFLICT (question_code)
DO NOTHING;


-- =========================================================
-- CREATE A DEMO SCREENING
-- =========================================================

INSERT INTO eligibility_screenings (
    donor_id,
    screening_type,
    status,
    preliminary_result,
    rules_version,
    completed_at
)
SELECT
    u.id,
    'GENERAL',
    'COMPLETED',
    'PRELIMINARY_ELIGIBLE',
    'V1',
    CURRENT_TIMESTAMP
FROM users u
WHERE u.username = 'dofrostbyte'
  AND NOT EXISTS (
      SELECT 1
      FROM eligibility_screenings es
      WHERE es.donor_id = u.id
        AND es.screening_type = 'GENERAL'
  );


-- =========================================================
-- DEMO ANSWERS
-- =========================================================

INSERT INTO screening_answers (
    screening_id,
    question_id,
    answer_value,
    is_flagged
)
SELECT
    es.id,
    sq.id,

    CASE sq.question_code

        WHEN 'FEELING_WELL'
            THEN 'true'

        WHEN 'RECENT_DONATION'
            THEN 'false'

        WHEN 'RECENT_TRAVEL'
            THEN 'false'

        WHEN 'RECENT_PROCEDURE'
            THEN 'false'

        WHEN 'ADDITIONAL_INFORMATION'
            THEN 'None'

    END,

    FALSE

FROM eligibility_screenings es
JOIN users u
    ON es.donor_id = u.id

CROSS JOIN screening_questions sq

WHERE u.username = 'dofrostbyte'
  AND es.screening_type = 'GENERAL'

ON CONFLICT (
    screening_id,
    question_id
)
DO NOTHING;