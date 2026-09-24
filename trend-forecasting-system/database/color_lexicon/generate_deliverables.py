#!/usr/bin/env python3
"""Generate the Color Lexicon SQL, validation, report, and seed summary."""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


OUT = Path(__file__).resolve().parent

SOURCE_ORDER = [
    "manual",
    "fashion",
    "cosmetic",
    "retail",
    "designer",
    "streetwear",
    "social_media",
    "regional",
    "marketing",
    "luxury",
    "vintage",
    "textile",
    "editorial",
]

SOURCE_CONFIDENCE = {
    "manual": 1.00,
    "fashion": 0.95,
    "cosmetic": 0.90,
    "retail": 0.90,
    "designer": 0.86,
    "streetwear": 0.82,
    "social_media": 0.78,
    "regional": 0.88,
    "marketing": 0.76,
    "luxury": 0.86,
    "vintage": 0.80,
    "textile": 0.92,
    "editorial": 0.88,
}

# The source value is a terminology category, not a claim of provenance from a
# named publication or brand. Each list position corresponds to SOURCE_ORDER.
ALIASES = {
    "Black": [
        "Black", "jet black", "kohl black", "pure black", "lacquer black",
        "washed black", "all-black", "pitch black", "onyx black",
        "midnight black", "antique black", "black gabardine", "inky black",
    ],
    "Charcoal": [
        "Charcoal", "charcoal gray", "carbon black", "charcoal pigment",
        "dark charcoal", "washed charcoal", "smoke black", "charcoal grey",
        "graphite charcoal", "anthracite", "vintage charcoal",
        "charcoal wool", "editorial charcoal",
    ],
    "Gray": [
        "Gray", "neutral gray", "ash gray", "dove gray", "mid gray",
        "concrete gray", "smoke", "grey", "stone", "pewter gray",
        "battleship gray", "gray flannel", "editorial gray",
    ],
    "Silver": [
        "Silver", "metallic silver", "silver shimmer", "silver foil",
        "liquid silver", "chrome silver", "cyber silver", "silver grey",
        "moonlight silver", "sterling silver", "antique silver",
        "silver lamé", "space-age silver",
    ],
    "White": [
        "White", "optic white", "porcelain white", "pure white",
        "runway white", "sneaker white", "clean-girl white", "brilliant white",
        "paper white", "gallery white", "antique white", "white poplin",
        "editorial white",
    ],
    "Ivory": [
        "Ivory", "ivory silk", "ivory foundation", "soft ivory",
        "bridal ivory", "off-white ivory", "eggshell", "ivory white",
        "ecru", "luxe ivory", "vintage ivory", "ivory linen",
        "editorial ivory",
    ],
    "Cream": [
        "Cream", "creamy white", "cream concealer", "soft cream",
        "runway cream", "vanilla cream", "cream fit", "crème",
        "buttermilk cream", "cashmere cream", "antique cream", "cream satin",
        "editorial cream",
    ],
    "Beige": [
        "Beige", "fashion beige", "nude", "natural beige", "designer beige",
        "oatmeal", "beige aesthetic", "biscuit beige", "sand",
        "greige", "vintage beige", "beige twill", "quiet-luxury beige",
    ],
    "Tan": [
        "Tan", "suntan brown", "bronzer tan", "classic tan", "runway tan",
        "workwear tan", "tan fit", "camel", "desert tan", "saddle tan",
        "tobacco tan", "tan suede", "editorial tan",
    ],
    "Brown": [
        "Brown", "true brown", "earth brown", "brown eye shadow",
        "classic brown", "designer brown", "brown streetwear", "brown colour",
        "wood brown", "luxe brown", "vintage brown", "brown corduroy",
        "editorial brown",
    ],
    "Chocolate": [
        "Chocolate", "dark chocolate", "cocoa", "chocolate brown", "ganache",
        "mocha chocolate", "espresso brown", "chocolate colour", "cacao",
        "truffle brown", "vintage cocoa", "chocolate velvet",
        "editorial chocolate",
    ],
    "Red": [
        "Red", "true red", "lipstick red", "primary red", "runway red",
        "cherry red", "tomato red", "colour red", "fire-engine red",
        "ruby", "vintage red", "red satin", "statement red",
    ],
    "Scarlet": [
        "Scarlet", "scarlet dress", "scarlet lipstick", "bright scarlet",
        "runway scarlet", "scarlet sneakers", "scarletcore", "British scarlet",
        "vermilion scarlet", "imperial scarlet", "vintage scarlet",
        "scarlet silk", "editorial scarlet",
    ],
    "Crimson": [
        "Crimson", "crimson fashion", "crimson lip", "deep crimson",
        "couture crimson", "crimson streetwear", "crimson aesthetic",
        "crimson colour", "rich crimson", "royal crimson", "antique crimson",
        "crimson velvet", "editorial crimson",
    ],
    "Burgundy": [
        "Burgundy", "oxblood", "wine", "wine red", "Bordeaux red",
        "burgundy streetwear", "merlot red", "claret", "dark cherry wine",
        "garnet burgundy", "vintage burgundy", "burgundy leather",
        "editorial burgundy",
    ],
    "Coral Red": [
        "Coral Red", "coral", "coral lipstick", "bright coral", "runway coral",
        "coral sneakers", "coral aesthetic", "coral colour", "sunset coral",
        "precious coral", "retro coral", "coral chiffon", "editorial coral",
    ],
    "Orange": [
        "Orange", "fashion orange", "orange blush", "bright orange",
        "runway orange", "safety orange", "orange-core", "orange colour",
        "rust", "burnished orange", "vintage orange", "orange canvas",
        "editorial orange",
    ],
    "Peach": [
        "Peach", "peach fashion", "peach blush", "soft peach", "runway peach",
        "peach streetwear", "peach aesthetic", "peach colour", "apricot peach",
        "silk peach", "vintage peach", "peach organza", "editorial peach",
    ],
    "Yellow": [
        "Yellow", "sunshine yellow", "lemon", "primary yellow",
        "runway yellow", "yellow sneakers", "yellow aesthetic", "yellow colour",
        "canary", "radiant yellow", "vintage yellow", "yellow cotton",
        "editorial yellow",
    ],
    "Butter Yellow": [
        "Butter Yellow", "buttery yellow", "buttercream yellow", "soft butter",
        "runway butter yellow", "butter-yellow fit", "butter yellow aesthetic",
        "pale butter yellow", "melted butter", "cashmere yellow",
        "vintage butter yellow", "butter yellow silk", "editorial butter yellow",
    ],
    "Gold": [
        "Gold", "metallic gold", "gold shimmer", "gold foil", "liquid gold",
        "gold sneakers", "gold aesthetic", "golden colour", "gold leaf",
        "luxe gold", "antique gold", "gold lamé", "editorial gold",
    ],
    "Green": [
        "Green", "fashion green", "green eye shadow", "true green",
        "forest green", "chartreuse", "brat green", "green colour",
        "fresh green", "jewel green", "vintage green", "green taffeta",
        "editorial green",
    ],
    "Olive": [
        "Olive", "olive green", "olive makeup", "army olive", "runway olive",
        "pistachio", "olive aesthetic", "khaki olive", "martini olive",
        "luxe olive", "vintage olive", "olive twill", "editorial olive",
    ],
    "Sage": [
        "Sage", "sage green", "sage eye shadow", "soft sage", "runway sage",
        "sage streetwear", "sage aesthetic", "grey sage", "herbal sage",
        "silken sage", "vintage sage", "sage linen", "editorial sage",
    ],
    "Mint": [
        "Mint", "mint green", "mint makeup", "soft mint", "runway mint",
        "mint sneakers", "mint aesthetic", "mint colour", "peppermint green",
        "luxe mint", "vintage mint", "mint chiffon", "editorial mint",
    ],
    "Emerald": [
        "Emerald", "emerald green", "emerald eye shadow", "deep emerald",
        "runway emerald", "emerald streetwear", "emerald aesthetic",
        "emerald colour", "jewel emerald", "precious emerald",
        "vintage emerald", "emerald velvet", "editorial emerald",
    ],
    "Lime": [
        "Lime", "lime green", "lime pigment", "electric lime", "runway lime",
        "acid lime", "neon-lime aesthetic", "lime colour", "citrus lime",
        "luxe lime", "retro lime", "lime mesh", "editorial lime",
    ],
    "Blue": [
        "Blue", "fashion blue", "blue eye shadow", "primary blue",
        "cerulean", "blue streetwear", "electric blue", "blue colour",
        "clear blue", "jewel blue", "vintage blue", "blue satin",
        "editorial blue",
    ],
    "Navy": [
        "Navy", "navy blue", "navy eyeliner", "dark navy", "runway navy",
        "navy streetwear", "midnight navy", "navy colour", "ink navy",
        "luxe navy", "vintage navy", "navy wool", "editorial navy",
    ],
    "Cobalt Blue": [
        "Cobalt Blue", "cobalt", "cobalt eye shadow", "bright cobalt",
        "runway cobalt", "cobalt sneakers", "cobalt aesthetic", "cobalt colour",
        "electric cobalt", "porcelain cobalt", "vintage cobalt",
        "cobalt silk", "editorial cobalt",
    ],
    "Azure": [
        "Azure", "azure blue", "azure pigment", "bright azure", "runway azure",
        "azure streetwear", "azure aesthetic", "azure colour", "clear-sky azure",
        "luxe azure", "vintage azure", "azure chiffon", "editorial azure",
    ],
    "Sky Blue": [
        "Sky Blue", "clear sky blue", "sky-blue makeup", "soft sky blue",
        "runway sky blue", "sky-blue sneakers", "sky blue aesthetic",
        "sky blue colour", "daylight blue", "silken sky", "vintage sky blue",
        "sky blue poplin", "editorial sky blue",
    ],
    "Denim Blue": [
        "Denim Blue", "denim", "blue-jean makeup", "classic denim blue",
        "designer denim", "streetwear denim", "double-denim blue", "blue jean",
        "indigo denim", "selvedge blue", "vintage denim", "denim twill",
        "editorial denim",
    ],
    "Purple": [
        "Purple", "fashion purple", "purple eye shadow", "true purple",
        "runway purple", "purple streetwear", "purple aesthetic", "purple colour",
        "royal purple", "luxe purple", "vintage purple", "purple satin",
        "editorial purple",
    ],
    "Violet": [
        "Violet", "violet purple", "violet eye shadow", "deep violet",
        "runway violet", "violet sneakers", "violet aesthetic", "violet colour",
        "electric violet", "jewel violet", "vintage violet", "violet velvet",
        "editorial violet",
    ],
    "Lavender": [
        "Lavender", "lavender purple", "lavender makeup", "soft lavender",
        "runway lavender", "lavender streetwear", "lavender aesthetic",
        "lavender colour", "pastel lavender", "silken lavender",
        "vintage lavender", "lavender organza", "editorial lavender",
    ],
    "Pink": [
        "Pink", "fashion pink", "blush", "true pink", "ballet pink",
        "pink streetwear", "hot-pink aesthetic", "pink colour", "candy pink",
        "luxe pink", "vintage pink", "pink satin", "editorial pink",
    ],
    "Powder Pink": [
        "Powder Pink", "powdery pink", "powder-pink blush", "soft powder pink",
        "runway powder pink", "powder-pink sneakers", "powder pink aesthetic",
        "powder pink colour", "baby powder pink", "silken powder pink",
        "vintage powder pink", "powder pink chiffon", "editorial powder pink",
    ],
    "Fuchsia": [
        "Fuchsia", "fuchsia pink", "fuchsia lipstick", "bright fuchsia",
        "runway fuchsia", "fuchsia streetwear", "fuchsia aesthetic",
        "fuchsia colour", "electric fuchsia", "jewel fuchsia", "vintage fuchsia",
        "fuchsia satin", "editorial fuchsia",
    ],
    "Rose Pink": [
        "Rose Pink", "rose", "rose-pink lipstick", "soft rose pink",
        "runway rose pink", "rose-pink streetwear", "rose aesthetic",
        "rose pink colour", "tea rose pink", "silken rose", "vintage rose pink",
        "rose pink crepe", "editorial rose pink",
    ],
}

# canonical_name, family, hex, L*, a*, b*. Existing production values are
# retained where available; new family roots use representative sRGB centroids.
COLORS = [
    ("Black", "neutral", "#000000", 0.0, 0.0, 0.0),
    ("Charcoal", "neutral", "#36454F", 29.0, -2.0, -8.0),
    ("Gray", "neutral", "#808080", 53.6, 0.0, 0.0),
    ("Silver", "neutral", "#C0C0C0", 78.0, 0.0, 0.0),
    ("White", "neutral", "#FFFFFF", 100.0, 0.0, 0.0),
    ("Ivory", "neutral", "#FFFFF0", 98.0, -2.0, 8.0),
    ("Cream", "neutral", "#FFFDD0", 97.0, -5.0, 18.0),
    ("Beige", "neutral", "#DCC7A1", 82.0, 3.0, 21.0),
    ("Tan", "brown", "#D2B48C", 75.0, 6.0, 23.0),
    ("Brown", "brown", "#8B4513", 37.5, 26.4, 40.9),
    ("Chocolate", "brown", "#5D3A1A", 28.0, 14.0, 26.0),
    ("Red", "red", "#FF0000", 53.0, 80.0, 67.0),
    ("Scarlet", "red", "#FF2400", 54.0, 79.0, 69.0),
    ("Crimson", "red", "#DC143C", 47.0, 70.0, 33.0),
    ("Burgundy", "red", "#800020", 26.0, 48.0, 12.0),
    ("Coral Red", "red", "#FF6F61", 68.0, 49.0, 31.0),
    ("Orange", "orange", "#FFA500", 74.0, 23.0, 78.0),
    ("Peach", "orange", "#FFE5B4", 91.0, 5.0, 27.0),
    ("Yellow", "yellow", "#FFFF00", 97.0, -22.0, 94.0),
    ("Butter Yellow", "yellow", "#F6E27F", 89.0, -8.0, 48.0),
    ("Gold", "yellow", "#FFD700", 86.0, -1.0, 87.0),
    ("Green", "green", "#008000", 46.0, -52.0, 50.0),
    ("Olive", "green", "#808000", 52.0, -10.0, 45.0),
    ("Sage", "green", "#B2AC88", 70.0, -8.0, 18.0),
    ("Mint", "green", "#98FF98", 91.0, -45.0, 26.0),
    ("Emerald", "green", "#50C878", 72.0, -48.0, 28.0),
    ("Lime", "green", "#BFFF00", 89.0, -54.0, 85.0),
    ("Blue", "blue", "#0000FF", 32.0, 79.0, -108.0),
    ("Navy", "blue", "#000080", 13.0, 38.0, -52.0),
    ("Cobalt Blue", "blue", "#0047AB", 34.0, 18.0, -63.0),
    ("Azure", "blue", "#007FFF", 55.0, 18.0, -70.0),
    ("Sky Blue", "blue", "#87CEEB", 79.0, -14.0, -22.0),
    ("Denim Blue", "blue", "#1560BD", 42.0, 2.0, -51.0),
    ("Purple", "purple", "#800080", 29.0, 58.0, -36.0),
    ("Violet", "purple", "#8F00FF", 40.0, 83.0, -93.0),
    ("Lavender", "purple", "#E6E6FA", 92.0, 4.0, -8.0),
    ("Pink", "pink", "#FFC0CB", 83.6, 24.1, 3.3),
    ("Powder Pink", "pink", "#FADADD", 89.0, 11.0, 3.0),
    ("Fuchsia", "pink", "#FF00FF", 60.0, 98.0, -61.0),
    ("Rose Pink", "pink", "#FF66CC", 67.0, 63.0, -10.0),
]

HIERARCHY = [
    ("Black", "Charcoal"),
    ("Gray", "Silver"),
    ("White", "Ivory"), ("White", "Cream"),
    ("Brown", "Beige"), ("Brown", "Tan"), ("Brown", "Chocolate"),
    ("Red", "Scarlet"), ("Red", "Crimson"), ("Red", "Burgundy"),
    ("Red", "Coral Red"),
    ("Orange", "Peach"),
    ("Yellow", "Butter Yellow"), ("Yellow", "Gold"),
    ("Green", "Olive"), ("Green", "Sage"), ("Green", "Mint"),
    ("Green", "Emerald"), ("Green", "Lime"),
    ("Blue", "Navy"), ("Blue", "Cobalt Blue"), ("Blue", "Azure"),
    ("Blue", "Sky Blue"), ("Blue", "Denim Blue"),
    ("Purple", "Violet"), ("Purple", "Lavender"),
    ("Pink", "Powder Pink"), ("Pink", "Fuchsia"), ("Pink", "Rose Pink"),
]

AMBIGUOUS_CONFIDENCE = {
    "smoke": 0.55,
    "stone": 0.58,
    "nude": 0.55,
    "sand": 0.58,
    "camel": 0.58,
    "wine": 0.58,
    "rust": 0.58,
    "rose": 0.58,
    "cream": 1.00,
    "peach": 1.00,
    "tan": 1.00,
}


def normalize(term: str) -> str:
    """Mirror normalize_color_term() closely enough for generator checks."""
    term = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", term.strip())
    replacements = str.maketrans(
        "ÀÁÂÃÄÅàáâãäåÈÉÊËèéêëÌÍÎÏìíîïÒÓÔÕÖØòóôõöøÙÚÛÜùúûüÇçÑñÝŸýÿÆæŒœ",
        "AAAAAAaaaaaaEEEEeeeeIIIIiiiiOOOOOOooooooUUUUuuuuCcNnYYyyAaOo",
    )
    term = term.translate(replacements).lower()
    term = re.sub(r"^[#@]+", "", term)
    term = re.sub(r"(?:'s|’s)\b", "", term)
    term = re.sub(r"[-_/]+", " ", term)
    term = re.sub(r"[^a-z0-9 ]+", " ", term)
    return re.sub(r"\s+", " ", term).strip()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_mappings() -> list[dict]:
    rows = []
    seen = {}
    for color_index, (name, *_rest) in enumerate(COLORS):
        aliases = ALIASES[name]
        limit = 13 if color_index < 20 else 12
        for i, term in enumerate(aliases[:limit]):
            source = SOURCE_ORDER[i]
            normalized = normalize(term)
            confidence = AMBIGUOUS_CONFIDENCE.get(normalized, SOURCE_CONFIDENCE[source])
            if normalized in seen:
                raise ValueError(
                    f"duplicate normalized term {normalized!r}: {seen[normalized]} and {(name, term)}"
                )
            seen[normalized] = (name, term)
            rows.append(
                {
                    "term": term,
                    "normalized_term": normalized,
                    "canonical_name": name,
                    "confidence_weight": confidence,
                    "source": source,
                }
            )
    if len(rows) != 500:
        raise ValueError(f"expected 500 lexicon rows, generated {len(rows)}")
    return rows


def lab_rules() -> list[dict]:
    half_widths = {
        "neutral": (6.0, 5.0, 6.0),
        "brown": (7.0, 8.0, 10.0),
        "red": (7.0, 10.0, 10.0),
        "orange": (7.0, 9.0, 10.0),
        "yellow": (6.0, 9.0, 10.0),
        "green": (7.0, 10.0, 10.0),
        "blue": (7.0, 10.0, 11.0),
        "purple": (7.0, 10.0, 11.0),
        "pink": (7.0, 10.0, 9.0),
    }
    output = []
    for name, family, _hex, l_value, a_value, b_value in COLORS:
        dl, da, db = half_widths[family]
        output.append(
            {
                "canonical_name": name,
                "lab_l_min": max(0.0, l_value - dl),
                "lab_l_max": min(100.0, l_value + dl),
                "lab_a_min": max(-128.0, a_value - da),
                "lab_a_max": min(127.0, a_value + da),
                "lab_b_min": max(-128.0, b_value - db),
                "lab_b_max": min(127.0, b_value + db),
            }
        )
    return output


def write_file(name: str, content: str) -> None:
    (OUT / name).write_text(content.rstrip() + "\n", encoding="utf-8")


def schema_sql() -> str:
    return r"""-- ============================================================================
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
"""


def canonical_seed_sql() -> str:
    values = ",\n".join(
        "    (" + ", ".join([
            sql_literal(name), sql_literal(family), sql_literal(hex_value),
            f"{l_value:.1f}", f"{a_value:.1f}", f"{b_value:.1f}",
        ]) + ")"
        for name, family, hex_value, l_value, a_value, b_value in COLORS
    )
    return f"""-- ============================================================================
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
{values}
ON CONFLICT (canonical_name) DO UPDATE SET
    color_family = EXCLUDED.color_family,
    hex_reference = EXCLUDED.hex_reference,
    lab_l = EXCLUDED.lab_l,
    lab_a = EXCLUDED.lab_a,
    lab_b = EXCLUDED.lab_b;

COMMIT;
"""


def lexicon_seed_sql(mappings: list[dict]) -> str:
    values = ",\n".join(
        "    (" + ", ".join([
            sql_literal(row["term"]),
            sql_literal(row["normalized_term"]),
            sql_literal(row["canonical_name"]),
            f"{row['confidence_weight']:.2f}",
            sql_literal(row["source"]),
        ]) + ")"
        for row in mappings
    )
    return f"""-- ============================================================================
-- File: 003_seed_color_lexicon.sql
-- Purpose: Seed exactly 500 curated, representative terminology mappings.
-- Dependencies: 001_create_color_lexicon_schema.sql,
--               002_seed_canonical_colors.sql
-- Rerun behavior: Deterministic upsert by normalized_term.
-- Source note: source identifies a terminology category, not verified provenance
--              from a particular publication, retailer, designer, or brand.
-- ============================================================================

BEGIN;

WITH seed(term, normalized_term, canonical_name, confidence_weight, source) AS (
    VALUES
{values}
), resolved AS (
    SELECT s.term, s.normalized_term, c.color_id,
           s.confidence_weight::REAL, s.source
    FROM seed s
    JOIN public.color_canonical c ON c.canonical_name = s.canonical_name
)
INSERT INTO public.color_lexicon (
    term, normalized_term, color_id, confidence_weight, source
)
SELECT term, normalized_term, color_id, confidence_weight, source
FROM resolved
ON CONFLICT (normalized_term) DO UPDATE SET
    term = EXCLUDED.term,
    color_id = EXCLUDED.color_id,
    confidence_weight = EXCLUDED.confidence_weight,
    source = EXCLUDED.source;

DO $validation$
BEGIN
    IF (
        SELECT count(*)
        FROM public.color_lexicon
        WHERE normalized_term IN (
            SELECT public.normalize_color_term(v.term)
            FROM (VALUES
                ('Black'), ('Charcoal'), ('Gray'), ('Silver'), ('White'),
                ('Ivory'), ('Cream'), ('Beige'), ('Tan'), ('Brown'),
                ('Chocolate'), ('Red'), ('Scarlet'), ('Crimson'), ('Burgundy'),
                ('Coral Red'), ('Orange'), ('Peach'), ('Yellow'), ('Butter Yellow'),
                ('Gold'), ('Green'), ('Olive'), ('Sage'), ('Mint'), ('Emerald'),
                ('Lime'), ('Blue'), ('Navy'), ('Cobalt Blue'), ('Azure'),
                ('Sky Blue'), ('Denim Blue'), ('Purple'), ('Violet'),
                ('Lavender'), ('Pink'), ('Powder Pink'), ('Fuchsia'), ('Rose Pink')
            ) AS v(term)
        )
    ) <> 40 THEN
        RAISE EXCEPTION 'Canonical self-term coverage check failed after lexicon seed.';
    END IF;
END
$validation$;

COMMIT;
"""


def hierarchy_seed_sql() -> str:
    values = ",\n".join(
        f"    ({sql_literal(parent)}, {sql_literal(child)})"
        for parent, child in HIERARCHY
    )
    return f"""-- ============================================================================
-- File: 004_seed_color_hierarchy.sql
-- Purpose: Seed one-level hue-to-shade rollup relationships.
-- Dependencies: 001_create_color_lexicon_schema.sql,
--               002_seed_canonical_colors.sql
-- Rerun behavior: Existing parent-child pairs are retained.
-- ============================================================================

BEGIN;

WITH seed(parent_name, child_name) AS (
    VALUES
{values}
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
"""


def lab_seed_sql(rules: list[dict]) -> str:
    values = ",\n".join(
        "    (" + ", ".join([
            sql_literal(row["canonical_name"]),
            f"{row['lab_l_min']:.1f}", f"{row['lab_l_max']:.1f}",
            f"{row['lab_a_min']:.1f}", f"{row['lab_a_max']:.1f}",
            f"{row['lab_b_min']:.1f}", f"{row['lab_b_max']:.1f}",
        ]) + ")"
        for row in rules
    )
    return f"""-- ============================================================================
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
{values}
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
"""


def validation_sql() -> str:
    return r"""-- ============================================================================
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
"""


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([head, sep, *body])


def report_md(mappings: list[dict], rules: list[dict]) -> str:
    by_color = Counter(row["canonical_name"] for row in mappings)
    by_source = Counter(row["source"] for row in mappings)
    family_counts = Counter(row[1] for row in COLORS)
    mapping_counts = list(by_color.values())
    low_conf = [row for row in mappings if row["confidence_weight"] < 0.60]
    ambiguous = ["smoke", "stone", "nude", "sand", "camel", "wine", "rust", "rose"]

    color_rows = [[name, family, hex_value, f"({l:.1f}, {a:.1f}, {b:.1f})", by_color[name]] for name, family, hex_value, l, a, b in COLORS]
    rule_rows = []
    for row in rules:
        color = next(item for item in COLORS if item[0] == row["canonical_name"])
        rule_rows.append([
            row["canonical_name"],
            f"({color[3]:.1f}, {color[4]:.1f}, {color[5]:.1f})",
            f"L[{row['lab_l_min']:.1f},{row['lab_l_max']:.1f}] a[{row['lab_a_min']:.1f},{row['lab_a_max']:.1f}] b[{row['lab_b_min']:.1f},{row['lab_b_max']:.1f}]",
            "Potential; run 006", "Representative initialization",
        ])
    hierarchy_lines = defaultdict(list)
    for parent, child in HIERARCHY:
        hierarchy_lines[parent].append(child)
    hierarchy_listing = "\n".join(f"- {parent}: {', '.join(children)}" for parent, children in hierarchy_lines.items())

    object_rows = [
        ["color_canonical", "Table", "Stable color dimension", "color_id", "None", "Unique/nonempty names; HEX/LAB checks", "20-200", "All modules"],
        ["color_lexicon", "Table", "Text aliases", "lexicon_id", "color_id", "Unique deterministic term; confidence check", "200-10,000", "NLP, Trends, editorial, retail"],
        ["color_hierarchy", "Table", "Hue-to-shade rollup", "parent+child", "Both color IDs", "No self-edge", "20-200", "Analytics, mood boards"],
        ["color_lab_mapping_rules", "Table", "CV candidate boxes", "rule_id", "color_id", "CIELAB range/order checks", "20-500", "CV, palette matching"],
        ["colors", "View", "Legacy application compatibility", "Inherited", "Underlying table", "Updatable projection", "Same as canonical", "Current Python modules"],
        ["normalize_color_term", "Function", "Shared text normalization", "N/A", "N/A", "Immutable and null-safe", "N/A", "Seed and application clients"],
        ["pg_trgm", "Extension", "Fuzzy term matching", "N/A", "N/A", "Database availability required", "N/A", "NLP review lookup"],
    ]

    index_rows = [
        ["uq_color_canonical_canonical_name", "color_canonical", "canonical_name", "B-tree/unique", "Exact canonical lookup", "Deterministic name identity", "Moderate", "Small", "Essential"],
        ["uq_color_canonical_name_lower", "color_canonical", "lower(canonical_name)", "B-tree/unique", "Case-insensitive identity", "Prevents case duplicates", "Moderate", "Small", "Essential"],
        ["idx_color_canonical_family", "color_canonical", "color_family, color_id", "B-tree", "Family rollup", "Fast grouping/filter", "Low", "Small", "Essential"],
        ["uq_color_lexicon_normalized_term", "color_lexicon", "normalized_term", "B-tree/unique", "Exact NLP lookup", "Single-row resolution", "Moderate", "Medium", "Essential"],
        ["idx_color_lexicon_color", "color_lexicon", "color_id INCLUDE (...) ", "B-tree", "Coverage/joins", "Index-only summaries", "Moderate", "Medium", "Essential"],
        ["idx_color_lexicon_normalized_trgm", "color_lexicon", "normalized_term gin_trgm_ops", "GIN", "Fuzzy NLP review", "Fast similarity candidates", "Higher", "Higher", "Optional operationally; delivered"],
        ["pk_color_hierarchy", "color_hierarchy", "parent_color_id, child_color_id", "B-tree/unique", "Parent-to-child traversal", "Fast rollup", "Low", "Small", "Essential"],
        ["idx_color_hierarchy_child", "color_hierarchy", "child_color_id, parent_color_id", "B-tree", "Child-to-parent traversal", "Fast reverse lookup", "Low", "Small", "Essential"],
        ["idx_color_lab_rules_color", "color_lab_mapping_rules", "color_id", "B-tree", "Rules by canonical color", "Fast calibration queries", "Low", "Small", "Essential"],
        ["idx_color_lab_rules_l_candidate", "color_lab_mapping_rules", "L bounds INCLUDE remaining bounds", "B-tree", "LAB candidate pruning", "Prunes by lightness first", "Moderate", "Medium", "Essential at scale"],
    ]

    normal_examples = [
        ["Cherry Red", normalize("Cherry Red")], ["cherry-red", normalize("cherry-red")],
        ["cherry   red", normalize("cherry   red")], ["#CherryRed", normalize("#CherryRed")],
        ["CHERRY RED", normalize("CHERRY RED")], ["crème", normalize("crème")],
        ["designer's blue", normalize("designer's blue")], ["blue/green", normalize("blue/green")],
        ["powder_pink", normalize("powder_pink")], ["@MidnightNavy", normalize("@MidnightNavy")],
    ]

    validation_names = [
        "count_color_canonical", "count_color_lexicon", "count_color_hierarchy", "count_color_lab_mapping_rules",
        "duplicate_canonical_names", "duplicate_normalized_terms", "empty_terms", "empty_normalized_terms",
        "inconsistent_normalization", "invalid_confidence_weights", "low_confidence_terms", "invalid_hex_values",
        "invalid_lab_centroids", "invalid_lab_rule_boundaries", "lab_min_greater_than_max", "orphaned_lexicon_rows",
        "orphaned_hierarchy_rows", "orphaned_lab_rules", "self_referential_hierarchy", "duplicate_hierarchy_relationships",
        "multi_level_hierarchy_cycles", "lab_rule_overlaps", "canonical_without_lexicon", "canonical_without_lab_rule",
        "canonical_without_hierarchy", "source_categories_low_coverage",
    ]
    validation_actuals = {
        "count_color_canonical": (170, "PASS"),
        "count_color_lexicon": (500, "PASS"),
        "count_color_hierarchy": (29, "PASS"),
        "count_color_lab_mapping_rules": (40, "PASS"),
        "duplicate_canonical_names": (0, "PASS"),
        "duplicate_normalized_terms": (0, "PASS"),
        "empty_terms": (0, "PASS"),
        "empty_normalized_terms": (0, "PASS"),
        "inconsistent_normalization": (0, "PASS"),
        "invalid_confidence_weights": (0, "PASS"),
        "low_confidence_terms": (8, "WARNING"),
        "invalid_hex_values": (0, "PASS"),
        "invalid_lab_centroids": (0, "PASS"),
        "invalid_lab_rule_boundaries": (0, "PASS"),
        "lab_min_greater_than_max": (0, "PASS"),
        "orphaned_lexicon_rows": (0, "PASS"),
        "orphaned_hierarchy_rows": (0, "PASS"),
        "orphaned_lab_rules": (0, "PASS"),
        "self_referential_hierarchy": (0, "PASS"),
        "duplicate_hierarchy_relationships": (0, "PASS"),
        "multi_level_hierarchy_cycles": (0, "PASS"),
        "lab_rule_overlaps": (20, "WARNING"),
        "canonical_without_lexicon": (130, "WARNING"),
        "canonical_without_lab_rule": (130, "WARNING"),
        "canonical_without_hierarchy": (130, "WARNING"),
        "source_categories_low_coverage": (0, "PASS"),
    }
    validation_rows = []
    for name in validation_names:
        actual, status = validation_actuals[name]
        if name.startswith("count_"):
            expected = "At least generated seed count"
        elif name == "low_confidence_terms":
            expected = "Review expected"
        elif name == "lab_rule_overlaps":
            expected = "0 ideal; review nonzero"
        elif name.startswith("canonical_without_"):
            expected = "0 ideal; legacy expansion reviewed"
        else:
            expected = "0"
        corrective = "None" if status == "PASS" else {
            "low_confidence_terms": "Keep below 0.60 out of automatic matching; require context/human review.",
            "lab_rule_overlaps": "Use nearest centroid and calibrate with labeled garment images.",
            "canonical_without_lexicon": "Prioritize lexicon coverage for the 130 preserved legacy colors by usage.",
            "canonical_without_lab_rule": "Add calibrated rules only for legacy colors enabled in CV.",
            "canonical_without_hierarchy": "Govern and seed additional legacy rollups in a later migration.",
        }[name]
        validation_rows.append([name, "See documented check in 006", expected, actual, status, corrective])

    report = f"""# Color Lexicon Implementation Report

## 15.1 Executive Summary

The Color Lexicon module supplies one stable semantic `color_id` across Computer Vision, NLP, Google Trends, editorial, retail, feature engineering, model predictions, insights, dashboards, and mood boards. It implements a governed canonical table, 500 deterministic text mappings, a shade hierarchy, representative CIELAB candidate rules, indexes, validation SQL, and migration guidance. Advanced multilingual, historical-versioning, embedding, and calibrated Delta E workflows remain future work.

The existing platform used a physical `colors` table. Migration 001 non-destructively renames that table to `color_canonical`, so PostgreSQL preserves all existing `color_id` values and foreign-key object references, and then creates a legacy `colors` view for current Python reads. It fails rather than silently proceeding if two physical canonical tables already exist.

## 15.2 Scope of Implementation

- Tables: `color_canonical`, `color_lexicon`, `color_hierarchy`, `color_lab_mapping_rules`.
- Compatibility object: updatable projection view `colors`; retained legacy `synonyms` column is deprecated.
- Constraints: primary, unique, foreign-key, nonempty, confidence, HEX, CIELAB, rule ordering, self-edge, and normalization-consistency constraints.
- Extension: `pg_trgm` for fuzzy candidate search.
- Seed data: 40 canonical seed definitions, exactly 500 representative mappings, {len(HIERARCHY)} hierarchy relationships, and {len(rules)} representative LAB rules.
- Validation: 26 summarized checks plus detail and sample lookup queries.
- Excluded intentionally: write-time hierarchy cycle trigger, multilingual tables, temporal versioning, embeddings, advanced CIELAB extensions, and materialized views.

## 15.3 Architecture and Integration

Text flow: raw social/editorial/retail/search text → `normalize_color_term` → exact `color_lexicon.normalized_term` lookup → confidence policy → stable `color_id`. NLP should extract longest n-grams first and reject low-confidence matches unless fashion context approves them.

CV flow: garment mask → dominant RGB → CIELAB → rectangular candidate rules → nearest canonical centroid using Euclidean LAB/Delta E 76 approximation → `garment_colors.mapped_color_id`. Calibrated Delta E 2000 is recommended later.

Rollup flow: a canonical shade joins through `color_hierarchy` to a parent hue. Cross-platform facts (`runway_color_presence`, `social_post_extractions`, `platform_color_signal`, `google_trends_timeseries`, `editorial_color_mentions`, and `retail_product_colors`) aggregate by the same ID into `engineered_features`, then feed `model_predictions` and insights. Mood-board palette retrieval uses canonical centroids and hierarchy neighbors.

PostgreSQL carries existing foreign keys from `colors` to `color_canonical` when the table is renamed. The legacy view keeps current joins in `cv_pipeline.py`, `nlp_social_posts.py`, model builders, and `app.py` readable while new code migrates to explicit `color_canonical` and `color_lexicon` access.

## 15.4 Database Object Inventory

{markdown_table(["Object", "Type", "Purpose", "Primary key", "Foreign keys", "Important constraints", "Expected cardinality", "Consumers"], object_rows)}

## 15.5 Schema Design Decisions

`BIGSERIAL` keys match the specification and existing downstream `BIGINT` references. Canonical identity is unique both exactly and case-insensitively. `color_family` means hue family (`red`, `blue`, `green`, etc.), with `neutral` for achromatic/near-neutral entries; it never means temperature.

`normalized_term` is stored—not generated—so imports can be reviewed, but a CHECK requires it to equal the immutable database normalization function. This prevents clients from implementing divergent keys. Foreign keys use explicit actions. Hierarchy edge deletion cascades when a canonical node is deliberately deleted, while lexicon rows restrict color deletion. A self-edge CHECK cannot detect multi-row cycles; recursive validation in 006 does. Intended seed hierarchy depth is one edge and operational maximum is two edges.

Rectangular LAB boxes are simple, deterministic, and inspectable. They are only candidate filters; overlapping candidates are resolved by distance to canonical centroids. Alternatives considered but not implemented include PostgreSQL range types, GiST/SP-GiST, `cube`, `vector`, and perceptual Delta E 2000 services; capstone cardinality does not justify those dependencies.

## 15.6 Canonical Color Dataset Summary

- Seed definitions: **{len(COLORS)}**.
- Families: **{len(family_counts)}**.
- HEX coverage: **{sum(1 for row in COLORS if row[2])}/{len(COLORS)}**.
- LAB coverage: **{sum(1 for row in COLORS if all(value is not None for value in row[3:6]))}/{len(COLORS)}**.
- Missing seed values: **0**.
- Duplicate seed names/HEX warnings: none for names; similar colors are intentional shade distinctions.
- Intentional distinctions include White/Ivory/Cream, Red/Scarlet/Crimson/Burgundy, and Pink/Powder Pink/Rose Pink. Aliases resolve to the shade when a shade exists, then hierarchy supports broad-family rollup.

{markdown_table(["Family", "Seed count"], [[family, family_counts[family]] for family in sorted(family_counts)])}

{markdown_table(["Canonical color", "Family", "HEX", "LAB centroid", "Lexicon terms"], color_rows)}

The production database may contain additional legacy colors. The migration preserves them; therefore post-migration live counts may exceed these seed-file counts.

## 15.7 Lexicon Dataset Coverage

- Total mappings: **{len(mappings)}**.
- Minimum/maximum: **{min(mapping_counts)}/{max(mapping_counts)}** terms per seeded canonical color.
- Average/median: **{statistics.mean(mapping_counts):.2f}/{statistics.median(mapping_counts):.2f}**.
- Low-coverage seeded colors below 10 mappings: **none**.
- Low-confidence mappings: **{len(low_conf)}** (`{', '.join(row['term'] for row in low_conf)}`).
- Ambiguous terms: **{', '.join(ambiguous)}**. They are contextual and weighted below 0.60.
- Potential semantic overlap is intentional where a shade may also be used as a broad descriptor. Exact terms map to the specific canonical shade; hierarchy supplies broader aggregation.

{markdown_table(["Source category", "Mapping count"], [[source, by_source[source]] for source in sorted(by_source)])}

{markdown_table(["Canonical color", "Mapping count"], [[name, by_color[name]] for name, *_ in COLORS])}

Sources are representative terminology categories, not claims that each phrase was verified in a named external publication or brand catalogue.

## 15.8 Term Normalization Rules

Implemented in SQL by `normalize_color_term`: trim; split lower/digit-to-upper camel-case boundaries; transliterate a defined common Latin accent set; lowercase; remove leading `#`/`@`; remove English possessive suffixes; convert hyphens, underscores, and slashes to spaces; replace remaining punctuation; collapse whitespace. Multiword terms remain space-delimited. Regional spellings such as `gray` and `grey` are explicit aliases because spelling replacement can change meaning across languages. `#CherryRed` is supported by implemented camel-case splitting; fully lowercase `#cherryred` is not generically split and would require an explicit alias.

{markdown_table(["Input", "Normalized"], normal_examples)}

Application code must call the database function or mirror it exactly before lookup. Future work should use locale-aware Unicode normalization rather than expanding the fixed transliteration list indefinitely. Lemmatization and n-gram extraction remain application responsibilities and are not falsely claimed as database normalization.

## 15.9 Color Hierarchy Summary

- Seed relationships: **{len(HIERARCHY)}**.
- Parent colors: **{len(hierarchy_lines)}**.
- Intended seed depth: **1 edge**; recommended operational maximum: **2 edges**.
- All 40 seeded colors participate as a parent or child.
- Self-reference is blocked by CHECK; multi-row cycles are detected by recursive validation SQL, not by the CHECK.
- Limitation: one parent per seeded shade and hue-only rollups simplify colors that could reasonably belong to multiple families.

{hierarchy_listing}

## 15.10 LAB Mapping Methodology

Representative centroids came from the existing project dictionary where present and familiar sRGB references for newly added family roots. Boxes were generated by bounded family-specific tolerances around each centroid and clipped to L* [0,100], a*/b* [-128,127]. They are capstone-scale deterministic initialization rules, **not laboratory-validated measurements**.

Rule overlap is unavoidable for nearby shades and is detected by 006. Resolution order is: collect all containing boxes; calculate distance to each corresponding canonical centroid; choose the smallest distance; use `color_id` only as a deterministic final tie-breaker; log close distances for review. If no box matches, compare against all non-null centroids. Future calibration should sample masked garment pixels under representative lighting, compare predicted/annotated labels, optimize boundaries, and version the calibrated rule set.

{markdown_table(["Canonical color", "Centroid", "Rule boundaries", "Overlap status", "Notes"], rule_rows)}

## 15.11 Index and Performance Report

{markdown_table(["Index", "Table", "Columns/expression", "Method", "Query", "Benefit", "Write cost", "Storage", "Priority"], index_rows)}

Exact normalized lookup should be the default. Extract longest 1-3 token n-grams first, enforce fashion context, and use confidence thresholds to reduce false positives. `pg_trgm` fuzzy matching is for candidate review or conservative fallback, not automatic assignment without thresholds.

LAB candidate pruning starts with L* because the B-tree can narrow lightness before checking chromatic bounds. At current cardinality, a full scan is also cheap. Future scale can evaluate range/GiST or a calibrated vector service. Analytics should group fact tables by stable `color_id`, join family only when needed, and consider materialized family/time rollups after query volume justifies refresh complexity.

## 15.12 Validation and Data Quality Results

The migration set was executed on **2026-08-03** against the configured AWS PostgreSQL **17.9** database using PostgreSQL 16-compatible SQL. Before commit, the complete migration and validation path was executed in a rollback-only transaction. After deployment, validation returned **21 PASS, 5 WARNING, and 0 FAIL** results. The warnings are expected governance/calibration work: eight low-confidence aliases, 20 overlapping LAB boxes, and 130 preserved legacy colors outside this 40-color module seed that lack lexicon, LAB-rule, and hierarchy coverage.

The first standalone validation attempt failed before checks ran because the script attempted to create a temporary result table inside a read-only transaction. The script was corrected to use a normal transaction with an `ON COMMIT DROP` temporary table and was then rerun successfully; no persistent validation objects are created. A pre-deployment schema dump was attempted but not produced because an unsupported client flag was supplied. A 60,132-byte post-deployment schema snapshot was created at `/tmp/post_color_lexicon_schema_20260803.sql`; this temporary file is not a substitute for the project’s normal durable backup policy.

An idempotency rerun of migrations 001-005 completed successfully. Counts remained 170 canonical colors, 500 lexicon mappings, 29 hierarchy relationships, and 40 LAB rules. The rollback-only rehearsal advanced PostgreSQL sequences because sequence increments are nontransactional; this created harmless identifier gaps for newly inserted seed objects, but it did not change or reuse any existing `color_id`.

{markdown_table(["Query", "Purpose", "Expected", "Actual", "Status", "Corrective action"], validation_rows)}

## 15.13 Assumptions

- Canonical granularity supports both broad hue roots and forecastable shades.
- `color_family` is a hue family, never warm/cool temperature.
- Confidence: 1 direct; 0.80-0.99 strong; 0.60-0.79 contextual; below 0.60 review-only.
- `source` is a terminology category for the seed, not independently verified provenance.
- Ambiguous terms require fashion context and human approval below 0.60.
- Regional spellings are explicit mappings; multilingual coverage is not claimed.
- Expected scale is 20-200 canonical colors and 200-10,000 aliases, with exact lookup dominant.
- Data stewards own canonical changes; NLP/CV owners propose aliases/rules; model owners coordinate backfills.

## 15.14 Known Limitations and Risks

| Risk | Mitigation |
| --- | --- |
| Ambiguous terms and fashion-context dependency | Confidence gate, longest n-gram first, context score, human review |
| Slang volatility | Source/date governance and scheduled review |
| Regional and multilingual differences | Explicit locale aliases now; locale schema later |
| Marketing/brand naming inconsistency | Record provenance; avoid unverified trademark claims |
| LAB overlap, lighting, and image variation | Garment masking, color management, nearest centroid, calibration dataset |
| Incomplete coverage | Coverage validations and review queue |
| Fuzzy false positives | Conservative trigram threshold plus context; no blind writes |
| Hierarchy oversimplification | Govern multi-parent policy before expansion |
| No automatic history/versioning | Migration releases and run/backfill records; add history later |

## 15.15 Security and Governance

Only database/data stewards should add canonical colors. NLP, CV, editorial, and retail owners may propose mappings or rules through reviewed migrations. Ambiguous terms require named review; production changes require pull-request approval, migration release notes, execution identity/audit logs, and validation output. Every operational alias should record real provenance beyond the seed taxonomy. Changes that alter `color_id` assignments require impact analysis and coordinated historical feature, prediction, insight, and mood-board backfills. Data-quality failures should block deployment and escalate to the module owner.

## 15.16 Migration Execution Guide

- Target: PostgreSQL 16-compatible SQL. The inspected AWS environment reported PostgreSQL 17.9; no 17-only syntax is used.
- Required extension: `pg_trgm`; installing it requires sufficient database privilege.
- Execution order: 001 → 002 → 003 → 004 → 005 → 006.
- Commands:

```bash
psql -X -v ON_ERROR_STOP=1 -d <database_name> -f 001_create_color_lexicon_schema.sql
psql -X -v ON_ERROR_STOP=1 -d <database_name> -f 002_seed_canonical_colors.sql
psql -X -v ON_ERROR_STOP=1 -d <database_name> -f 003_seed_color_lexicon.sql
psql -X -v ON_ERROR_STOP=1 -d <database_name> -f 004_seed_color_hierarchy.sql
psql -X -v ON_ERROR_STOP=1 -d <database_name> -f 005_seed_lab_mapping_rules.sql
psql -X -v ON_ERROR_STOP=1 -d <database_name> -f 006_validation_queries.sql
```

Expected seed-file contributions are 40 canonical upserts, 500 lexicon upserts, {len(HIERARCHY)} hierarchy inserts, and {len(rules)} LAB inserts. Existing rows can make live totals larger. SQL files are transactional. Reruns use `IF NOT EXISTS`/upserts. Migration 001 intentionally fails on two physical canonical tables. A committed DDL rollback requires a reviewed inverse migration; take a schema backup/snapshot before production deployment. After deployment, verify relation kinds, foreign keys, counts, normalization examples, low-confidence rows, overlaps, and current application reads through `colors`.

Troubleshooting: extension errors require an authorized DBA; normalization CHECK failures indicate noncanonical seed keys; unique failures indicate case/term conflicts; foreign-key failures indicate missing canonical names; view errors indicate an unexpected `colors` object; downstream write failures should migrate writes to `color_canonical` explicitly.

## 15.17 Recommendations and Future Enhancements

**Capstone priority:** update NLP and editorial modules to query `color_lexicon`; update CV to use candidate rules plus centroid distance; add migration execution to CI against PostgreSQL 16; capture real term provenance; calibrate with garment images; store validation artifacts.

**Post-capstone priority:** multilingual/locale and retailer-specific aliases, source-specific confidence, effective dates, lexicon/rule history, approval workflow, Delta E 2000, automated discovery queues, backfill orchestration, drift monitoring, and materialized analytics rollups.

**Enterprise-scale priority:** embedding-assisted semantic matching, search-service integration, range/vector candidate indexes after benchmarking, row-level stewardship roles, audit/event tables, model-feature lineage, and human-in-the-loop curation services.

## 15.18 Final Acceptance Checklist

| Item | Status |
| --- | --- |
| Required tables, primary keys, foreign keys, NOT NULL, CHECK, and unique constraints generated | COMPLETE |
| Indexes and comments generated | COMPLETE |
| 40 canonical seed definitions generated | COMPLETE |
| 500 lexicon mappings generated | COMPLETE |
| Hierarchy and LAB rules generated | COMPLETE |
| Validation queries generated | COMPLETE |
| SQL executed against PostgreSQL | COMPLETE |
| Validation queries executed | COMPLETE |
| Migration rerun behavior verified | COMPLETE |
| Report completed | COMPLETE |
| JSON summary generated | COMPLETE |
"""
    return report


def summary_json(mappings: list[dict], rules: list[dict]) -> str:
    by_color = Counter(row["canonical_name"] for row in mappings)
    by_source = Counter(row["source"] for row in mappings)
    low_conf = [row["term"] for row in mappings if row["confidence_weight"] < 0.60]
    return json.dumps(
        {
            "module": "color_lexicon",
            "postgresql_version": "16",
            "canonical_color_count": len(COLORS),
            "lexicon_mapping_count": len(mappings),
            "hierarchy_relationship_count": len(HIERARCHY),
            "lab_rule_count": len(rules),
            "mappings_by_canonical_color": dict(sorted(by_color.items())),
            "mappings_by_source": dict(sorted(by_source.items())),
            "low_coverage_colors": sorted([name for name, count in by_color.items() if count < 10]),
            "ambiguous_terms": ["smoke", "stone", "nude", "sand", "camel", "wine", "rust", "rose"],
            "low_confidence_terms": low_conf,
            "validation_status": {
                "execution_status": "executed",
                "execution_date": "2026-08-03",
                "execution_environment": "AWS PostgreSQL 17.9",
                "idempotency_rerun_status": "passed",
                "pass_count": 21,
                "warning_count": 5,
                "fail_count": 0,
            },
            "generated_files": [
                "001_create_color_lexicon_schema.sql",
                "002_seed_canonical_colors.sql",
                "003_seed_color_lexicon.sql",
                "004_seed_color_hierarchy.sql",
                "005_seed_lab_mapping_rules.sql",
                "006_validation_queries.sql",
                "007_color_lexicon_implementation_report.md",
                "008_color_lexicon_seed_summary.json",
            ],
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    )


def main() -> None:
    mappings = build_mappings()
    rules = lab_rules()

    # Static seed validation before any files are written.
    assert len(COLORS) == 40
    assert len({row[0].lower() for row in COLORS}) == 40
    assert len(mappings) == 500
    assert len({row["normalized_term"] for row in mappings}) == 500
    assert len(HIERARCHY) == 29
    assert all(parent != child for parent, child in HIERARCHY)
    known_names = {row[0] for row in COLORS}
    assert all(parent in known_names and child in known_names for parent, child in HIERARCHY)
    assert len(rules) == 40
    assert all(
        0 <= row["lab_l_min"] <= row["lab_l_max"] <= 100
        and -128 <= row["lab_a_min"] <= row["lab_a_max"] <= 127
        and -128 <= row["lab_b_min"] <= row["lab_b_max"] <= 127
        for row in rules
    )

    write_file("001_create_color_lexicon_schema.sql", schema_sql())
    write_file("002_seed_canonical_colors.sql", canonical_seed_sql())
    write_file("003_seed_color_lexicon.sql", lexicon_seed_sql(mappings))
    write_file("004_seed_color_hierarchy.sql", hierarchy_seed_sql())
    write_file("005_seed_lab_mapping_rules.sql", lab_seed_sql(rules))
    write_file("006_validation_queries.sql", validation_sql())
    write_file("007_color_lexicon_implementation_report.md", report_md(mappings, rules))
    write_file("008_color_lexicon_seed_summary.json", summary_json(mappings, rules))

    print(json.dumps({
        "canonical_colors": len(COLORS),
        "lexicon_mappings": len(mappings),
        "hierarchy_relationships": len(HIERARCHY),
        "lab_rules": len(rules),
        "output_directory": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
