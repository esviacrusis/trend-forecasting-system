"""
build_trend_insights.py

Purpose
- Generate rule-based insight rows from engineered_features
- Link each insight to model_predictions.prediction_id
- Insert results into trend_insights

Pipeline
engineered_features -> model_predictions -> trend_insights
"""

from __future__ import annotations

import json
from typing import List, Tuple, Any, Dict

import psycopg2
from psycopg2.extras import execute_batch

from config import Config


def get_connection():
    return psycopg2.connect(**Config.from_env().db_connection_params())


def fetch_feature_rows(conn) -> List[Tuple]:
    """
    Pull engineered feature rows joined to model_predictions and colors.
    """
    sql = """
        SELECT
            mp.prediction_id,
            ef.color_id,
            c.color_name,
            ef.cross_platform_coverage,
            ef.avg_velocity_score,
            ef.avg_persistence_score,
            ef.adoption_curve,
            ef.features_json
        FROM engineered_features ef
        JOIN colors c
            ON ef.color_id = c.color_id
        JOIN model_predictions mp
            ON mp.color_id = ef.color_id
           AND mp.season = COALESCE(ef.season, 'SS 2025')
           AND mp.year = COALESCE(ef.year, 2025)
        ORDER BY mp.prediction_id
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def safe_json_load(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return json.loads(value)


def build_insights_for_row(
    prediction_id,
    color_id,
    color_name,
    cross_platform_coverage,
    avg_velocity_score,
    avg_persistence_score,
    adoption_curve,
    features_json,
):
    """
    Build multiple insight rows for one engineered_features/model_predictions record.
    """
    features = safe_json_load(features_json)

    total_mentions = features.get("total_mentions", 0)
    avg_sentiment = features.get("avg_sentiment", 0)
    active_days = features.get("active_days", 0)
    first_seen = features.get("first_seen")
    last_seen = features.get("last_seen")

    insights = []

    # 1. Momentum insight
    if total_mentions >= 120:
        momentum_text = (
            f"{color_name.title()} shows strong momentum with high mention volume "
            f"({total_mentions} mentions) across the observed period."
        )
    elif total_mentions >= 60:
        momentum_text = (
            f"{color_name.title()} shows moderate momentum with {total_mentions} mentions "
            f"and consistent social visibility."
        )
    else:
        momentum_text = (
            f"{color_name.title()} currently shows lower momentum with {total_mentions} mentions, "
            f"suggesting an emerging or niche signal."
        )

    insights.append((
        prediction_id,
        "momentum",
        momentum_text,
        json.dumps({
            "color_id": color_id,
            "color_name": color_name,
            "total_mentions": total_mentions,
            "active_days": active_days,
            "first_seen": first_seen,
            "last_seen": last_seen,
        }),
    ))

    # 2. Platform driver insight
    if cross_platform_coverage is None:
        platform_text = (
            f"{color_name.title()} does not yet have enough platform coverage data for comparison."
        )
    elif cross_platform_coverage >= 2:
        platform_text = (
            f"{color_name.title()} appears across multiple platforms, indicating broader cross-platform traction."
        )
    else:
        platform_text = (
            f"{color_name.title()} is concentrated on a single platform, suggesting a narrower signal."
        )

    insights.append((
        prediction_id,
        "platform_driver",
        platform_text,
        json.dumps({
            "color_id": color_id,
            "color_name": color_name,
            "cross_platform_coverage": cross_platform_coverage,
        }),
    ))

    # 3. Diffusion insight
    if active_days >= 20:
        diffusion_label = "slow_burn"
        diffusion_text = (
            f"{color_name.title()} shows a slow-burn diffusion pattern with activity across {active_days} days."
        )
    elif active_days >= 10:
        diffusion_label = "steady"
        diffusion_text = (
            f"{color_name.title()} shows a steady diffusion pattern with recurring activity across {active_days} days."
        )
    else:
        diffusion_label = "fast_spike"
        diffusion_text = (
            f"{color_name.title()} behaves more like a fast spike, with activity concentrated across {active_days} days."
        )

    insights.append((
        prediction_id,
        "diffusion",
        diffusion_text,
        json.dumps({
            "color_id": color_id,
            "color_name": color_name,
            "active_days": active_days,
            "derived_diffusion_type": diffusion_label,
            "stored_adoption_curve": adoption_curve,
        }),
    ))

    # 4. Recommendation insight
    if total_mentions >= 100 and (avg_sentiment is not None and avg_sentiment > 0):
        rec_text = (
            f"{color_name.title()} is a strong candidate for monitoring or prioritization due to high visibility and positive sentiment."
        )
    elif total_mentions >= 50:
        rec_text = (
            f"{color_name.title()} is worth tracking further as a developing trend candidate."
        )
    else:
        rec_text = (
            f"{color_name.title()} should remain under observation until stronger signal strength appears."
        )

    insights.append((
        prediction_id,
        "recommendation",
        rec_text,
        json.dumps({
            "color_id": color_id,
            "color_name": color_name,
            "total_mentions": total_mentions,
            "avg_sentiment": avg_sentiment,
        }),
    ))

    return insights


def build_all_insights(rows: List[Tuple]) -> List[Tuple]:
    output_rows = []

    for row in rows:
        output_rows.extend(build_insights_for_row(*row))

    return output_rows


def insert_trend_insights(conn, rows: List[Tuple]) -> None:
    sql = """
        INSERT INTO trend_insights (
            prediction_id,
            insight_type,
            insight_text,
            insight_json
        )
        VALUES (%s, %s, %s, %s)
    """

    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=100)

    conn.commit()


def main():
    conn = get_connection()

    try:
        feature_rows = fetch_feature_rows(conn)
        print(f"Loaded {len(feature_rows)} joined prediction-feature rows")

        insight_rows = build_all_insights(feature_rows)
        print(f"Built {len(insight_rows)} insight rows")

        insert_trend_insights(conn, insight_rows)
        print(f"Inserted {len(insight_rows)} rows into trend_insights")

    except Exception as e:
        conn.rollback()
        print(f"Error building trend_insights: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
