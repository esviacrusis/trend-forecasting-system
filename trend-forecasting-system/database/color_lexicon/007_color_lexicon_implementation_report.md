# Color Lexicon Implementation Report

## 15.1 Executive Summary

The Color Lexicon module supplies one stable semantic `color_id` across Computer Vision, NLP, Google Trends, editorial, retail, feature engineering, model predictions, insights, dashboards, and mood boards. It implements a governed canonical table, 500 deterministic text mappings, a shade hierarchy, representative CIELAB candidate rules, indexes, validation SQL, and migration guidance. Advanced multilingual, historical-versioning, embedding, and calibrated Delta E workflows remain future work.

The existing platform used a physical `colors` table. Migration 001 non-destructively renames that table to `color_canonical`, so PostgreSQL preserves all existing `color_id` values and foreign-key object references, and then creates a legacy `colors` view for current Python reads. It fails rather than silently proceeding if two physical canonical tables already exist.

## 15.2 Scope of Implementation

- Tables: `color_canonical`, `color_lexicon`, `color_hierarchy`, `color_lab_mapping_rules`.
- Compatibility object: updatable projection view `colors`; retained legacy `synonyms` column is deprecated.
- Constraints: primary, unique, foreign-key, nonempty, confidence, HEX, CIELAB, rule ordering, self-edge, and normalization-consistency constraints.
- Extension: `pg_trgm` for fuzzy candidate search.
- Seed data: 40 canonical seed definitions, exactly 500 representative mappings, 29 hierarchy relationships, and 40 representative LAB rules.
- Validation: 26 summarized checks plus detail and sample lookup queries.
- Excluded intentionally: write-time hierarchy cycle trigger, multilingual tables, temporal versioning, embeddings, advanced CIELAB extensions, and materialized views.

## 15.3 Architecture and Integration

Text flow: raw social/editorial/retail/search text → `normalize_color_term` → exact `color_lexicon.normalized_term` lookup → confidence policy → stable `color_id`. NLP should extract longest n-grams first and reject low-confidence matches unless fashion context approves them.

CV flow: garment mask → dominant RGB → CIELAB → rectangular candidate rules → nearest canonical centroid using Euclidean LAB/Delta E 76 approximation → `garment_colors.mapped_color_id`. Calibrated Delta E 2000 is recommended later.

Rollup flow: a canonical shade joins through `color_hierarchy` to a parent hue. Cross-platform facts (`runway_color_presence`, `social_post_extractions`, `platform_color_signal`, `google_trends_timeseries`, `editorial_color_mentions`, and `retail_product_colors`) aggregate by the same ID into `engineered_features`, then feed `model_predictions` and insights. Mood-board palette retrieval uses canonical centroids and hierarchy neighbors.

PostgreSQL carries existing foreign keys from `colors` to `color_canonical` when the table is renamed. The legacy view keeps current joins in `cv_pipeline.py`, `nlp_social_posts.py`, model builders, and `app.py` readable while new code migrates to explicit `color_canonical` and `color_lexicon` access.

## 15.4 Database Object Inventory

| Object | Type | Purpose | Primary key | Foreign keys | Important constraints | Expected cardinality | Consumers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| color_canonical | Table | Stable color dimension | color_id | None | Unique/nonempty names; HEX/LAB checks | 20-200 | All modules |
| color_lexicon | Table | Text aliases | lexicon_id | color_id | Unique deterministic term; confidence check | 200-10,000 | NLP, Trends, editorial, retail |
| color_hierarchy | Table | Hue-to-shade rollup | parent+child | Both color IDs | No self-edge | 20-200 | Analytics, mood boards |
| color_lab_mapping_rules | Table | CV candidate boxes | rule_id | color_id | CIELAB range/order checks | 20-500 | CV, palette matching |
| colors | View | Legacy application compatibility | Inherited | Underlying table | Updatable projection | Same as canonical | Current Python modules |
| normalize_color_term | Function | Shared text normalization | N/A | N/A | Immutable and null-safe | N/A | Seed and application clients |
| pg_trgm | Extension | Fuzzy term matching | N/A | N/A | Database availability required | N/A | NLP review lookup |

## 15.5 Schema Design Decisions

`BIGSERIAL` keys match the specification and existing downstream `BIGINT` references. Canonical identity is unique both exactly and case-insensitively. `color_family` means hue family (`red`, `blue`, `green`, etc.), with `neutral` for achromatic/near-neutral entries; it never means temperature.

`normalized_term` is stored—not generated—so imports can be reviewed, but a CHECK requires it to equal the immutable database normalization function. This prevents clients from implementing divergent keys. Foreign keys use explicit actions. Hierarchy edge deletion cascades when a canonical node is deliberately deleted, while lexicon rows restrict color deletion. A self-edge CHECK cannot detect multi-row cycles; recursive validation in 006 does. Intended seed hierarchy depth is one edge and operational maximum is two edges.

Rectangular LAB boxes are simple, deterministic, and inspectable. They are only candidate filters; overlapping candidates are resolved by distance to canonical centroids. Alternatives considered but not implemented include PostgreSQL range types, GiST/SP-GiST, `cube`, `vector`, and perceptual Delta E 2000 services; capstone cardinality does not justify those dependencies.

## 15.6 Canonical Color Dataset Summary

- Seed definitions: **40**.
- Families: **9**.
- HEX coverage: **40/40**.
- LAB coverage: **40/40**.
- Missing seed values: **0**.
- Duplicate seed names/HEX warnings: none for names; similar colors are intentional shade distinctions.
- Intentional distinctions include White/Ivory/Cream, Red/Scarlet/Crimson/Burgundy, and Pink/Powder Pink/Rose Pink. Aliases resolve to the shade when a shade exists, then hierarchy supports broad-family rollup.

| Family | Seed count |
| --- | --- |
| blue | 6 |
| brown | 3 |
| green | 6 |
| neutral | 8 |
| orange | 2 |
| pink | 4 |
| purple | 3 |
| red | 5 |
| yellow | 3 |

| Canonical color | Family | HEX | LAB centroid | Lexicon terms |
| --- | --- | --- | --- | --- |
| Black | neutral | #000000 | (0.0, 0.0, 0.0) | 13 |
| Charcoal | neutral | #36454F | (29.0, -2.0, -8.0) | 13 |
| Gray | neutral | #808080 | (53.6, 0.0, 0.0) | 13 |
| Silver | neutral | #C0C0C0 | (78.0, 0.0, 0.0) | 13 |
| White | neutral | #FFFFFF | (100.0, 0.0, 0.0) | 13 |
| Ivory | neutral | #FFFFF0 | (98.0, -2.0, 8.0) | 13 |
| Cream | neutral | #FFFDD0 | (97.0, -5.0, 18.0) | 13 |
| Beige | neutral | #DCC7A1 | (82.0, 3.0, 21.0) | 13 |
| Tan | brown | #D2B48C | (75.0, 6.0, 23.0) | 13 |
| Brown | brown | #8B4513 | (37.5, 26.4, 40.9) | 13 |
| Chocolate | brown | #5D3A1A | (28.0, 14.0, 26.0) | 13 |
| Red | red | #FF0000 | (53.0, 80.0, 67.0) | 13 |
| Scarlet | red | #FF2400 | (54.0, 79.0, 69.0) | 13 |
| Crimson | red | #DC143C | (47.0, 70.0, 33.0) | 13 |
| Burgundy | red | #800020 | (26.0, 48.0, 12.0) | 13 |
| Coral Red | red | #FF6F61 | (68.0, 49.0, 31.0) | 13 |
| Orange | orange | #FFA500 | (74.0, 23.0, 78.0) | 13 |
| Peach | orange | #FFE5B4 | (91.0, 5.0, 27.0) | 13 |
| Yellow | yellow | #FFFF00 | (97.0, -22.0, 94.0) | 13 |
| Butter Yellow | yellow | #F6E27F | (89.0, -8.0, 48.0) | 13 |
| Gold | yellow | #FFD700 | (86.0, -1.0, 87.0) | 12 |
| Green | green | #008000 | (46.0, -52.0, 50.0) | 12 |
| Olive | green | #808000 | (52.0, -10.0, 45.0) | 12 |
| Sage | green | #B2AC88 | (70.0, -8.0, 18.0) | 12 |
| Mint | green | #98FF98 | (91.0, -45.0, 26.0) | 12 |
| Emerald | green | #50C878 | (72.0, -48.0, 28.0) | 12 |
| Lime | green | #BFFF00 | (89.0, -54.0, 85.0) | 12 |
| Blue | blue | #0000FF | (32.0, 79.0, -108.0) | 12 |
| Navy | blue | #000080 | (13.0, 38.0, -52.0) | 12 |
| Cobalt Blue | blue | #0047AB | (34.0, 18.0, -63.0) | 12 |
| Azure | blue | #007FFF | (55.0, 18.0, -70.0) | 12 |
| Sky Blue | blue | #87CEEB | (79.0, -14.0, -22.0) | 12 |
| Denim Blue | blue | #1560BD | (42.0, 2.0, -51.0) | 12 |
| Purple | purple | #800080 | (29.0, 58.0, -36.0) | 12 |
| Violet | purple | #8F00FF | (40.0, 83.0, -93.0) | 12 |
| Lavender | purple | #E6E6FA | (92.0, 4.0, -8.0) | 12 |
| Pink | pink | #FFC0CB | (83.6, 24.1, 3.3) | 12 |
| Powder Pink | pink | #FADADD | (89.0, 11.0, 3.0) | 12 |
| Fuchsia | pink | #FF00FF | (60.0, 98.0, -61.0) | 12 |
| Rose Pink | pink | #FF66CC | (67.0, 63.0, -10.0) | 12 |

The production database may contain additional legacy colors. The migration preserves them; therefore post-migration live counts may exceed these seed-file counts.

## 15.7 Lexicon Dataset Coverage

- Total mappings: **500**.
- Minimum/maximum: **12/13** terms per seeded canonical color.
- Average/median: **12.50/12.50**.
- Low-coverage seeded colors below 10 mappings: **none**.
- Low-confidence mappings: **8** (`smoke, stone, nude, sand, camel, wine, rust, rose`).
- Ambiguous terms: **smoke, stone, nude, sand, camel, wine, rust, rose**. They are contextual and weighted below 0.60.
- Potential semantic overlap is intentional where a shade may also be used as a broad descriptor. Exact terms map to the specific canonical shade; hierarchy supplies broader aggregation.

| Source category | Mapping count |
| --- | --- |
| cosmetic | 40 |
| designer | 40 |
| editorial | 20 |
| fashion | 40 |
| luxury | 40 |
| manual | 40 |
| marketing | 40 |
| regional | 40 |
| retail | 40 |
| social_media | 40 |
| streetwear | 40 |
| textile | 40 |
| vintage | 40 |

| Canonical color | Mapping count |
| --- | --- |
| Black | 13 |
| Charcoal | 13 |
| Gray | 13 |
| Silver | 13 |
| White | 13 |
| Ivory | 13 |
| Cream | 13 |
| Beige | 13 |
| Tan | 13 |
| Brown | 13 |
| Chocolate | 13 |
| Red | 13 |
| Scarlet | 13 |
| Crimson | 13 |
| Burgundy | 13 |
| Coral Red | 13 |
| Orange | 13 |
| Peach | 13 |
| Yellow | 13 |
| Butter Yellow | 13 |
| Gold | 12 |
| Green | 12 |
| Olive | 12 |
| Sage | 12 |
| Mint | 12 |
| Emerald | 12 |
| Lime | 12 |
| Blue | 12 |
| Navy | 12 |
| Cobalt Blue | 12 |
| Azure | 12 |
| Sky Blue | 12 |
| Denim Blue | 12 |
| Purple | 12 |
| Violet | 12 |
| Lavender | 12 |
| Pink | 12 |
| Powder Pink | 12 |
| Fuchsia | 12 |
| Rose Pink | 12 |

Sources are representative terminology categories, not claims that each phrase was verified in a named external publication or brand catalogue.

## 15.8 Term Normalization Rules

Implemented in SQL by `normalize_color_term`: trim; split lower/digit-to-upper camel-case boundaries; transliterate a defined common Latin accent set; lowercase; remove leading `#`/`@`; remove English possessive suffixes; convert hyphens, underscores, and slashes to spaces; replace remaining punctuation; collapse whitespace. Multiword terms remain space-delimited. Regional spellings such as `gray` and `grey` are explicit aliases because spelling replacement can change meaning across languages. `#CherryRed` is supported by implemented camel-case splitting; fully lowercase `#cherryred` is not generically split and would require an explicit alias.

| Input | Normalized |
| --- | --- |
| Cherry Red | cherry red |
| cherry-red | cherry red |
| cherry   red | cherry red |
| #CherryRed | cherry red |
| CHERRY RED | cherry red |
| crème | creme |
| designer's blue | designer blue |
| blue/green | blue green |
| powder_pink | powder pink |
| @MidnightNavy | midnight navy |

Application code must call the database function or mirror it exactly before lookup. Future work should use locale-aware Unicode normalization rather than expanding the fixed transliteration list indefinitely. Lemmatization and n-gram extraction remain application responsibilities and are not falsely claimed as database normalization.

## 15.9 Color Hierarchy Summary

- Seed relationships: **29**.
- Parent colors: **11**.
- Intended seed depth: **1 edge**; recommended operational maximum: **2 edges**.
- All 40 seeded colors participate as a parent or child.
- Self-reference is blocked by CHECK; multi-row cycles are detected by recursive validation SQL, not by the CHECK.
- Limitation: one parent per seeded shade and hue-only rollups simplify colors that could reasonably belong to multiple families.

- Black: Charcoal
- Gray: Silver
- White: Ivory, Cream
- Brown: Beige, Tan, Chocolate
- Red: Scarlet, Crimson, Burgundy, Coral Red
- Orange: Peach
- Yellow: Butter Yellow, Gold
- Green: Olive, Sage, Mint, Emerald, Lime
- Blue: Navy, Cobalt Blue, Azure, Sky Blue, Denim Blue
- Purple: Violet, Lavender
- Pink: Powder Pink, Fuchsia, Rose Pink

## 15.10 LAB Mapping Methodology

Representative centroids came from the existing project dictionary where present and familiar sRGB references for newly added family roots. Boxes were generated by bounded family-specific tolerances around each centroid and clipped to L* [0,100], a*/b* [-128,127]. They are capstone-scale deterministic initialization rules, **not laboratory-validated measurements**.

Rule overlap is unavoidable for nearby shades and is detected by 006. Resolution order is: collect all containing boxes; calculate distance to each corresponding canonical centroid; choose the smallest distance; use `color_id` only as a deterministic final tie-breaker; log close distances for review. If no box matches, compare against all non-null centroids. Future calibration should sample masked garment pixels under representative lighting, compare predicted/annotated labels, optimize boundaries, and version the calibrated rule set.

| Canonical color | Centroid | Rule boundaries | Overlap status | Notes |
| --- | --- | --- | --- | --- |
| Black | (0.0, 0.0, 0.0) | L[0.0,6.0] a[-5.0,5.0] b[-6.0,6.0] | Potential; run 006 | Representative initialization |
| Charcoal | (29.0, -2.0, -8.0) | L[23.0,35.0] a[-7.0,3.0] b[-14.0,-2.0] | Potential; run 006 | Representative initialization |
| Gray | (53.6, 0.0, 0.0) | L[47.6,59.6] a[-5.0,5.0] b[-6.0,6.0] | Potential; run 006 | Representative initialization |
| Silver | (78.0, 0.0, 0.0) | L[72.0,84.0] a[-5.0,5.0] b[-6.0,6.0] | Potential; run 006 | Representative initialization |
| White | (100.0, 0.0, 0.0) | L[94.0,100.0] a[-5.0,5.0] b[-6.0,6.0] | Potential; run 006 | Representative initialization |
| Ivory | (98.0, -2.0, 8.0) | L[92.0,100.0] a[-7.0,3.0] b[2.0,14.0] | Potential; run 006 | Representative initialization |
| Cream | (97.0, -5.0, 18.0) | L[91.0,100.0] a[-10.0,0.0] b[12.0,24.0] | Potential; run 006 | Representative initialization |
| Beige | (82.0, 3.0, 21.0) | L[76.0,88.0] a[-2.0,8.0] b[15.0,27.0] | Potential; run 006 | Representative initialization |
| Tan | (75.0, 6.0, 23.0) | L[68.0,82.0] a[-2.0,14.0] b[13.0,33.0] | Potential; run 006 | Representative initialization |
| Brown | (37.5, 26.4, 40.9) | L[30.5,44.5] a[18.4,34.4] b[30.9,50.9] | Potential; run 006 | Representative initialization |
| Chocolate | (28.0, 14.0, 26.0) | L[21.0,35.0] a[6.0,22.0] b[16.0,36.0] | Potential; run 006 | Representative initialization |
| Red | (53.0, 80.0, 67.0) | L[46.0,60.0] a[70.0,90.0] b[57.0,77.0] | Potential; run 006 | Representative initialization |
| Scarlet | (54.0, 79.0, 69.0) | L[47.0,61.0] a[69.0,89.0] b[59.0,79.0] | Potential; run 006 | Representative initialization |
| Crimson | (47.0, 70.0, 33.0) | L[40.0,54.0] a[60.0,80.0] b[23.0,43.0] | Potential; run 006 | Representative initialization |
| Burgundy | (26.0, 48.0, 12.0) | L[19.0,33.0] a[38.0,58.0] b[2.0,22.0] | Potential; run 006 | Representative initialization |
| Coral Red | (68.0, 49.0, 31.0) | L[61.0,75.0] a[39.0,59.0] b[21.0,41.0] | Potential; run 006 | Representative initialization |
| Orange | (74.0, 23.0, 78.0) | L[67.0,81.0] a[14.0,32.0] b[68.0,88.0] | Potential; run 006 | Representative initialization |
| Peach | (91.0, 5.0, 27.0) | L[84.0,98.0] a[-4.0,14.0] b[17.0,37.0] | Potential; run 006 | Representative initialization |
| Yellow | (97.0, -22.0, 94.0) | L[91.0,100.0] a[-31.0,-13.0] b[84.0,104.0] | Potential; run 006 | Representative initialization |
| Butter Yellow | (89.0, -8.0, 48.0) | L[83.0,95.0] a[-17.0,1.0] b[38.0,58.0] | Potential; run 006 | Representative initialization |
| Gold | (86.0, -1.0, 87.0) | L[80.0,92.0] a[-10.0,8.0] b[77.0,97.0] | Potential; run 006 | Representative initialization |
| Green | (46.0, -52.0, 50.0) | L[39.0,53.0] a[-62.0,-42.0] b[40.0,60.0] | Potential; run 006 | Representative initialization |
| Olive | (52.0, -10.0, 45.0) | L[45.0,59.0] a[-20.0,0.0] b[35.0,55.0] | Potential; run 006 | Representative initialization |
| Sage | (70.0, -8.0, 18.0) | L[63.0,77.0] a[-18.0,2.0] b[8.0,28.0] | Potential; run 006 | Representative initialization |
| Mint | (91.0, -45.0, 26.0) | L[84.0,98.0] a[-55.0,-35.0] b[16.0,36.0] | Potential; run 006 | Representative initialization |
| Emerald | (72.0, -48.0, 28.0) | L[65.0,79.0] a[-58.0,-38.0] b[18.0,38.0] | Potential; run 006 | Representative initialization |
| Lime | (89.0, -54.0, 85.0) | L[82.0,96.0] a[-64.0,-44.0] b[75.0,95.0] | Potential; run 006 | Representative initialization |
| Blue | (32.0, 79.0, -108.0) | L[25.0,39.0] a[69.0,89.0] b[-119.0,-97.0] | Potential; run 006 | Representative initialization |
| Navy | (13.0, 38.0, -52.0) | L[6.0,20.0] a[28.0,48.0] b[-63.0,-41.0] | Potential; run 006 | Representative initialization |
| Cobalt Blue | (34.0, 18.0, -63.0) | L[27.0,41.0] a[8.0,28.0] b[-74.0,-52.0] | Potential; run 006 | Representative initialization |
| Azure | (55.0, 18.0, -70.0) | L[48.0,62.0] a[8.0,28.0] b[-81.0,-59.0] | Potential; run 006 | Representative initialization |
| Sky Blue | (79.0, -14.0, -22.0) | L[72.0,86.0] a[-24.0,-4.0] b[-33.0,-11.0] | Potential; run 006 | Representative initialization |
| Denim Blue | (42.0, 2.0, -51.0) | L[35.0,49.0] a[-8.0,12.0] b[-62.0,-40.0] | Potential; run 006 | Representative initialization |
| Purple | (29.0, 58.0, -36.0) | L[22.0,36.0] a[48.0,68.0] b[-47.0,-25.0] | Potential; run 006 | Representative initialization |
| Violet | (40.0, 83.0, -93.0) | L[33.0,47.0] a[73.0,93.0] b[-104.0,-82.0] | Potential; run 006 | Representative initialization |
| Lavender | (92.0, 4.0, -8.0) | L[85.0,99.0] a[-6.0,14.0] b[-19.0,3.0] | Potential; run 006 | Representative initialization |
| Pink | (83.6, 24.1, 3.3) | L[76.6,90.6] a[14.1,34.1] b[-5.7,12.3] | Potential; run 006 | Representative initialization |
| Powder Pink | (89.0, 11.0, 3.0) | L[82.0,96.0] a[1.0,21.0] b[-6.0,12.0] | Potential; run 006 | Representative initialization |
| Fuchsia | (60.0, 98.0, -61.0) | L[53.0,67.0] a[88.0,108.0] b[-70.0,-52.0] | Potential; run 006 | Representative initialization |
| Rose Pink | (67.0, 63.0, -10.0) | L[60.0,74.0] a[53.0,73.0] b[-19.0,-1.0] | Potential; run 006 | Representative initialization |

## 15.11 Index and Performance Report

| Index | Table | Columns/expression | Method | Query | Benefit | Write cost | Storage | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| uq_color_canonical_canonical_name | color_canonical | canonical_name | B-tree/unique | Exact canonical lookup | Deterministic name identity | Moderate | Small | Essential |
| uq_color_canonical_name_lower | color_canonical | lower(canonical_name) | B-tree/unique | Case-insensitive identity | Prevents case duplicates | Moderate | Small | Essential |
| idx_color_canonical_family | color_canonical | color_family, color_id | B-tree | Family rollup | Fast grouping/filter | Low | Small | Essential |
| uq_color_lexicon_normalized_term | color_lexicon | normalized_term | B-tree/unique | Exact NLP lookup | Single-row resolution | Moderate | Medium | Essential |
| idx_color_lexicon_color | color_lexicon | color_id INCLUDE (...)  | B-tree | Coverage/joins | Index-only summaries | Moderate | Medium | Essential |
| idx_color_lexicon_normalized_trgm | color_lexicon | normalized_term gin_trgm_ops | GIN | Fuzzy NLP review | Fast similarity candidates | Higher | Higher | Optional operationally; delivered |
| pk_color_hierarchy | color_hierarchy | parent_color_id, child_color_id | B-tree/unique | Parent-to-child traversal | Fast rollup | Low | Small | Essential |
| idx_color_hierarchy_child | color_hierarchy | child_color_id, parent_color_id | B-tree | Child-to-parent traversal | Fast reverse lookup | Low | Small | Essential |
| idx_color_lab_rules_color | color_lab_mapping_rules | color_id | B-tree | Rules by canonical color | Fast calibration queries | Low | Small | Essential |
| idx_color_lab_rules_l_candidate | color_lab_mapping_rules | L bounds INCLUDE remaining bounds | B-tree | LAB candidate pruning | Prunes by lightness first | Moderate | Medium | Essential at scale |

Exact normalized lookup should be the default. Extract longest 1-3 token n-grams first, enforce fashion context, and use confidence thresholds to reduce false positives. `pg_trgm` fuzzy matching is for candidate review or conservative fallback, not automatic assignment without thresholds.

LAB candidate pruning starts with L* because the B-tree can narrow lightness before checking chromatic bounds. At current cardinality, a full scan is also cheap. Future scale can evaluate range/GiST or a calibrated vector service. Analytics should group fact tables by stable `color_id`, join family only when needed, and consider materialized family/time rollups after query volume justifies refresh complexity.

## 15.12 Validation and Data Quality Results

The migration set was executed on **2026-08-03** against the configured AWS PostgreSQL **17.9** database using PostgreSQL 16-compatible SQL. Before commit, the complete migration and validation path was executed in a rollback-only transaction. After deployment, validation returned **21 PASS, 5 WARNING, and 0 FAIL** results. The warnings are expected governance/calibration work: eight low-confidence aliases, 20 overlapping LAB boxes, and 130 preserved legacy colors outside this 40-color module seed that lack lexicon, LAB-rule, and hierarchy coverage.

The first standalone validation attempt failed before checks ran because the script attempted to create a temporary result table inside a read-only transaction. The script was corrected to use a normal transaction with an `ON COMMIT DROP` temporary table and was then rerun successfully; no persistent validation objects are created. A pre-deployment schema dump was attempted but not produced because an unsupported client flag was supplied. A 60,132-byte post-deployment schema snapshot was created at `/tmp/post_color_lexicon_schema_20260803.sql`; this temporary file is not a substitute for the project’s normal durable backup policy.

An idempotency rerun of migrations 001-005 completed successfully. Counts remained 170 canonical colors, 500 lexicon mappings, 29 hierarchy relationships, and 40 LAB rules. The rollback-only rehearsal advanced PostgreSQL sequences because sequence increments are nontransactional; this created harmless identifier gaps for newly inserted seed objects, but it did not change or reuse any existing `color_id`.

| Query | Purpose | Expected | Actual | Status | Corrective action |
| --- | --- | --- | --- | --- | --- |
| count_color_canonical | See documented check in 006 | At least generated seed count | 170 | PASS | None |
| count_color_lexicon | See documented check in 006 | At least generated seed count | 500 | PASS | None |
| count_color_hierarchy | See documented check in 006 | At least generated seed count | 29 | PASS | None |
| count_color_lab_mapping_rules | See documented check in 006 | At least generated seed count | 40 | PASS | None |
| duplicate_canonical_names | See documented check in 006 | 0 | 0 | PASS | None |
| duplicate_normalized_terms | See documented check in 006 | 0 | 0 | PASS | None |
| empty_terms | See documented check in 006 | 0 | 0 | PASS | None |
| empty_normalized_terms | See documented check in 006 | 0 | 0 | PASS | None |
| inconsistent_normalization | See documented check in 006 | 0 | 0 | PASS | None |
| invalid_confidence_weights | See documented check in 006 | 0 | 0 | PASS | None |
| low_confidence_terms | See documented check in 006 | Review expected | 8 | WARNING | Keep below 0.60 out of automatic matching; require context/human review. |
| invalid_hex_values | See documented check in 006 | 0 | 0 | PASS | None |
| invalid_lab_centroids | See documented check in 006 | 0 | 0 | PASS | None |
| invalid_lab_rule_boundaries | See documented check in 006 | 0 | 0 | PASS | None |
| lab_min_greater_than_max | See documented check in 006 | 0 | 0 | PASS | None |
| orphaned_lexicon_rows | See documented check in 006 | 0 | 0 | PASS | None |
| orphaned_hierarchy_rows | See documented check in 006 | 0 | 0 | PASS | None |
| orphaned_lab_rules | See documented check in 006 | 0 | 0 | PASS | None |
| self_referential_hierarchy | See documented check in 006 | 0 | 0 | PASS | None |
| duplicate_hierarchy_relationships | See documented check in 006 | 0 | 0 | PASS | None |
| multi_level_hierarchy_cycles | See documented check in 006 | 0 | 0 | PASS | None |
| lab_rule_overlaps | See documented check in 006 | 0 ideal; review nonzero | 20 | WARNING | Use nearest centroid and calibrate with labeled garment images. |
| canonical_without_lexicon | See documented check in 006 | 0 ideal; legacy expansion reviewed | 130 | WARNING | Prioritize lexicon coverage for the 130 preserved legacy colors by usage. |
| canonical_without_lab_rule | See documented check in 006 | 0 ideal; legacy expansion reviewed | 130 | WARNING | Add calibrated rules only for legacy colors enabled in CV. |
| canonical_without_hierarchy | See documented check in 006 | 0 ideal; legacy expansion reviewed | 130 | WARNING | Govern and seed additional legacy rollups in a later migration. |
| source_categories_low_coverage | See documented check in 006 | 0 | 0 | PASS | None |

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

Expected seed-file contributions are 40 canonical upserts, 500 lexicon upserts, 29 hierarchy inserts, and 40 LAB inserts. Existing rows can make live totals larger. SQL files are transactional. Reruns use `IF NOT EXISTS`/upserts. Migration 001 intentionally fails on two physical canonical tables. A committed DDL rollback requires a reviewed inverse migration; take a schema backup/snapshot before production deployment. After deployment, verify relation kinds, foreign keys, counts, normalization examples, low-confidence rows, overlaps, and current application reads through `colors`.

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
