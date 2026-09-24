-- ============================================================================
-- File: 004_seed_color_hierarchy.sql
-- Purpose: Seed one-level hue-to-shade rollup relationships.
-- Dependencies: 001_create_color_lexicon_schema.sql,
--               002_seed_canonical_colors.sql
-- Rerun behavior: Existing parent-child pairs are retained.
-- ============================================================================

BEGIN;

WITH seed(parent_name, child_name) AS (
    VALUES
    ('Black', 'Charcoal'),
    ('Gray', 'Silver'),
    ('White', 'Ivory'),
    ('White', 'Cream'),
    ('Brown', 'Beige'),
    ('Brown', 'Tan'),
    ('Brown', 'Chocolate'),
    ('Red', 'Scarlet'),
    ('Red', 'Crimson'),
    ('Red', 'Burgundy'),
    ('Red', 'Coral Red'),
    ('Orange', 'Peach'),
    ('Yellow', 'Butter Yellow'),
    ('Yellow', 'Gold'),
    ('Green', 'Olive'),
    ('Green', 'Sage'),
    ('Green', 'Mint'),
    ('Green', 'Emerald'),
    ('Green', 'Lime'),
    ('Blue', 'Navy'),
    ('Blue', 'Cobalt Blue'),
    ('Blue', 'Azure'),
    ('Blue', 'Sky Blue'),
    ('Blue', 'Denim Blue'),
    ('Purple', 'Violet'),
    ('Purple', 'Lavender'),
    ('Pink', 'Powder Pink'),
    ('Pink', 'Fuchsia'),
    ('Pink', 'Rose Pink')
), resolved AS (
    SELECT parent.color_id AS parent_color_id,
           child.color_id AS child_color_id
    FROM seed s
    JOIN public.color_canonical parent ON parent.canonical_name = s.parent_name
    JOIN public.color_canonical child ON child.canonical_name = s.child_name
)
INSERT INTO public.color_hierarchy (parent_color_id, child_color_id)
SELECT parent_color_id, child_color_id
FROM resolved
ON CONFLICT (parent_color_id, child_color_id) DO NOTHING;

COMMIT;
