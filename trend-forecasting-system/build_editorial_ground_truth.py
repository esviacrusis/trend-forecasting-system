#!/usr/bin/env python3
"""
build_editorial_ground_truth.py

Purpose:
    Load editorial article evidence from an Excel file and populate
    editorial_ground_truth by matching article color terms against the
    canonical colors table (color_name + synonyms).

Expected Excel columns:
    - Title
    - Date
    - Colors Mentioned
    - Styles/Trends Mentioned
    - URL

Pipeline order:
    1. build_platform_color_signal.py
    2. build_engineered_features.py
    3. build_editorial_ground_truth.py
    4. build_model_predictions.py
    5. build_trend_insights.py
    6. app.py
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Dict, List, Optional, Tuple

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch

from config import Config

DEFAULT_LABEL_SOURCE = "editorial_articles"
DEFAULT_LABEL_METHOD = "color_table_match"

# Broad or non-canonical terms that should not directly map to one color
STOP_TERMS = {
    "",
    "pastels",
    "pastel",
    "neutral",
    "neutrals",
    "neutral palette",
    "mixed palettes",
    "mixed palette",
    "prints",
    "print",
    "floral prints",
    "florals",
    "sheer",
    "lace",
    "beading",
    "sequins",
    "bubble hems",
    "fringe",
    "embellishment",
    "embellishments",
    "color",
    "colors",
}


def normalize_text(value: object) -> str:
    """Normalize text for case-insensitive matching."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    text = str(value).strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[;/|]", ",", text)
    text = re.sub(r"[\(\)\[\]\{\}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_color_terms(colors_mentioned: object) -> List[str]:
    """
    Split a Colors Mentioned cell into candidate terms.
    Example:
        'Butter yellow, soft powder pinks and mint greens'
    """
    text = normalize_text(colors_mentioned)
    if not text:
        return []

    parts = [p.strip() for p in text.split(",") if p.strip()]
    terms: List[str] = []

    for part in parts:
        subparts = [s.strip() for s in re.split(r"\band\b", part) if s.strip()]
        for sp in subparts:
            sp = re.sub(r"\s+", " ", sp).strip()
            if sp:
                terms.append(sp)

    return terms


def generate_candidate_terms(raw_term: str) -> List[str]:
    """
    Generate multiple candidate forms of a raw article term for matching
    against colors.color_name or colors.synonyms.

    This is lightweight normalization, not a separate manual dictionary.
    """
    term = normalize_text(raw_term)
    if not term:
        return []

    candidates = {term}

    # Remove common descriptive prefixes
    prefixes = [
        "soft ",
        "refreshing ",
        "creamy ",
        "bold ",
        "bright ",
        "deep ",
        "light ",
        "pale ",
        "dark ",
        "muted ",
        "dusty ",
        "warm ",
        "cool ",
        "accent of ",
        "accents of ",
        "shades of ",
        "hints of ",
        "touches of ",
    ]
    for prefix in prefixes:
        if term.startswith(prefix):
            candidates.add(term[len(prefix):].strip())

    # Singularize simple plurals
    if term.endswith("s") and len(term) > 3:
        candidates.add(term[:-1])

    # Remove common trailing generic words
    generic_suffixes = [" tones", " tone", " hues", " hue", " shades", " shade"]
    for suffix in generic_suffixes:
        if term.endswith(suffix):
            candidates.add(term[: -len(suffix)].strip())

    # Example: "soft powder pinks" -> "powder pinks" -> "powder pink"
    expanded = set(candidates)
    for cand in list(candidates):
        if cand.endswith("s") and len(cand) > 3:
            expanded.add(cand[:-1])

    final_candidates = [c.strip() for c in expanded if c.strip() and c.strip() not in STOP_TERMS]
    return sorted(set(final_candidates), key=len, reverse=True)


def get_connection():
    return psycopg2.connect(**Config.from_env().db_connection_params())


def load_color_lookup(conn) -> Dict[str, Tuple[int, str]]:
    """
    Build lookup from normalized term -> (color_id, canonical color_name)
    using:
      - colors.color_name
      - colors.synonyms
    """
    lookup: Dict[str, Tuple[int, str]] = {}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT color_id, color_name, synonyms
            FROM colors
        """)
        rows = cur.fetchall()

    for row in rows:
        color_id = row["color_id"]
        color_name = row["color_name"]
        synonyms = row["synonyms"]

        canonical = normalize_text(color_name)
        if canonical:
            lookup[canonical] = (color_id, color_name)

        if synonyms:
            for syn in synonyms:
                normalized_syn = normalize_text(syn)
                if normalized_syn:
                    lookup[normalized_syn] = (color_id, color_name)

    return lookup


def resolve_color_term(raw_term: str, color_lookup: Dict[str, Tuple[int, str]]) -> Optional[Tuple[int, str, str]]:
    """
    Returns:
        (color_id, canonical_color_name, matched_term)
    or None if not matched
    """
    candidates = generate_candidate_terms(raw_term)

    for cand in candidates:
        if cand in color_lookup:
            color_id, canonical_name = color_lookup[cand]
            return color_id, canonical_name, cand

    return None


def load_engineered_features(conn, season: str, year: int) -> List[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT feature_id, color_id, season, year
            FROM engineered_features
            WHERE season = %s
              AND year = %s
        """, (season, year))
        return cur.fetchall()


def build_note(title: str, article_date: object, url: str, matched_raw_term: str, matched_db_term: str, canonical_color: str) -> str:
    date_text = ""
    if pd.notna(article_date):
        try:
            date_text = pd.to_datetime(article_date).date().isoformat()
        except Exception:
            date_text = str(article_date)

    parts = [
        f"title={title}" if title else None,
        f"date={date_text}" if date_text else None,
        f"url={url}" if url else None,
        f"article_term={matched_raw_term}" if matched_raw_term else None,
        f"matched_term={matched_db_term}" if matched_db_term else None,
        f"canonical_color={canonical_color}" if canonical_color else None,
    ]
    return " | ".join([p for p in parts if p])


def upsert_ground_truth(conn, rows: List[Tuple[str, int, str, str, str]]) -> None:
    if not rows:
        return

    sql = """
        INSERT INTO editorial_ground_truth (
            feature_id,
            editorial_label,
            label_source,
            label_method,
            notes
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (feature_id)
        DO UPDATE SET
            editorial_label = EXCLUDED.editorial_label,
            label_source = EXCLUDED.label_source,
            label_method = EXCLUDED.label_method,
            notes = EXCLUDED.notes,
            annotated_at = now()
    """

    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=100)

    conn.commit()


def backfill_zero_labels(conn, season: str, year: int) -> int:
    """
    Optional:
    Insert label=0 for engineered_features rows that do not yet have a row
    in editorial_ground_truth.
    """
    sql = """
        INSERT INTO editorial_ground_truth (
            feature_id,
            editorial_label,
            label_source,
            label_method,
            notes
        )
        SELECT
            ef.feature_id,
            0,
            'editorial_articles',
            'no_matching_editorial_evidence',
            'No matching editorial evidence found during article import'
        FROM engineered_features ef
        LEFT JOIN editorial_ground_truth gt
            ON ef.feature_id = gt.feature_id
        WHERE ef.season = %s
          AND ef.year = %s
          AND gt.feature_id IS NULL
    """
    with conn.cursor() as cur:
        cur.execute(sql, (season, year))
        inserted = cur.rowcount

    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Build editorial_ground_truth from editorial Excel file using colors table.")
    parser.add_argument("--input", required=True, help="Path to Excel file")
    parser.add_argument("--season", required=True, help='Season in engineered_features, e.g. "SS 2025"')
    parser.add_argument("--year", required=True, type=int, help="Year in engineered_features, e.g. 2025")
    parser.add_argument("--sheet-name", default=0, help="Excel sheet name or index")
    parser.add_argument("--backfill-zero", action="store_true", help="Backfill label=0 for unmatched engineered_features rows")
    parser.add_argument("--verbose", action="store_true", help="Print diagnostics")
    args = parser.parse_args()

    try:
        df = pd.read_excel(args.input, sheet_name=args.sheet_name)
    except Exception as exc:
        print(f"ERROR reading Excel file: {exc}", file=sys.stderr)
        sys.exit(1)

    required_cols = {
        "Title",
        "Date",
        "Colors Mentioned",
        "Styles/Trends Mentioned",
        "URL",
    }
    missing = required_cols - set(df.columns)
    if missing:
        print(f"ERROR: missing required columns: {', '.join(sorted(missing))}", file=sys.stderr)
        sys.exit(1)

    conn = None
    try:
        conn = get_connection()

        color_lookup = load_color_lookup(conn)
        feature_rows = load_engineered_features(conn, args.season, args.year)

        if not feature_rows:
            print(f"ERROR: no engineered_features rows found for season={args.season}, year={args.year}", file=sys.stderr)
            sys.exit(1)

        # color_id -> feature_ids for this season/year
        color_to_features: Dict[int, List[str]] = {}
        for row in feature_rows:
            color_to_features.setdefault(row["color_id"], []).append(str(row["feature_id"]))

        matched_by_feature: Dict[str, List[str]] = {}
        unmatched_terms: Dict[str, int] = {}

        for _, row in df.iterrows():
            title = str(row["Title"]).strip() if pd.notna(row["Title"]) else ""
            article_date = row["Date"]
            url = str(row["URL"]).strip() if pd.notna(row["URL"]) else ""
            raw_terms = split_color_terms(row["Colors Mentioned"])

            for raw_term in raw_terms:
                match = resolve_color_term(raw_term, color_lookup)

                if not match:
                    unmatched_terms[raw_term] = unmatched_terms.get(raw_term, 0) + 1
                    continue

                color_id, canonical_name, matched_db_term = match
                feature_ids = color_to_features.get(color_id, [])

                if not feature_ids:
                    continue

                for feature_id in feature_ids:
                    note = build_note(
                        title=title,
                        article_date=article_date,
                        url=url,
                        matched_raw_term=raw_term,
                        matched_db_term=matched_db_term,
                        canonical_color=canonical_name,
                    )
                    matched_by_feature.setdefault(feature_id, []).append(note)

        upsert_rows: List[Tuple[str, int, str, str, str]] = []
        for feature_id, notes in matched_by_feature.items():
            merged_notes = " || ".join(sorted(set(notes)))
            upsert_rows.append(
                (
                    feature_id,
                    1,
                    DEFAULT_LABEL_SOURCE,
                    DEFAULT_LABEL_METHOD,
                    merged_notes,
                )
            )

        upsert_ground_truth(conn, upsert_rows)
        print(f"Inserted/updated {len(upsert_rows)} rows in editorial_ground_truth with editorial_label=1.")

        if args.backfill_zero:
            zero_count = backfill_zero_labels(conn, args.season, args.year)
            print(f"Inserted {zero_count} unmatched rows with editorial_label=0.")

        if args.verbose:
            print(f"Loaded {len(color_lookup)} color lookup terms from colors table.")
            print(f"Loaded {len(feature_rows)} engineered_features rows.")
            if unmatched_terms:
                print("\nUnmatched article color terms:")
                for term, count in sorted(unmatched_terms.items(), key=lambda x: (-x[1], x[0])):
                    print(f"  {term}: {count}")
            else:
                print("\nNo unmatched article color terms.")

    except Exception as exc:
        if conn is not None:
            conn.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
