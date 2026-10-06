-- ============================================================================
-- File: 005_seed_lab_mapping_rules.sql
-- Purpose: Seed one representative rectangular CIELAB candidate rule for each
--          of the 40 curated canonical colors.
-- Dependencies: 001_create_color_lexicon_schema.sql,
--               002_seed_canonical_colors.sql
-- Rerun behavior: Existing identical color/boundary rules are retained.
-- Scientific-status note: These are capstone-scale initialization rules derived
-- from representative centroids, not laboratory-validated garment calibration.
-- ============================================================================

BEGIN;

WITH seed(
    canonical_name, lab_l_min, lab_l_max, lab_a_min, lab_a_max, lab_b_min, lab_b_max
) AS (
    VALUES
    ('Black', 0.0, 6.0, -5.0, 5.0, -6.0, 6.0),
    ('Charcoal', 23.0, 35.0, -7.0, 3.0, -14.0, -2.0),
    ('Gray', 47.6, 59.6, -5.0, 5.0, -6.0, 6.0),
    ('Silver', 72.0, 84.0, -5.0, 5.0, -6.0, 6.0),
    ('White', 94.0, 100.0, -5.0, 5.0, -6.0, 6.0),
    ('Ivory', 92.0, 100.0, -7.0, 3.0, 2.0, 14.0),
    ('Cream', 91.0, 100.0, -10.0, 0.0, 12.0, 24.0),
    ('Beige', 76.0, 88.0, -2.0, 8.0, 15.0, 27.0),
    ('Tan', 68.0, 82.0, -2.0, 14.0, 13.0, 33.0),
    ('Brown', 30.5, 44.5, 18.4, 34.4, 30.9, 50.9),
    ('Chocolate', 21.0, 35.0, 6.0, 22.0, 16.0, 36.0),
    ('Red', 46.0, 60.0, 70.0, 90.0, 57.0, 77.0),
    ('Scarlet', 47.0, 61.0, 69.0, 89.0, 59.0, 79.0),
    ('Crimson', 40.0, 54.0, 60.0, 80.0, 23.0, 43.0),
    ('Burgundy', 19.0, 33.0, 38.0, 58.0, 2.0, 22.0),
    ('Coral Red', 61.0, 75.0, 39.0, 59.0, 21.0, 41.0),
    ('Orange', 67.0, 81.0, 14.0, 32.0, 68.0, 88.0),
    ('Peach', 84.0, 98.0, -4.0, 14.0, 17.0, 37.0),
    ('Yellow', 91.0, 100.0, -31.0, -13.0, 84.0, 104.0),
    ('Butter Yellow', 83.0, 95.0, -17.0, 1.0, 38.0, 58.0),
    ('Gold', 80.0, 92.0, -10.0, 8.0, 77.0, 97.0),
    ('Green', 39.0, 53.0, -62.0, -42.0, 40.0, 60.0),
    ('Olive', 45.0, 59.0, -20.0, 0.0, 35.0, 55.0),
    ('Sage', 63.0, 77.0, -18.0, 2.0, 8.0, 28.0),
    ('Mint', 84.0, 98.0, -55.0, -35.0, 16.0, 36.0),
    ('Emerald', 65.0, 79.0, -58.0, -38.0, 18.0, 38.0),
    ('Lime', 82.0, 96.0, -64.0, -44.0, 75.0, 95.0),
    ('Blue', 25.0, 39.0, 69.0, 89.0, -119.0, -97.0),
    ('Navy', 6.0, 20.0, 28.0, 48.0, -63.0, -41.0),
    ('Cobalt Blue', 27.0, 41.0, 8.0, 28.0, -74.0, -52.0),
    ('Azure', 48.0, 62.0, 8.0, 28.0, -81.0, -59.0),
    ('Sky Blue', 72.0, 86.0, -24.0, -4.0, -33.0, -11.0),
    ('Denim Blue', 35.0, 49.0, -8.0, 12.0, -62.0, -40.0),
    ('Purple', 22.0, 36.0, 48.0, 68.0, -47.0, -25.0),
    ('Violet', 33.0, 47.0, 73.0, 93.0, -104.0, -82.0),
    ('Lavender', 85.0, 99.0, -6.0, 14.0, -19.0, 3.0),
    ('Pink', 76.6, 90.6, 14.1, 34.1, -5.7, 12.3),
    ('Powder Pink', 82.0, 96.0, 1.0, 21.0, -6.0, 12.0),
    ('Fuchsia', 53.0, 67.0, 88.0, 108.0, -70.0, -52.0),
    ('Rose Pink', 60.0, 74.0, 53.0, 73.0, -19.0, -1.0)
), resolved AS (
    SELECT c.color_id,
           s.lab_l_min::REAL, s.lab_l_max::REAL,
           s.lab_a_min::REAL, s.lab_a_max::REAL,
           s.lab_b_min::REAL, s.lab_b_max::REAL
    FROM seed s
    JOIN public.color_canonical c ON c.canonical_name = s.canonical_name
)
INSERT INTO public.color_lab_mapping_rules (
    color_id, lab_l_min, lab_l_max, lab_a_min, lab_a_max, lab_b_min, lab_b_max
)
SELECT color_id, lab_l_min, lab_l_max, lab_a_min, lab_a_max, lab_b_min, lab_b_max
FROM resolved
ON CONFLICT (
    color_id, lab_l_min, lab_l_max, lab_a_min, lab_a_max, lab_b_min, lab_b_max
) DO NOTHING;

COMMIT;
