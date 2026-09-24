-- ============================================================================
-- File: 002_seed_canonical_colors.sql
-- Purpose: Seed/update the curated 40-color capstone reference subset.
-- Dependencies: 001_create_color_lexicon_schema.sql
-- Rerun behavior: Deterministic upsert by canonical_name; stable color_id values
--                 are preserved for existing production rows.
-- ============================================================================

BEGIN;

INSERT INTO public.color_canonical (
    canonical_name, color_family, hex_reference, lab_l, lab_a, lab_b
)
VALUES
    ('Black', 'neutral', '#000000', 0.0, 0.0, 0.0),
    ('Charcoal', 'neutral', '#36454F', 29.0, -2.0, -8.0),
    ('Gray', 'neutral', '#808080', 53.6, 0.0, 0.0),
    ('Silver', 'neutral', '#C0C0C0', 78.0, 0.0, 0.0),
    ('White', 'neutral', '#FFFFFF', 100.0, 0.0, 0.0),
    ('Ivory', 'neutral', '#FFFFF0', 98.0, -2.0, 8.0),
    ('Cream', 'neutral', '#FFFDD0', 97.0, -5.0, 18.0),
    ('Beige', 'neutral', '#DCC7A1', 82.0, 3.0, 21.0),
    ('Tan', 'brown', '#D2B48C', 75.0, 6.0, 23.0),
    ('Brown', 'brown', '#8B4513', 37.5, 26.4, 40.9),
    ('Chocolate', 'brown', '#5D3A1A', 28.0, 14.0, 26.0),
    ('Red', 'red', '#FF0000', 53.0, 80.0, 67.0),
    ('Scarlet', 'red', '#FF2400', 54.0, 79.0, 69.0),
    ('Crimson', 'red', '#DC143C', 47.0, 70.0, 33.0),
    ('Burgundy', 'red', '#800020', 26.0, 48.0, 12.0),
    ('Coral Red', 'red', '#FF6F61', 68.0, 49.0, 31.0),
    ('Orange', 'orange', '#FFA500', 74.0, 23.0, 78.0),
    ('Peach', 'orange', '#FFE5B4', 91.0, 5.0, 27.0),
    ('Yellow', 'yellow', '#FFFF00', 97.0, -22.0, 94.0),
    ('Butter Yellow', 'yellow', '#F6E27F', 89.0, -8.0, 48.0),
    ('Gold', 'yellow', '#FFD700', 86.0, -1.0, 87.0),
    ('Green', 'green', '#008000', 46.0, -52.0, 50.0),
    ('Olive', 'green', '#808000', 52.0, -10.0, 45.0),
    ('Sage', 'green', '#B2AC88', 70.0, -8.0, 18.0),
    ('Mint', 'green', '#98FF98', 91.0, -45.0, 26.0),
    ('Emerald', 'green', '#50C878', 72.0, -48.0, 28.0),
    ('Lime', 'green', '#BFFF00', 89.0, -54.0, 85.0),
    ('Blue', 'blue', '#0000FF', 32.0, 79.0, -108.0),
    ('Navy', 'blue', '#000080', 13.0, 38.0, -52.0),
    ('Cobalt Blue', 'blue', '#0047AB', 34.0, 18.0, -63.0),
    ('Azure', 'blue', '#007FFF', 55.0, 18.0, -70.0),
    ('Sky Blue', 'blue', '#87CEEB', 79.0, -14.0, -22.0),
    ('Denim Blue', 'blue', '#1560BD', 42.0, 2.0, -51.0),
    ('Purple', 'purple', '#800080', 29.0, 58.0, -36.0),
    ('Violet', 'purple', '#8F00FF', 40.0, 83.0, -93.0),
    ('Lavender', 'purple', '#E6E6FA', 92.0, 4.0, -8.0),
    ('Pink', 'pink', '#FFC0CB', 83.6, 24.1, 3.3),
    ('Powder Pink', 'pink', '#FADADD', 89.0, 11.0, 3.0),
    ('Fuchsia', 'pink', '#FF00FF', 60.0, 98.0, -61.0),
    ('Rose Pink', 'pink', '#FF66CC', 67.0, 63.0, -10.0)
ON CONFLICT (canonical_name) DO UPDATE SET
    color_family = EXCLUDED.color_family,
    hex_reference = EXCLUDED.hex_reference,
    lab_l = EXCLUDED.lab_l,
    lab_a = EXCLUDED.lab_a,
    lab_b = EXCLUDED.lab_b;

COMMIT;
