-- ============================================================================
-- File: 001_create_color_lexicon_schema.sql
-- Purpose: Create the shared canonical color, textual lexicon, hierarchy, and
--          deterministic LAB mapping schema for PostgreSQL 16.
-- Dependencies: Existing public.colors table is supported but not required.
-- Rerun behavior: Safe when the completed migration is rerun. A conflicting
--                 pair of physical colors/color_canonical tables fails loudly.
-- ============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Purpose: Master semantic color dimension shared by CV, NLP, search,
-- editorial, retail, feature-engineering, modeling, insights, and mood boards.
-- Relationships: Referenced through stable color_id values by downstream facts.
-- Expected cardinality: 20-200 rows at capstone scale.
-- Maintenance: Governed additions only; color_id values must never be recycled.
DO $migration$
DECLARE
    colors_kind "char";
    canonical_kind "char";
BEGIN
    SELECT c.relkind INTO colors_kind
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'colors';

    SELECT c.relkind INTO canonical_kind
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'color_canonical';

    IF colors_kind IN ('r', 'p') AND canonical_kind IN ('r', 'p') THEN
        RAISE EXCEPTION
            'Both public.colors and public.color_canonical are physical tables; manual reconciliation is required.';
    ELSIF colors_kind IN ('r', 'p') AND canonical_kind IS NULL THEN
        ALTER TABLE public.colors RENAME TO color_canonical;
    ELSIF colors_kind = 'v' AND canonical_kind IS NULL THEN
        RAISE EXCEPTION
            'public.colors is a view but public.color_canonical is absent; dependency is inconsistent.';
    END IF;
END
$migration$;

CREATE TABLE IF NOT EXISTS public.color_canonical (
    color_id BIGSERIAL,
    canonical_name TEXT NOT NULL,
    color_family TEXT NOT NULL,
    hex_reference TEXT,
    lab_l REAL,
    lab_a REAL,
    lab_b REAL,
    synonyms TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_color_canonical PRIMARY KEY (color_id),
    CONSTRAINT uq_color_canonical_canonical_name UNIQUE (canonical_name)
);

-- Reconcile legacy column names after a non-destructive public.colors rename.
DO $migration$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'color_canonical'
          AND column_name = 'color_name'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'color_canonical'
          AND column_name = 'canonical_name'
    ) THEN
        ALTER TABLE public.color_canonical RENAME COLUMN color_name TO canonical_name;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'color_canonical'
          AND column_name = 'hex'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'color_canonical'
          AND column_name = 'hex_reference'
    ) THEN
        ALTER TABLE public.color_canonical RENAME COLUMN hex TO hex_reference;
    END IF;
END
$migration$;

ALTER TABLE public.color_canonical
    ADD COLUMN IF NOT EXISTS canonical_name TEXT,
    ADD COLUMN IF NOT EXISTS color_family TEXT,
    ADD COLUMN IF NOT EXISTS hex_reference TEXT,
    ADD COLUMN IF NOT EXISTS lab_l REAL,
    ADD COLUMN IF NOT EXISTS lab_a REAL,
    ADD COLUMN IF NOT EXISTS lab_b REAL,
    ADD COLUMN IF NOT EXISTS synonyms TEXT[],
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE public.color_canonical
    ALTER COLUMN canonical_name SET NOT NULL,
    ALTER COLUMN color_family SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL;

DO $migration$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.color_canonical'::regclass
          AND conname = 'colors_pkey'
    ) THEN
        ALTER TABLE public.color_canonical RENAME CONSTRAINT colors_pkey TO pk_color_canonical;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.color_canonical'::regclass
          AND conname = 'colors_color_name_key'
    ) THEN
        ALTER TABLE public.color_canonical
            RENAME CONSTRAINT colors_color_name_key TO uq_color_canonical_canonical_name;
    END IF;
END
$migration$;

DO $migration$
BEGIN
    IF to_regclass('public.colors_color_id_seq') IS NOT NULL
       AND to_regclass('public.color_canonical_color_id_seq') IS NULL THEN
        ALTER SEQUENCE public.colors_color_id_seq RENAME TO color_canonical_color_id_seq;
    END IF;
END
$migration$;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.color_canonical'::regclass
          AND contype = 'p'
    ) THEN
        ALTER TABLE public.color_canonical
            ADD CONSTRAINT pk_color_canonical PRIMARY KEY (color_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.color_canonical'::regclass
          AND conname = 'uq_color_canonical_canonical_name'
    ) THEN
        ALTER TABLE public.color_canonical
            ADD CONSTRAINT uq_color_canonical_canonical_name UNIQUE (canonical_name);
    END IF;
END
$migration$;

DO $migration$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_color_canonical_name_nonempty' AND conrelid = 'public.color_canonical'::regclass) THEN
        ALTER TABLE public.color_canonical ADD CONSTRAINT ck_color_canonical_name_nonempty CHECK (btrim(canonical_name) <> '');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_color_canonical_family_nonempty' AND conrelid = 'public.color_canonical'::regclass) THEN
        ALTER TABLE public.color_canonical ADD CONSTRAINT ck_color_canonical_family_nonempty CHECK (btrim(color_family) <> '');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_color_canonical_hex_format' AND conrelid = 'public.color_canonical'::regclass) THEN
        ALTER TABLE public.color_canonical ADD CONSTRAINT ck_color_canonical_hex_format CHECK (hex_reference IS NULL OR hex_reference ~ '^#[0-9A-Fa-f]{6}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_color_canonical_lab_l' AND conrelid = 'public.color_canonical'::regclass) THEN
        ALTER TABLE public.color_canonical ADD CONSTRAINT ck_color_canonical_lab_l CHECK (lab_l IS NULL OR lab_l BETWEEN 0 AND 100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_color_canonical_lab_a' AND conrelid = 'public.color_canonical'::regclass) THEN
        ALTER TABLE public.color_canonical ADD CONSTRAINT ck_color_canonical_lab_a CHECK (lab_a IS NULL OR lab_a BETWEEN -128 AND 127);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_color_canonical_lab_b' AND conrelid = 'public.color_canonical'::regclass) THEN
        ALTER TABLE public.color_canonical ADD CONSTRAINT ck_color_canonical_lab_b CHECK (lab_b IS NULL OR lab_b BETWEEN -128 AND 127);
    END IF;
END
$migration$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_color_canonical_name_lower
    ON public.color_canonical (lower(canonical_name));
CREATE INDEX IF NOT EXISTS idx_color_canonical_family
    ON public.color_canonical (color_family, color_id);

-- Required normalization function. Keeping normalization in the database makes
-- seed imports and every application client enforce the same exact algorithm.
CREATE OR REPLACE FUNCTION public.normalize_color_term(input_term TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
RETURNS NULL ON NULL INPUT
PARALLEL SAFE
AS $function$
    SELECT btrim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        regexp_replace(
                            lower(translate(
                                regexp_replace(btrim(input_term), '([[:lower:][:digit:]])([[:upper:]])', '\1 \2', 'g'),
                                'ÀÁÂÃÄÅàáâãäåÈÉÊËèéêëÌÍÎÏìíîïÒÓÔÕÖØòóôõöøÙÚÛÜùúûüÇçÑñÝŸýÿÆæŒœ',
                                'AAAAAAaaaaaaEEEEeeeeIIIIiiiiOOOOOOooooooUUUUuuuuCcNnYYyyAaOo'
                            )),
                            '^[#@]+', '', 'g'
                        ),
                        '(''s|’s)\y', '', 'g'
                    ),
                    '[-_/]+', ' ', 'g'
                ),
                '[^a-z0-9 ]+', ' ', 'g'
            ),
            '[[:space:]]+', ' ', 'g'
        )
    );
$function$;

COMMENT ON FUNCTION public.normalize_color_term(TEXT) IS
'Deterministically lowercases, transliterates common Latin accents, splits lower-to-upper camel case, strips leading hashtags/mentions and possessives, converts hyphens/slashes/underscores and punctuation to spaces, and collapses whitespace. Regional spellings remain explicit aliases.';

-- Purpose: Text aliases mapped to one canonical color.
-- Relationships: Many lexicon terms reference one color_canonical row.
-- Downstream consumers: NLP, Google Trends keyword normalization, editorial,
-- retail normalization, signal fusion, and human-review workflows.
-- Expected cardinality: 200-10,000 rows; approximately 500 for this seed.
-- Maintenance: normalized_term must equal normalize_color_term(term).
CREATE TABLE IF NOT EXISTS public.color_lexicon (
    lexicon_id BIGSERIAL,
    term TEXT NOT NULL,
    normalized_term TEXT NOT NULL,
    color_id BIGINT NOT NULL,
    confidence_weight REAL NOT NULL DEFAULT 1.0,
    source TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_color_lexicon PRIMARY KEY (lexicon_id),
    CONSTRAINT uq_color_lexicon_normalized_term UNIQUE (normalized_term),
    CONSTRAINT fk_color_lexicon_color_id FOREIGN KEY (color_id)
        REFERENCES public.color_canonical(color_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT ck_color_lexicon_term_nonempty CHECK (btrim(term) <> ''),
    CONSTRAINT ck_color_lexicon_normalized_nonempty CHECK (btrim(normalized_term) <> ''),
    CONSTRAINT ck_color_lexicon_normalized_consistent CHECK (normalized_term = public.normalize_color_term(term)),
    CONSTRAINT ck_color_lexicon_confidence CHECK (confidence_weight BETWEEN 0 AND 1),
    CONSTRAINT ck_color_lexicon_source_nonempty CHECK (source IS NULL OR btrim(source) <> '')
);

CREATE INDEX IF NOT EXISTS idx_color_lexicon_color
    ON public.color_lexicon (color_id) INCLUDE (normalized_term, confidence_weight, source);
CREATE INDEX IF NOT EXISTS idx_color_lexicon_normalized_trgm
    ON public.color_lexicon USING gin (normalized_term gin_trgm_ops);

-- Purpose: Directed parent-to-child shade hierarchy for family-level rollups.
-- Relationships: Both columns reference color_canonical.
-- Downstream consumers: Analytics, feature rollups, dashboard, mood boards.
-- Expected cardinality: Similar to canonical color count; intended depth <= 2.
-- Maintenance: Self-edges are blocked; multi-row cycles are detected by 006.
CREATE TABLE IF NOT EXISTS public.color_hierarchy (
    parent_color_id BIGINT NOT NULL,
    child_color_id BIGINT NOT NULL,
    CONSTRAINT pk_color_hierarchy PRIMARY KEY (parent_color_id, child_color_id),
    CONSTRAINT fk_color_hierarchy_parent FOREIGN KEY (parent_color_id)
        REFERENCES public.color_canonical(color_id) ON UPDATE RESTRICT ON DELETE CASCADE,
    CONSTRAINT fk_color_hierarchy_child FOREIGN KEY (child_color_id)
        REFERENCES public.color_canonical(color_id) ON UPDATE RESTRICT ON DELETE CASCADE,
    CONSTRAINT ck_color_hierarchy_not_self CHECK (parent_color_id <> child_color_id)
);

CREATE INDEX IF NOT EXISTS idx_color_hierarchy_child
    ON public.color_hierarchy (child_color_id, parent_color_id);

-- Purpose: Rectangular CIELAB candidate boundaries for deterministic CV mapping.
-- Relationships: Multiple calibrated rules may reference one canonical color.
-- Downstream consumers: Garment/image CV and mood-board palette matching.
-- Expected cardinality: 1-5 rules per CV-enabled canonical color.
-- Maintenance: Seed boxes are representative and require image-based calibration.
CREATE TABLE IF NOT EXISTS public.color_lab_mapping_rules (
    rule_id BIGSERIAL,
    color_id BIGINT NOT NULL,
    lab_l_min REAL NOT NULL,
    lab_l_max REAL NOT NULL,
    lab_a_min REAL NOT NULL,
    lab_a_max REAL NOT NULL,
    lab_b_min REAL NOT NULL,
    lab_b_max REAL NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_color_lab_mapping_rules PRIMARY KEY (rule_id),
    CONSTRAINT fk_color_lab_mapping_rules_color_id FOREIGN KEY (color_id)
        REFERENCES public.color_canonical(color_id) ON UPDATE RESTRICT ON DELETE CASCADE,
    CONSTRAINT uq_color_lab_mapping_rules_bounds UNIQUE (
        color_id, lab_l_min, lab_l_max, lab_a_min, lab_a_max, lab_b_min, lab_b_max
    ),
    CONSTRAINT ck_color_lab_rules_l_min CHECK (lab_l_min BETWEEN 0 AND 100),
    CONSTRAINT ck_color_lab_rules_l_max CHECK (lab_l_max BETWEEN 0 AND 100),
    CONSTRAINT ck_color_lab_rules_a_min CHECK (lab_a_min BETWEEN -128 AND 127),
    CONSTRAINT ck_color_lab_rules_a_max CHECK (lab_a_max BETWEEN -128 AND 127),
    CONSTRAINT ck_color_lab_rules_b_min CHECK (lab_b_min BETWEEN -128 AND 127),
    CONSTRAINT ck_color_lab_rules_b_max CHECK (lab_b_max BETWEEN -128 AND 127),
    CONSTRAINT ck_color_lab_rules_l_order CHECK (lab_l_min <= lab_l_max),
    CONSTRAINT ck_color_lab_rules_a_order CHECK (lab_a_min <= lab_a_max),
    CONSTRAINT ck_color_lab_rules_b_order CHECK (lab_b_min <= lab_b_max)
);

CREATE INDEX IF NOT EXISTS idx_color_lab_rules_color
    ON public.color_lab_mapping_rules (color_id);
CREATE INDEX IF NOT EXISTS idx_color_lab_rules_l_candidate
    ON public.color_lab_mapping_rules (lab_l_min, lab_l_max)
    INCLUDE (color_id, lab_a_min, lab_a_max, lab_b_min, lab_b_max);

COMMENT ON TABLE public.color_canonical IS 'Master hue/shade dictionary and stable cross-platform color identifier. color_family is a hue family (red, blue, green, etc.); neutral is used for achromatic and near-neutral colors.';
COMMENT ON COLUMN public.color_canonical.color_id IS 'Stable surrogate identifier referenced across CV, NLP, search, editorial, retail, feature, prediction, insight, and mood-board data.';
COMMENT ON COLUMN public.color_canonical.canonical_name IS 'Governed display name for a distinct canonical hue or shade.';
COMMENT ON COLUMN public.color_canonical.color_family IS 'Hue-family rollup label, not a warm/cool temperature classification.';
COMMENT ON COLUMN public.color_canonical.hex_reference IS 'Representative sRGB HEX value in #RRGGBB format; nullable when not yet curated.';
COMMENT ON COLUMN public.color_canonical.lab_l IS 'Representative CIELAB L* centroid in [0,100].';
COMMENT ON COLUMN public.color_canonical.lab_a IS 'Representative CIELAB a* centroid in approximately [-128,127].';
COMMENT ON COLUMN public.color_canonical.lab_b IS 'Representative CIELAB b* centroid in approximately [-128,127].';
COMMENT ON COLUMN public.color_canonical.synonyms IS 'Deprecated legacy compatibility field; new aliases belong in color_lexicon.';
COMMENT ON TABLE public.color_lexicon IS 'Curated textual aliases mapped to canonical colors for deterministic exact and controlled fuzzy matching.';
COMMENT ON COLUMN public.color_lexicon.term IS 'Human-readable raw alias retained for display and governance.';
COMMENT ON COLUMN public.color_lexicon.normalized_term IS 'Unique deterministic output of normalize_color_term(term), used for exact matching.';
COMMENT ON COLUMN public.color_lexicon.color_id IS 'Stable canonical color selected for this alias.';
COMMENT ON COLUMN public.color_lexicon.confidence_weight IS 'Mapping certainty: 1.00 direct; 0.80-0.99 strong; 0.60-0.79 contextual; below 0.60 requires review and must not be auto-applied.';
COMMENT ON COLUMN public.color_lexicon.source IS 'Terminology category or governed provenance label; seed categories do not claim external source verification.';
COMMENT ON TABLE public.color_hierarchy IS 'Directed canonical shade hierarchy for rollup; seed design uses one edge level and intended maximum traversal depth two.';
COMMENT ON COLUMN public.color_hierarchy.parent_color_id IS 'Broader canonical hue used for rollup.';
COMMENT ON COLUMN public.color_hierarchy.child_color_id IS 'More specific canonical shade.';
COMMENT ON TABLE public.color_lab_mapping_rules IS 'Representative rectangular CIELAB candidate regions; nearest canonical centroid resolves overlaps.';
COMMENT ON COLUMN public.color_lab_mapping_rules.color_id IS 'Canonical candidate produced when an observation lies inside this rule box.';
COMMENT ON COLUMN public.color_lab_mapping_rules.lab_l_min IS 'Inclusive minimum CIELAB L* candidate boundary.';
COMMENT ON COLUMN public.color_lab_mapping_rules.lab_l_max IS 'Inclusive maximum CIELAB L* candidate boundary.';
COMMENT ON COLUMN public.color_lab_mapping_rules.lab_a_min IS 'Inclusive minimum CIELAB a* candidate boundary.';
COMMENT ON COLUMN public.color_lab_mapping_rules.lab_a_max IS 'Inclusive maximum CIELAB a* candidate boundary.';
COMMENT ON COLUMN public.color_lab_mapping_rules.lab_b_min IS 'Inclusive minimum CIELAB b* candidate boundary.';
COMMENT ON COLUMN public.color_lab_mapping_rules.lab_b_max IS 'Inclusive maximum CIELAB b* candidate boundary.';

-- Recreate the legacy read/write-compatible relation name used by current code.
-- Existing foreign keys remain attached to color_canonical by PostgreSQL object ID.
DO $migration$
DECLARE
    colors_kind "char";
BEGIN
    SELECT c.relkind INTO colors_kind
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'colors';

    IF colors_kind IS NULL THEN
        EXECUTE $view$
            CREATE VIEW public.colors AS
            SELECT color_id,
                   canonical_name AS color_name,
                   color_family,
                   hex_reference AS hex,
                   lab_l, lab_a, lab_b,
                   synonyms,
                   created_at
            FROM public.color_canonical
        $view$;
    ELSIF colors_kind <> 'v' THEN
        RAISE EXCEPTION 'Expected public.colors compatibility view, found relkind %', colors_kind;
    END IF;
END
$migration$;

COMMENT ON VIEW public.colors IS 'Legacy compatibility view over color_canonical. New foreign keys and writes should target color_canonical.';

COMMIT;
