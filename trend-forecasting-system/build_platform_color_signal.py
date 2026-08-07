"""
build_platform_color_signal.py

Purpose
- Aggregate post-level NLP outputs into platform_color_signal
- Joins:
    social_posts
    social_post_extractions
- Builds simple daily signal rows by:
    platform_id
    color_id
    created_at::date

MVP metrics
- mention_count
- avg_sentiment

Optional placeholders
- weighted_engagement
- velocity_score
- persistence_score
- lead_lag_index
- spike_flag
- run_id

Notes
- This is a capstone-friendly minimal builder.
- It assumes detected_color_ids is stored as an array in social_post_extractions.
"""

from __future__ import annotations

from typing import List, Tuple

import psycopg2
from psycopg2.extras import execute_batch

from config import Config


def get_connection():
    return psycopg2.connect(**Config.from_env().db_connection_params())


def fetch_aggregated_signals(conn) -> List[Tuple]:
    """
    Aggregate daily platform-color signals from social_posts + social_post_extractions.
    """

    sql = """
        SELECT
            sp.platform_id,
            color_id,
            DATE(sp.created_at) AS bucket_day,
            COUNT(*) AS mention_count,
            AVG(spe.sentiment_score) AS avg_sentiment
        FROM social_posts sp
        JOIN social_post_extractions spe
            ON sp.post_id = spe.post_id
        CROSS JOIN LATERAL unnest(spe.detected_color_ids) AS color_id
        WHERE spe.detected_color_ids IS NOT NULL
        GROUP BY
            sp.platform_id,
            color_id,
            DATE(sp.created_at)
        ORDER BY
            sp.platform_id,
            color_id,
            bucket_day
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def build_rows(aggregated_rows: List[Tuple]) -> List[Tuple]:
    """
    Convert aggregate query results into insert-ready rows.
    """
    rows_to_insert = []

    for platform_id, color_id, bucket_day, mention_count, avg_sentiment in aggregated_rows:
        row = (
            platform_id,          # platform_id
            color_id,             # color_id
            bucket_day,           # time_bucket_start
            bucket_day,           # time_bucket_end
            mention_count,        # mention_count
            None,                 # weighted_engagement
            None,                 # velocity_score
            None,                 # persistence_score
            round(float(avg_sentiment), 3) if avg_sentiment is not None else None,  # avg_sentiment
            None,                 # lead_lag_index
            None,                 # spike_flag
            None,                 # run_id
        )
        rows_to_insert.append(row)

    return rows_to_insert


def insert_platform_color_signal(conn, rows: List[Tuple]) -> None:
    """
    Insert rows into platform_color_signal.

    Uses ON CONFLICT if your table has a unique constraint on:
    (platform_id, color_id, time_bucket_start, run_id)

    If your table does not have that exact unique constraint,
    remove the ON CONFLICT clause.
    """

    sql = """
        INSERT INTO platform_color_signal (
            platform_id,
            color_id,
            time_bucket_start,
            time_bucket_end,
            mention_count,
            weighted_engagement,
            velocity_score,
            persistence_score,
            avg_sentiment,
            lead_lag_index,
            spike_flag,
            run_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=200)

    conn.commit()


def main():
    conn = get_connection()

    try:
        aggregated_rows = fetch_aggregated_signals(conn)
        print(f"Aggregated {len(aggregated_rows)} platform-color-day rows")

        insert_rows = build_rows(aggregated_rows)
        insert_platform_color_signal(conn, insert_rows)
        print(f"Inserted {len(insert_rows)} rows into platform_color_signal")

    except Exception as e:
        conn.rollback()
        print(f"Error building platform_color_signal: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
