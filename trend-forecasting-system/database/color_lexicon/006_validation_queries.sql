-- ============================================================================
-- File: 006_validation_queries.sql
-- Purpose: Execute data-quality checks and provide representative lookup and
--          analytics queries for the Color Lexicon module.
-- Dependencies: 001 through 005.
-- Passing convention: problem_count = 0 unless expected_result says otherwise.
-- This script is read-only apart from a transaction-local temporary table.
-- ============================================================================

BEGIN;

CREATE TEMP TABLE color_lexicon_validation_results (
    query_name TEXT NOT NULL,
    validation_purpose TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    actual_result BIGINT NOT NULL,
    status TEXT NOT NULL,
    failure_meaning TEXT NOT NULL
) ON COMMIT DROP;

-- Record counts: passing means each required table is populated; counts are
-- reported individually because pre-existing canonical rows may exceed 40.
INSERT INTO color_lexicon_validation_results VALUES
('count_color_canonical', 'Record count for color_canonical', 'At least 40', (SELECT count(*) FROM public.color_canonical), CASE WHEN (SELECT count(*) FROM public.color_canonical) >= 40 THEN 'PASS' ELSE 'FAIL' END, 'Canonical seed is incomplete.'),
('count_color_lexicon', 'Record count for color_lexicon', 'At least 500', (SELECT count(*) FROM public.color_lexicon), CASE WHEN (SELECT count(*) FROM public.color_lexicon) >= 500 THEN 'PASS' ELSE 'FAIL' END, 'Lexicon seed is incomplete.'),
('count_color_hierarchy', 'Record count for color_hierarchy', 'At least 29', (SELECT count(*) FROM public.color_hierarchy), CASE WHEN (SELECT count(*) FROM public.color_hierarchy) >= 29 THEN 'PASS' ELSE 'FAIL' END, 'Hierarchy seed is incomplete.'),
('count_color_lab_mapping_rules', 'Record count for LAB rules', 'At least 40', (SELECT count(*) FROM public.color_lab_mapping_rules), CASE WHEN (SELECT count(*) FROM public.color_lab_mapping_rules) >= 40 THEN 'PASS' ELSE 'FAIL' END, 'LAB rule seed is incomplete.');

-- Duplicate canonical names: passing result is zero; nonzero means uniqueness
-- has been bypassed or inconsistent case variants exist.
INSERT INTO color_lexicon_validation_results
SELECT 'duplicate_canonical_names', 'Duplicate case-normalized canonical names', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Canonical identity is ambiguous.'
FROM (SELECT lower(canonical_name) FROM public.color_canonical GROUP BY lower(canonical_name) HAVING count(*) > 1) d;

-- Duplicate normalized terms: passing result is zero; nonzero means text lookup
-- can resolve to more than one row.
INSERT INTO color_lexicon_validation_results
SELECT 'duplicate_normalized_terms', 'Duplicate normalized lexicon terms', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Exact lexicon lookup is nondeterministic.'
FROM (SELECT normalized_term FROM public.color_lexicon GROUP BY normalized_term HAVING count(*) > 1) d;

-- Empty raw/normalized terms: passing result is zero; nonzero indicates invalid
-- searchable content.
INSERT INTO color_lexicon_validation_results
SELECT 'empty_terms', 'Null or empty term values', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Raw lexicon terms are missing.' FROM public.color_lexicon WHERE term IS NULL OR btrim(term) = '';
INSERT INTO color_lexicon_validation_results
SELECT 'empty_normalized_terms', 'Null or empty normalized_term values', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Normalized lookup keys are missing.' FROM public.color_lexicon WHERE normalized_term IS NULL OR btrim(normalized_term) = '';

-- Normalization consistency: passing result is zero; nonzero means application
-- and stored lookup keys have diverged.
INSERT INTO color_lexicon_validation_results
SELECT 'inconsistent_normalization', 'normalized_term differs from normalization function', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Stored terms cannot be reproduced deterministically.' FROM public.color_lexicon WHERE normalized_term <> public.normalize_color_term(term);

-- Confidence/source checks: invalid values must be zero. Low confidence is a
-- governance warning rather than a constraint failure.
INSERT INTO color_lexicon_validation_results
SELECT 'invalid_confidence_weights', 'Confidence outside [0,1]', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Confidence semantics are invalid.' FROM public.color_lexicon WHERE confidence_weight NOT BETWEEN 0 AND 1;
INSERT INTO color_lexicon_validation_results
SELECT 'low_confidence_terms', 'Mappings below auto-application threshold 0.60', 'Review expected', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARNING' END, 'These mappings require human/context review.' FROM public.color_lexicon WHERE confidence_weight < 0.60;

-- HEX/LAB centroid checks: passing result is zero; nonzero means canonical CV
-- reference values are malformed or out of accepted CIELAB bounds.
INSERT INTO color_lexicon_validation_results
SELECT 'invalid_hex_values', 'Malformed canonical HEX values', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'HEX references cannot be used reliably.' FROM public.color_canonical WHERE hex_reference IS NOT NULL AND hex_reference !~ '^#[0-9A-Fa-f]{6}$';
INSERT INTO color_lexicon_validation_results
SELECT 'invalid_lab_centroids', 'Out-of-range canonical LAB centroids', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Canonical CV centroids violate CIELAB assumptions.' FROM public.color_canonical WHERE (lab_l IS NOT NULL AND lab_l NOT BETWEEN 0 AND 100) OR (lab_a IS NOT NULL AND lab_a NOT BETWEEN -128 AND 127) OR (lab_b IS NOT NULL AND lab_b NOT BETWEEN -128 AND 127);

-- LAB rule bounds/order: passing result is zero; nonzero means candidate rules
-- are unusable or inverted.
INSERT INTO color_lexicon_validation_results
SELECT 'invalid_lab_rule_boundaries', 'LAB rule values outside accepted ranges', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'CV candidate boundaries are invalid.' FROM public.color_lab_mapping_rules WHERE lab_l_min NOT BETWEEN 0 AND 100 OR lab_l_max NOT BETWEEN 0 AND 100 OR lab_a_min NOT BETWEEN -128 AND 127 OR lab_a_max NOT BETWEEN -128 AND 127 OR lab_b_min NOT BETWEEN -128 AND 127 OR lab_b_max NOT BETWEEN -128 AND 127;
INSERT INTO color_lexicon_validation_results
SELECT 'lab_min_greater_than_max', 'LAB minimum greater than maximum', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'One or more rectangular candidate rules are inverted.' FROM public.color_lab_mapping_rules WHERE lab_l_min > lab_l_max OR lab_a_min > lab_a_max OR lab_b_min > lab_b_max;

-- Orphan checks: passing result is zero; nonzero means referential integrity was
-- bypassed or disabled.
INSERT INTO color_lexicon_validation_results
SELECT 'orphaned_lexicon_rows', 'Lexicon rows without canonical color', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Lexicon mappings cannot resolve.' FROM public.color_lexicon l LEFT JOIN public.color_canonical c ON c.color_id = l.color_id WHERE c.color_id IS NULL;
INSERT INTO color_lexicon_validation_results
SELECT 'orphaned_hierarchy_rows', 'Hierarchy endpoints without canonical color', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Hierarchy traversal contains missing nodes.' FROM public.color_hierarchy h LEFT JOIN public.color_canonical p ON p.color_id = h.parent_color_id LEFT JOIN public.color_canonical c ON c.color_id = h.child_color_id WHERE p.color_id IS NULL OR c.color_id IS NULL;
INSERT INTO color_lexicon_validation_results
SELECT 'orphaned_lab_rules', 'LAB rules without canonical color', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'CV rules cannot produce a valid canonical color.' FROM public.color_lab_mapping_rules r LEFT JOIN public.color_canonical c ON c.color_id = r.color_id WHERE c.color_id IS NULL;

-- Hierarchy structural checks: self/duplicate/cycle counts must be zero. The
-- recursive path query detects multi-level cycles; the CHECK only blocks self.
INSERT INTO color_lexicon_validation_results
SELECT 'self_referential_hierarchy', 'Parent equals child', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Hierarchy contains a direct self-cycle.' FROM public.color_hierarchy WHERE parent_color_id = child_color_id;
INSERT INTO color_lexicon_validation_results
SELECT 'duplicate_hierarchy_relationships', 'Duplicate parent-child edges', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Hierarchy contains redundant edges.' FROM (SELECT parent_color_id, child_color_id FROM public.color_hierarchy GROUP BY parent_color_id, child_color_id HAVING count(*) > 1) d;
INSERT INTO color_lexicon_validation_results
WITH RECURSIVE paths AS (
    SELECT parent_color_id AS origin, child_color_id AS node, ARRAY[parent_color_id, child_color_id] AS path, false AS cycle
    FROM public.color_hierarchy
    UNION ALL
    SELECT p.origin, h.child_color_id, p.path || h.child_color_id, h.child_color_id = ANY(p.path)
    FROM paths p JOIN public.color_hierarchy h ON h.parent_color_id = p.node
    WHERE NOT p.cycle AND cardinality(p.path) <= 100
)
SELECT 'multi_level_hierarchy_cycles', 'Recursive hierarchy cycles', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, 'Rollup traversal may loop or double count.' FROM paths WHERE cycle;

-- Rule overlaps: zero is ideal, but representative rectangular boxes may overlap.
-- Nonzero is a warning resolved by nearest canonical centroid, not a false PASS.
INSERT INTO color_lexicon_validation_results
SELECT 'lab_rule_overlaps', 'Pairs of LAB rules with intersecting boxes', '0 ideal; review nonzero', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARNING' END, 'Multiple CV candidates require nearest-centroid resolution.'
FROM public.color_lab_mapping_rules a JOIN public.color_lab_mapping_rules b ON a.rule_id < b.rule_id AND a.lab_l_min <= b.lab_l_max AND b.lab_l_min <= a.lab_l_max AND a.lab_a_min <= b.lab_a_max AND b.lab_a_min <= a.lab_a_max AND a.lab_b_min <= b.lab_b_max AND b.lab_b_min <= a.lab_b_max;

-- Coverage checks: no lexicon/LAB coverage is a warning for an expanded legacy
-- canonical dictionary; no hierarchy participation is informational governance.
INSERT INTO color_lexicon_validation_results
SELECT 'canonical_without_lexicon', 'Canonical colors lacking any text mapping', '0 for auto-normalized colors', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARNING' END, 'These colors cannot be found by lexicon lookup.' FROM public.color_canonical c LEFT JOIN public.color_lexicon l ON l.color_id = c.color_id WHERE l.color_id IS NULL;
INSERT INTO color_lexicon_validation_results
SELECT 'canonical_without_lab_rule', 'Canonical colors lacking a CV rule', '0 for CV-enabled colors', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARNING' END, 'These colors rely on nearest-centroid fallback only.' FROM public.color_canonical c LEFT JOIN public.color_lab_mapping_rules r ON r.color_id = c.color_id WHERE r.color_id IS NULL;
INSERT INTO color_lexicon_validation_results
SELECT 'canonical_without_hierarchy', 'Canonical colors absent from hierarchy', 'Review expanded legacy colors', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARNING' END, 'These colors cannot participate in explicit hierarchy rollups.' FROM public.color_canonical c LEFT JOIN public.color_hierarchy p ON p.parent_color_id = c.color_id LEFT JOIN public.color_hierarchy ch ON ch.child_color_id = c.color_id WHERE p.parent_color_id IS NULL AND ch.child_color_id IS NULL;

-- Source coverage: every governed seed category should have at least 10 rows.
INSERT INTO color_lexicon_validation_results
SELECT 'source_categories_low_coverage', 'Source categories with fewer than 10 mappings', '0', count(*), CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARNING' END, 'Terminology-category coverage may be too narrow.' FROM (SELECT source FROM public.color_lexicon GROUP BY source HAVING count(*) < 10) s;

SELECT query_name, validation_purpose, expected_result, actual_result, status, failure_meaning
FROM color_lexicon_validation_results
ORDER BY CASE status WHEN 'FAIL' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END, query_name;

-- Detail: ambiguous/low-confidence mappings. Passing review means each row has
-- an approved context policy; returned rows must not be auto-applied.
SELECT l.term, l.normalized_term, c.canonical_name, l.confidence_weight, l.source
FROM public.color_lexicon l JOIN public.color_canonical c USING (color_id)
WHERE l.confidence_weight < 0.60 ORDER BY l.confidence_weight, l.normalized_term;

-- Detail: source counts. Passing seed coverage means all expected terminology
-- categories appear with meaningful volume.
SELECT source, count(*) AS mapping_count FROM public.color_lexicon GROUP BY source ORDER BY source;

-- Detail: canonical mapping counts. Low values indicate synonym curation work.
SELECT c.canonical_name, count(l.lexicon_id) AS mapping_count
FROM public.color_canonical c LEFT JOIN public.color_lexicon l USING (color_id)
GROUP BY c.color_id, c.canonical_name ORDER BY mapping_count, c.canonical_name;

-- Detail: LAB overlaps requiring nearest-centroid resolution.
SELECT a.rule_id AS rule_a, ca.canonical_name AS color_a,
       b.rule_id AS rule_b, cb.canonical_name AS color_b
FROM public.color_lab_mapping_rules a
JOIN public.color_lab_mapping_rules b ON a.rule_id < b.rule_id
JOIN public.color_canonical ca ON ca.color_id = a.color_id
JOIN public.color_canonical cb ON cb.color_id = b.color_id
WHERE a.lab_l_min <= b.lab_l_max AND b.lab_l_min <= a.lab_l_max
  AND a.lab_a_min <= b.lab_a_max AND b.lab_a_min <= a.lab_a_max
  AND a.lab_b_min <= b.lab_b_max AND b.lab_b_min <= a.lab_b_max
ORDER BY color_a, color_b;

-- Sample exact NLP lookup. A passing result is one deterministic row for all
-- listed input variations after normalization.
SELECT input_term, public.normalize_color_term(input_term) AS normalized_input,
       c.color_id, c.canonical_name, l.confidence_weight
FROM unnest(ARRAY['Cherry Red', 'cherry-red', 'cherry   red', '#CherryRed', 'CHERRY RED']) AS i(input_term)
LEFT JOIN public.color_lexicon l ON l.normalized_term = public.normalize_color_term(input_term)
LEFT JOIN public.color_canonical c ON c.color_id = l.color_id;

-- Sample fuzzy NLP lookup. Review similarity and enforce a context threshold;
-- a failing operational result is an irrelevant high-ranked candidate.
SELECT l.term, c.canonical_name, similarity(l.normalized_term, public.normalize_color_term('midnite navi')) AS score
FROM public.color_lexicon l JOIN public.color_canonical c USING (color_id)
WHERE l.normalized_term % public.normalize_color_term('midnite navi')
ORDER BY score DESC, l.confidence_weight DESC LIMIT 10;

-- Sample parent-to-child lookup. A passing result lists governed canonical shade
-- children and no repeated/cyclic nodes.
SELECT p.canonical_name AS parent_color, c.canonical_name AS child_color
FROM public.color_hierarchy h JOIN public.color_canonical p ON p.color_id = h.parent_color_id JOIN public.color_canonical c ON c.color_id = h.child_color_id
WHERE p.canonical_name = 'Blue' ORDER BY c.canonical_name;

-- Sample child-to-parent lookup. A passing result resolves Cobalt Blue to Blue.
SELECT c.canonical_name AS child_color, p.canonical_name AS parent_color
FROM public.color_hierarchy h JOIN public.color_canonical p ON p.color_id = h.parent_color_id JOIN public.color_canonical c ON c.color_id = h.child_color_id
WHERE c.canonical_name = 'Cobalt Blue';

-- Sample LAB candidate lookup. Multiple rows are allowed; nearest centroid below
-- provides the deterministic winner.
WITH observation(l, a, b) AS (VALUES (34.0::REAL, 18.0::REAL, -63.0::REAL))
SELECT r.rule_id, c.color_id, c.canonical_name
FROM observation o JOIN public.color_lab_mapping_rules r ON o.l BETWEEN r.lab_l_min AND r.lab_l_max AND o.a BETWEEN r.lab_a_min AND r.lab_a_max AND o.b BETWEEN r.lab_b_min AND r.lab_b_max
JOIN public.color_canonical c ON c.color_id = r.color_id ORDER BY c.canonical_name;

-- Sample nearest canonical lookup using Euclidean CIELAB distance (Delta E 1976
-- approximation). A passing result returns the visually nearest curated centroid.
WITH observation(l, a, b) AS (VALUES (34.0::DOUBLE PRECISION, 18.0::DOUBLE PRECISION, -63.0::DOUBLE PRECISION))
SELECT c.color_id, c.canonical_name,
       sqrt(power(c.lab_l - o.l, 2) + power(c.lab_a - o.a, 2) + power(c.lab_b - o.b, 2)) AS delta_e_76
FROM observation o CROSS JOIN public.color_canonical c
WHERE c.lab_l IS NOT NULL AND c.lab_a IS NOT NULL AND c.lab_b IS NOT NULL
ORDER BY delta_e_76, c.color_id LIMIT 5;

-- Sample analytics count by hue family. Empty family values indicate failed
-- governance and should be corrected.
SELECT color_family, count(*) AS canonical_color_count FROM public.color_canonical GROUP BY color_family ORDER BY color_family;

-- Sample lexicon counts by canonical color and by source for coverage reporting.
SELECT c.canonical_name, count(*) AS mapping_count FROM public.color_lexicon l JOIN public.color_canonical c USING (color_id) GROUP BY c.canonical_name ORDER BY mapping_count DESC, c.canonical_name;
SELECT source, count(*) AS mapping_count FROM public.color_lexicon GROUP BY source ORDER BY mapping_count DESC, source;

COMMIT;
