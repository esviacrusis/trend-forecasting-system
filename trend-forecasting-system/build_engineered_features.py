"""
build_engineered_features.py

Author: Eric
Last Updated: April 25, 2026
Revision: Season-aware rewrite using runway-derived season/year

Purpose
- Build season-level engineered features for forecasting
- Derive season/year from runway metadata (shows -> runway_color_presence)
- Aggregate platform and trends signals within a runway-based feature window
- Insert/upsert rows into engineered_features

Design rules
1. season/year MUST NOT be hardcoded
2. season/year MUST NOT come from platform_color_signal
3. shows is the source of truth for season/year
4. platform_color_signal is only a time-bucketed signal layer
5. adoption_curve must match the PostgreSQL enum values exactly:
   - fast_spike
   - slow_burn
   - steady
   - volatile
   - unknown

Output grain
- one row per:
  (color_id, season, year, feature_window_start, feature_window_end, run_id)

Notes
- This is still a capstone-friendly implementation
- Editorial features remain NULL for now
- run_id is supported but optional in this file
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_batch

from config import Config


def get_connection():
    """
    Create and return a PostgreSQL connection.
    """
    return psycopg2.connect(**Config.from_env().db_connection_params())


def fetch_runway_context(conn) -> List[Tuple]:
    """
    Build one runway season context row per color_id, season, year.

    Source of truth:
    - shows.season
    - shows.year
    - shows.show_date
    - runway_color_presence.color_id

    Returns one row per:
    - color_id
    - season
    - year

    Fields returned:
    - color_id
    - season
    - year
    - first_show_date
    - last_show_date
    - runway_looks_with_color
    - runway_prominence_score
    """

    sql = """
        SELECT
            rcp.color_id,
            s.season,
            s.year,
            MIN(s.show_date) AS first_show_date,
            MAX(s.show_date) AS last_show_date,
            COUNT(DISTINCT rcp.look_id) AS runway_looks_with_color,
            SUM(rcp.prominence_score) AS runway_prominence_score
        FROM runway_color_presence rcp
        JOIN shows s
          ON rcp.show_id = s.show_id
        WHERE s.season IS NOT NULL
          AND s.year IS NOT NULL
          AND s.show_date IS NOT NULL
        GROUP BY rcp.color_id, s.season, s.year
        ORDER BY s.year, s.season, rcp.color_id
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def derive_feature_window(first_show_date, last_show_date):
    """
    Define the feature window for one runway season.

    MVP rule:
    - start at first runway show date
    - end 28 days after the last runway show date
    """

    if first_show_date is None or last_show_date is None:
        raise ValueError("Cannot derive feature window without runway show dates")

    feature_window_start = first_show_date
    feature_window_end = last_show_date + timedelta(days=28)

    return feature_window_start, feature_window_end


def fetch_platform_metrics(conn, color_id, window_start, window_end) -> Dict[str, Any]:
    """
    Aggregate platform_color_signal for one color within one feature window.

    Returns:
    - twitter_weighted_engagement
    - instagram_weighted_engagement
    - cross_platform_coverage
    - avg_velocity_score
    - avg_persistence_score
    - total_mentions
    - avg_sentiment
    - active_days
    - first_seen
    - last_seen
    """

    sql = """
        SELECT
            p.name AS platform_name,
            AVG(pcs.weighted_engagement) AS avg_weighted_engagement,
            AVG(pcs.velocity_score) AS avg_velocity_score,
            AVG(pcs.persistence_score) AS avg_persistence_score,
            SUM(pcs.mention_count) AS total_mentions,
            AVG(pcs.avg_sentiment) AS avg_sentiment,
            COUNT(DISTINCT pcs.time_bucket_start) AS active_days,
            MIN(pcs.time_bucket_start) AS first_seen,
            MAX(pcs.time_bucket_end) AS last_seen
        FROM platform_color_signal pcs
        JOIN platforms p
          ON pcs.platform_id = p.platform_id
        WHERE pcs.color_id = %s
          AND pcs.time_bucket_start >= %s
          AND pcs.time_bucket_end <= %s
        GROUP BY p.name
    """

    with conn.cursor() as cur:
        cur.execute(sql, (color_id, window_start, window_end))
        rows = cur.fetchall()

    twitter_weighted_engagement = None
    instagram_weighted_engagement = None
    velocity_scores: List[float] = []
    persistence_scores: List[float] = []
    mention_totals: List[int] = []
    sentiments: List[float] = []
    active_days_values: List[int] = []
    first_seen_values = []
    last_seen_values = []

    for (
        platform_name,
        avg_weighted_engagement,
        avg_velocity_score,
        avg_persistence_score,
        total_mentions,
        avg_sentiment,
        active_days,
        first_seen,
        last_seen,
    ) in rows:
        if platform_name == "twitter":
            twitter_weighted_engagement = avg_weighted_engagement
        elif platform_name == "instagram":
            instagram_weighted_engagement = avg_weighted_engagement

        if avg_velocity_score is not None:
            velocity_scores.append(float(avg_velocity_score))

        if avg_persistence_score is not None:
            persistence_scores.append(float(avg_persistence_score))

        if total_mentions is not None:
            mention_totals.append(int(total_mentions))

        if avg_sentiment is not None:
            sentiments.append(float(avg_sentiment))

        if active_days is not None:
            active_days_values.append(int(active_days))

        if first_seen is not None:
            first_seen_values.append(first_seen)

        if last_seen is not None:
            last_seen_values.append(last_seen)

    return {
        "twitter_weighted_engagement": twitter_weighted_engagement,
        "instagram_weighted_engagement": instagram_weighted_engagement,
        "cross_platform_coverage": len(rows),
        "avg_velocity_score": (
            sum(velocity_scores) / len(velocity_scores) if velocity_scores else None
        ),
        "avg_persistence_score": (
            sum(persistence_scores) / len(persistence_scores) if persistence_scores else None
        ),
        "total_mentions": sum(mention_totals) if mention_totals else 0,
        "avg_sentiment": (sum(sentiments) / len(sentiments)) if sentiments else None,
        "active_days": max(active_days_values) if active_days_values else 0,
        "first_seen": min(first_seen_values) if first_seen_values else None,
        "last_seen": max(last_seen_values) if last_seen_values else None,
    }


def fetch_trends_metrics(conn, color_id, window_start, window_end) -> Dict[str, Any]:
    """
    Aggregate trends_signal for one color within one feature window.

    Uses trends_signal fields aligned to the schema.

    Returns:
    - google_trends_avg_index
    - google_trends_acceleration
    - time_to_peak_days
    """

    sql = """
        SELECT
            AVG(search_score) AS google_trends_avg_index,
            AVG(diffusion_speed) AS google_trends_acceleration,
            AVG(time_to_peak_days) AS time_to_peak_days
        FROM trends_signal
        WHERE color_id = %s
          AND window_start >= %s
          AND window_end <= %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (color_id, window_start, window_end))
        row = cur.fetchone()

    if not row:
        return {
            "google_trends_avg_index": None,
            "google_trends_acceleration": None,
            "time_to_peak_days": None,
        }

    return {
        "google_trends_avg_index": row[0],
        "google_trends_acceleration": row[1],
        "time_to_peak_days": row[2],
    }


def classify_adoption_curve(
    avg_velocity_score,
    avg_persistence_score,
    active_days,
    total_mentions,
):
    """
    Classify the trend lifecycle using enum-safe labels only.

    Allowed enum values:
    - fast_spike
    - slow_burn
    - steady
    - volatile
    - unknown
    """

    if avg_velocity_score is None or avg_persistence_score is None:
        return "unknown"

    velocity = float(avg_velocity_score)
    persistence = float(avg_persistence_score)
    days = int(active_days) if active_days is not None else 0
    mentions = int(total_mentions) if total_mentions is not None else 0

    # High momentum but low staying power
    if velocity >= 0.75 and persistence < 0.45:
        return "fast_spike"

    # Strong momentum plus sustained persistence
    if velocity >= 0.60 and persistence >= 0.50 and days >= 5 and mentions >= 20:
        return "slow_burn"

    # Moderate, consistent signal
    if 0.30 <= velocity < 0.60 and persistence >= 0.45:
        return "steady"

    # Strong but unstable / mixed pattern
    if velocity >= 0.60 and persistence >= 0.70:
        return "volatile"

    return "unknown"


def build_rows(
    conn,
    runway_context_rows: List[Tuple],
    run_id: Optional[str] = None,
) -> List[Tuple]:
    """
    Build insert-ready rows for engineered_features starting from runway context.
    """

    rows_to_insert = []

    for (
        color_id,
        season,
        year,
        first_show_date,
        last_show_date,
        runway_looks_with_color,
        runway_prominence_score,
    ) in runway_context_rows:
        feature_window_start, feature_window_end = derive_feature_window(
            first_show_date, last_show_date
        )

        platform_metrics = fetch_platform_metrics(
            conn=conn,
            color_id=color_id,
            window_start=feature_window_start,
            window_end=feature_window_end,
        )

        trends_metrics = fetch_trends_metrics(
            conn=conn,
            color_id=color_id,
            window_start=feature_window_start,
            window_end=feature_window_end,
        )

        adoption_curve = classify_adoption_curve(
            avg_velocity_score=platform_metrics["avg_velocity_score"],
            avg_persistence_score=platform_metrics["avg_persistence_score"],
            active_days=platform_metrics["active_days"],
            total_mentions=platform_metrics["total_mentions"],
        )

        features_json = {
            "total_mentions": int(platform_metrics["total_mentions"]),
            "avg_sentiment": (
                round(float(platform_metrics["avg_sentiment"]), 3)
                if platform_metrics["avg_sentiment"] is not None
                else None
            ),
            "active_days": int(platform_metrics["active_days"]),
            "first_seen": (
                str(platform_metrics["first_seen"])
                if platform_metrics["first_seen"] is not None
                else None
            ),
            "last_seen": (
                str(platform_metrics["last_seen"])
                if platform_metrics["last_seen"] is not None
                else None
            ),
            "first_show_date": str(first_show_date) if first_show_date is not None else None,
            "last_show_date": str(last_show_date) if last_show_date is not None else None,
        }

        row = (
            color_id,  # color_id
            season,  # season
            int(year),  # year
            feature_window_start,  # feature_window_start
            feature_window_end,  # feature_window_end
            int(runway_looks_with_color) if runway_looks_with_color is not None else None,
            (
                round(float(runway_prominence_score), 3)
                if runway_prominence_score is not None
                else None
            ),
            None,  # editorial_mention_count
            None,  # editorial_weighted_score
            (
                round(float(platform_metrics["twitter_weighted_engagement"]), 3)
                if platform_metrics["twitter_weighted_engagement"] is not None
                else None
            ),
            (
                round(float(platform_metrics["instagram_weighted_engagement"]), 3)
                if platform_metrics["instagram_weighted_engagement"] is not None
                else None
            ),
            int(platform_metrics["cross_platform_coverage"]),
            (
                round(float(platform_metrics["avg_velocity_score"]), 3)
                if platform_metrics["avg_velocity_score"] is not None
                else None
            ),
            (
                round(float(platform_metrics["avg_persistence_score"]), 3)
                if platform_metrics["avg_persistence_score"] is not None
                else None
            ),
            (
                round(float(trends_metrics["google_trends_avg_index"]), 3)
                if trends_metrics["google_trends_avg_index"] is not None
                else None
            ),
            (
                round(float(trends_metrics["google_trends_acceleration"]), 3)
                if trends_metrics["google_trends_acceleration"] is not None
                else None
            ),
            (
                int(round(float(trends_metrics["time_to_peak_days"])))
                if trends_metrics["time_to_peak_days"] is not None
                else None
            ),
            adoption_curve,  # adoption_curve
            json.dumps(features_json),  # features_json
            run_id,  # run_id
        )

        rows_to_insert.append(row)

    return rows_to_insert


def insert_engineered_features(conn, rows: List[Tuple]) -> None:
    """
    Upsert engineered feature rows into engineered_features.

    Important note:
    - If run_id is NULL, PostgreSQL uniqueness will allow multiple rows
      because NULL values do not collide in a UNIQUE constraint.
    - For strict idempotency across reruns, pass a real run_id.
    """

    sql = """
        INSERT INTO engineered_features (
            color_id,
            season,
            year,
            feature_window_start,
            feature_window_end,
            runway_looks_with_color,
            runway_prominence_score,
            editorial_mention_count,
            editorial_weighted_score,
            twitter_weighted_engagement,
            instagram_weighted_engagement,
            cross_platform_coverage,
            avg_velocity_score,
            avg_persistence_score,
            google_trends_avg_index,
            google_trends_acceleration,
            time_to_peak_days,
            adoption_curve,
            features_json,
            run_id
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (
            color_id,
            season,
            year,
            feature_window_start,
            feature_window_end,
            run_id
        )
        DO UPDATE SET
            runway_looks_with_color = EXCLUDED.runway_looks_with_color,
            runway_prominence_score = EXCLUDED.runway_prominence_score,
            editorial_mention_count = EXCLUDED.editorial_mention_count,
            editorial_weighted_score = EXCLUDED.editorial_weighted_score,
            twitter_weighted_engagement = EXCLUDED.twitter_weighted_engagement,
            instagram_weighted_engagement = EXCLUDED.instagram_weighted_engagement,
            cross_platform_coverage = EXCLUDED.cross_platform_coverage,
            avg_velocity_score = EXCLUDED.avg_velocity_score,
            avg_persistence_score = EXCLUDED.avg_persistence_score,
            google_trends_avg_index = EXCLUDED.google_trends_avg_index,
            google_trends_acceleration = EXCLUDED.google_trends_acceleration,
            time_to_peak_days = EXCLUDED.time_to_peak_days,
            adoption_curve = EXCLUDED.adoption_curve,
            features_json = EXCLUDED.features_json
    """

    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=100)

    conn.commit()


def main(run_id: Optional[str] = None):
    """
    Main pipeline step:
    1. Derive runway color-season-year contexts from shows + runway_color_presence
    2. Build platform/trends feature aggregates inside the derived feature window
    3. Upsert rows into engineered_features
    """

    conn = get_connection()

    try:
        runway_context_rows = fetch_runway_context(conn)

        if not runway_context_rows:
            raise ValueError(
                "No runway season/year context found. Cannot build engineered_features."
            )

        print(f"Found {len(runway_context_rows)} runway color-season contexts")

        insert_rows = build_rows(conn, runway_context_rows, run_id=run_id)
        print(f"Built {len(insert_rows)} engineered feature rows")

        insert_engineered_features(conn, insert_rows)
        print(f"Upserted {len(insert_rows)} rows into engineered_features")

    except Exception as e:
        conn.rollback()
        print(f"Error building engineered_features: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
