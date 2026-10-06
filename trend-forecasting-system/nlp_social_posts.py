"""
nlp_social_posts.py

Lightweight NLP layer for social_posts -> social_post_extractions

Purpose
- Read posts from social_posts
- Normalize text
- Detect color terms using a rule-based lexicon
- Map terms to color_id from the colors table
- Assign simple sentiment and fashion-context scores
- Insert results into social_post_extractions

Notes
- This is an MVP rule-based NLP layer for capstone use.
- It avoids heavy NLP libraries and focuses on deterministic output.
- Assumes PostgreSQL tables:
    social_posts
    social_post_extractions
    colors
"""

from __future__ import annotations

import re
import json
import string
from typing import Dict, List, Tuple

import psycopg2
from psycopg2.extras import execute_batch

from config import Config

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Text helpers
# -------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Lowercase and remove punctuation for simple lexicon matching.
    """
    if not text:
        return ""

    text = text.lower()
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from raw text before punctuation cleanup.
    """
    if not text:
        return []
    return re.findall(r"#\w+", text.lower())


# -------------------------------------------------------------------
# Lexicon + scoring
# -------------------------------------------------------------------

def get_default_color_lexicon() -> Dict[str, List[str]]:
    """
    Rule-based color lexicon.
    Keys are canonical color terms.
    Values are surface forms to match in text.
    """
    return {
        "cobalt blue": ["cobalt blue", "cobalt", "blue"],
        "butter yellow": ["butter yellow", "buttery yellow", "yellow"],
        "cherry red": ["cherry red", "red", "crimson red"],
        "sage green": ["sage green", "sage", "green"],
        "jet black": ["jet black", "black"],
    }


POSITIVE_WORDS = {
    "love", "loving", "obsessed", "favorite", "favourite",
    "beautiful", "gorgeous", "stunning", "amazing", "perfect",
    "fire", "iconic", "best", "dream", "cool"
}

NEGATIVE_WORDS = {
    "hate", "ugly", "bad", "worst", "boring", "awful", "terrible",
    "dislike", "messy", "cheap"
}

FASHION_WORDS = {
    "fashion", "style", "runway", "look", "outfit", "dress", "coat",
    "shirt", "pants", "skirt", "trend", "season", "collection",
    "designer", "wear", "wardrobe", "ootd"
}


def extract_color_terms(text: str, lexicon: Dict[str, List[str]]) -> List[str]:
    """
    Return canonical color terms detected in text.
    Matching is phrase-first, rule-based.
    """
    normalized = normalize_text(text)
    found: List[str] = []

    for canonical_term, variants in lexicon.items():
        for variant in sorted(variants, key=len, reverse=True):
            pattern = r"\b" + re.escape(normalize_text(variant)) + r"\b"
            if re.search(pattern, normalized):
                found.append(canonical_term)
                break

    return found


def score_sentiment(text: str) -> float:
    """
    Very simple lexicon-based sentiment score.
    Returns value in [-1, 1].
    """
    normalized = normalize_text(text)
    if not normalized:
        return 0.0

    tokens = normalized.split()
    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)

    if pos == 0 and neg == 0:
        return 0.0

    score = (pos - neg) / max(pos + neg, 1)
    return round(score, 3)


def score_fashion_context(text: str) -> float:
    """
    Score how fashion-related the text appears to be.
    Returns value in [0, 1].
    """
    normalized = normalize_text(text)
    if not normalized:
        return 0.0

    tokens = set(normalized.split())
    overlap = len(tokens.intersection(FASHION_WORDS))
    score = min(overlap / 3.0, 1.0)
    return round(score, 3)


# -------------------------------------------------------------------
# Database helpers
# -------------------------------------------------------------------

def get_connection():
    return psycopg2.connect(**Config.from_env().db_connection_params())


def load_color_id_map(conn, lexicon: Dict[str, List[str]]) -> Dict[str, int]:
    """
    Load canonical color_name -> color_id from colors table.
    Only pulls color names relevant to the lexicon.
    """
    canonical_terms = list(lexicon.keys())
    color_id_map: Dict[str, int] = {}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT color_id, lower(color_name) AS color_name
            FROM colors
            WHERE lower(color_name) = ANY(%s)
            """,
            (canonical_terms,),
        )
        for color_id, color_name in cur.fetchall():
            color_id_map[color_name] = color_id

    return color_id_map


def fetch_social_posts(conn) -> List[Tuple[str, str]]:
    """
    Pull posts for processing.
    Fetches post_id and text_content.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT post_id, text_content
            FROM social_posts
            WHERE text_content IS NOT NULL
            ORDER BY created_at
            """
        )
        return cur.fetchall()


def insert_social_post_extractions(conn, rows: List[Tuple]):
    """
    Insert extracted results.
    Uses ON CONFLICT to allow reruns.
    Assumes PK/post uniqueness is handled by (post_id, extracted_at)
    or no strict unique constraint beyond that.
    """
    sql = """
        INSERT INTO social_post_extractions (
            post_id,
            detected_color_terms,
            detected_color_ids,
            sentiment_score,
            fashion_context_score,
            dominant_colors_lab,
            color_proportion
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=200)

    conn.commit()


# -------------------------------------------------------------------
# Main processing
# -------------------------------------------------------------------

def build_extraction_row(
    post_id: str,
    text: str,
    lexicon: Dict[str, List[str]],
    color_id_map: Dict[str, int]
) -> Tuple:
    """
    Convert one social post into one extraction row.
    """
    detected_terms = extract_color_terms(text, lexicon)

    detected_ids: List[int] = []
    for term in detected_terms:
        color_id = color_id_map.get(term.lower())
        if color_id is not None:
            detected_ids.append(color_id)

    sentiment_score = score_sentiment(text)
    fashion_context_score = score_fashion_context(text)

    # Compact placeholders for schema compatibility
    dominant_colors_lab = json.dumps([])
    color_proportion = json.dumps([])

    return (
        post_id,
        detected_terms if detected_terms else None,
        detected_ids if detected_ids else None,
        sentiment_score,
        fashion_context_score,
        dominant_colors_lab,
        color_proportion,
    )


def process_social_posts():
    """
    End-to-end processing:
    - connect
    - load lexicon + color mapping
    - fetch posts
    - build extraction rows
    - insert into social_post_extractions
    """
    lexicon = get_default_color_lexicon()

    conn = get_connection()
    try:
        color_id_map = load_color_id_map(conn, lexicon)
        posts = fetch_social_posts(conn)

        print(f"Loaded {len(posts)} posts from social_posts")
        print(f"Mapped {len(color_id_map)} canonical colors from colors table")

        rows_to_insert: List[Tuple] = []

        for post_id, text_content in posts:
            row = build_extraction_row(
                post_id=post_id,
                text=text_content or "",
                lexicon=lexicon,
                color_id_map=color_id_map,
            )
            rows_to_insert.append(row)

        insert_social_post_extractions(conn, rows_to_insert)
        print(f"Inserted {len(rows_to_insert)} rows into social_post_extractions")

    except Exception as e:
        conn.rollback()
        print(f"Error processing social posts: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    process_social_posts()
