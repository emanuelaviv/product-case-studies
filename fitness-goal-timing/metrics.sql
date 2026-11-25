-- SYNTHETIC portfolio exercise. All assigned accounts remain in denominators.
SELECT
    arm,
    COUNT(*) AS assigned_accounts,
    SUM(CASE WHEN week4_workout_day BETWEEN 22 AND 28 THEN 1 ELSE 0 END) AS retention_w4,
    SUM(CASE WHEN first_workout_day BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS first_workout_d7,
    SUM(CASE WHEN first_paid_day BETWEEN 0 AND 28 THEN 1 ELSE 0 END) AS paid_d28,
    SUM(CASE WHEN onboarding_error_day BETWEEN 0 AND 7 THEN 1 ELSE 0 END) AS error_d7
FROM accounts
GROUP BY arm;
