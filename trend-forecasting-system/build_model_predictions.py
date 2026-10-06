
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import Json, execute_batch

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import Config

# ============================================================
# Config
# ============================================================

PIPELINE_NAME = "model_predict"
MODEL_NAME = "rf_color_trend_v1"
MODEL_VERSION = "model3_rf_proxylabel_v1"


# ============================================================
# Helpers
# ============================================================

def get_connection():
    return psycopg2.connect(**Config.from_env().db_connection_params())


def start_run(cursor, pipeline_name: str, params: dict[str, Any], notes: str | None = None) -> str:
    cursor.execute(
        """
        INSERT INTO runs (pipeline_name, params_json, notes)
        VALUES (%s, %s::jsonb, %s)
        RETURNING run_id
        """,
        (pipeline_name, json.dumps(params), notes),
    )
    return str(cursor.fetchone()[0])


def end_run(cursor, run_id: str):
    cursor.execute(
        """
        UPDATE runs
        SET finished_at = now()
        WHERE run_id = %s
        """,
        (run_id,),
    )


def ensure_model_row(cursor) -> int:
    cursor.execute(
        """
        INSERT INTO models (name, task, version, source)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name, task, version)
        DO UPDATE SET source = EXCLUDED.source
        RETURNING model_id
        """,
        (MODEL_NAME, "forecasting", MODEL_VERSION, "build_model_predictions.py"),
    )
    return int(cursor.fetchone()[0])


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def extract_json_feature(features_json: Any, key: str, default: float = 0.0) -> float:
    if features_json is None:
        return default
    if isinstance(features_json, str):
        try:
            features_json = json.loads(features_json)
        except Exception:
            return default
    if not isinstance(features_json, dict):
        return default
    return safe_float(features_json.get(key), default)


# ============================================================
# Data load
# ============================================================

def load_engineered_features(conn) -> pd.DataFrame:
    # Keeps the other pipeline files untouched.
    # We read only engineered_features and derive whatever is missing here.
    query = """
    SELECT
        ef.feature_id,
        ef.color_id,
        ef.season,
        ef.year,
        ef.feature_window_start,
        ef.feature_window_end,
        ef.runway_looks_with_color,
        ef.runway_prominence_score,
        ef.editorial_mention_count,
        ef.editorial_weighted_score,
        ef.twitter_weighted_engagement,
        ef.instagram_weighted_engagement,
        ef.cross_platform_coverage,
        ef.avg_velocity_score,
        ef.avg_persistence_score,
        ef.google_trends_avg_index,
        ef.google_trends_acceleration,
        ef.time_to_peak_days,
        ef.adoption_curve,
        ef.features_json,
        c.color_name
    FROM engineered_features ef
    JOIN colors c
      ON c.color_id = ef.color_id
    ORDER BY ef.year, ef.season, ef.color_id
    """
    return pd.read_sql(query, conn)


# ============================================================
# Label logic (proxy label aligned to Model 3 + docs)
# ============================================================

def add_proxy_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Model 3 says y=1 when a color becomes a Spring trend.
    Your docs say high-impact candidates show:
      - sustained lift
      - cross-platform adoption
      - strong engagement
      - search/public-interest confirmation
    This function derives a proxy label from those signals.
    """
    out = df.copy()

    # Pull optional fields from features_json if present.
    out["search_peak"] = out["features_json"].apply(lambda x: extract_json_feature(x, "google_trends_peak_index", 0.0))
    out["editorial_confirmation"] = out["features_json"].apply(lambda x: extract_json_feature(x, "editorial_confirmation_flag", 0.0))
    out["retail_adoption"] = out["features_json"].apply(lambda x: extract_json_feature(x, "retail_adoption_flag", 0.0))
    out["social_mentions"] = out["features_json"].apply(lambda x: extract_json_feature(x, "total_mentions", 0.0))
    out["sentiment_mean"] = out["features_json"].apply(lambda x: extract_json_feature(x, "avg_sentiment", 0.0))

    # Normalize some missings to zero.
    numeric_fill = [
        "runway_looks_with_color",
        "runway_prominence_score",
        "editorial_mention_count",
        "editorial_weighted_score",
        "twitter_weighted_engagement",
        "instagram_weighted_engagement",
        "cross_platform_coverage",
        "avg_velocity_score",
        "avg_persistence_score",
        "google_trends_avg_index",
        "google_trends_acceleration",
        "time_to_peak_days",
        "search_peak",
        "editorial_confirmation",
        "retail_adoption",
        "social_mentions",
        "sentiment_mean",
    ]
    for col in numeric_fill:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    # Model 3 and the data-spec both emphasize:
    # runway signal + temporal dynamics + search validation + editorial/downstream validation.
    # We use a weighted composite score, then label top colors as high-impact.
    out["combined_social_engagement"] = (
        out["twitter_weighted_engagement"] + out["instagram_weighted_engagement"]
    )

    out["proxy_score"] = (
        0.18 * out["runway_prominence_score"].rank(pct=True) +
        0.10 * out["runway_looks_with_color"].rank(pct=True) +
        0.16 * out["cross_platform_coverage"].rank(pct=True) +
        0.16 * out["combined_social_engagement"].rank(pct=True) +
        0.12 * out["avg_velocity_score"].rank(pct=True) +
        0.12 * out["avg_persistence_score"].rank(pct=True) +
        0.08 * out["google_trends_avg_index"].rank(pct=True) +
        0.04 * out["google_trends_acceleration"].rank(pct=True) +
        0.02 * out["editorial_weighted_score"].rank(pct=True) +
        0.02 * out["search_peak"].rank(pct=True)
    )

    # Threshold:
    # label colors in the top ~30% as high impact.
    # This is a proxy target for MVP, not a true downstream sales label.

    # April 23 : commented out these and replace with a new code
    # threshold = out["proxy_score"].quantile(0.70)
    # out["is_high_impact"] = (out["proxy_score"] >= threshold).astype(int)

    #New Code : 


    # ---------------- April 23 ---------------- 
    # Extract total_mentions from features_json

    # out["total_mentions"] = out["features_json"].apply(
    #     lambda x: json.loads(x)["total_mentions"]
    # )

    # April 23 17:00 - added a safe_json_load function to handle cases where features_json might already be a dict or might be None.
    out["total_mentions"] = out["features_json"].apply(
    lambda x: x["total_mentions"] if isinstance(x, dict) else json.loads(x)["total_mentions"]
    )
    


    # Use median split (more stable for small data)
    threshold = out["total_mentions"].median()

    out["is_high_impact"] = (out["total_mentions"] >= threshold).astype(int)

    # Debug check
    print(out["is_high_impact"].value_counts())
    
    # ---------------- April 23 ---------------- 




    return out


# ============================================================
# Feature prep
# ============================================================

FEATURE_COLUMNS = [
    "runway_looks_with_color",
    "runway_prominence_score",
    "editorial_mention_count",
    "editorial_weighted_score",
    "twitter_weighted_engagement",
    "instagram_weighted_engagement",
    "cross_platform_coverage",
    "avg_velocity_score",
    "avg_persistence_score",
    "google_trends_avg_index",
    "google_trends_acceleration",
    "time_to_peak_days",
    "search_peak",
    "social_mentions",
    "sentiment_mean",
]


def derive_adoption_curve(df: pd.DataFrame) -> pd.Series:
    """
    Keep curve derivation rule-based for now.
    That matches your architecture: curve type can be derived from time-series stats
    while the main prediction is a binary classifier.
    """
    curve = []
    for _, row in df.iterrows():
        v = safe_float(row.get("avg_velocity_score"))
        p = safe_float(row.get("avg_persistence_score"))
        t = safe_float(row.get("time_to_peak_days"))

        if v >= 0.75 and t <= 7 and p < 0.45:
            curve.append("fast_spike")
        elif p >= 0.70 and t >= 10:
            curve.append("slow_burn")
        elif 0.40 <= p < 0.70 and 7 <= t <= 21:
            curve.append("steady")
        elif v >= 0.70 and p >= 0.70:
            curve.append("volatile")
        else:
            curve.append("unknown")
    return pd.Series(curve, index=df.index)


# ============================================================
# Training
# ============================================================

@dataclass
class TrainResult:
    model: Any
    pipeline: Any
    pred_proba: np.ndarray
    pred_label: np.ndarray
    feature_importance: dict[str, float]
    metrics: dict[str, float]


def train_model(df: pd.DataFrame, model_kind: str = "random_forest") -> TrainResult:
    work = df.copy()

    X = work[FEATURE_COLUMNS].copy()
    y = work["is_high_impact"].astype(int)

    # Very important:
    # if there is only one class, ML training is impossible.
    if y.nunique() < 2:
        raise ValueError(
            "Training labels contain only one class. Adjust proxy label threshold or add more feature rows."
        )

    # If you truly have multiple seasons, split by year.
    # Otherwise use full fit for MVP and report that validation is limited.
    unique_years = sorted([int(x) for x in work["year"].dropna().unique().tolist()])
    has_real_holdout = len(unique_years) >= 2

    if has_real_holdout:
        train_years = unique_years[:-1]
        test_years = [unique_years[-1]]

        train_mask = work["year"].isin(train_years)
        test_mask = work["year"].isin(test_years)

        X_train, y_train = X.loc[train_mask], y.loc[train_mask]
        X_test, y_test = X.loc[test_mask], y.loc[test_mask]
    else:
        X_train, y_train = X, y
        X_test, y_test = X, y

    if model_kind == "logistic_regression":
        pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
            ]
        )
    else:
        pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestClassifier(
                    n_estimators=300,
                    max_depth=6,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=42,
                )),
            ]
        )

    pipeline.fit(X_train, y_train)

    pred_proba_test = pipeline.predict_proba(X_test)[:, 1]
    pred_label_test = (pred_proba_test >= 0.5).astype(int)

    metrics = {
        "f1": float(f1_score(y_test, pred_label_test)),
    }
    try:
        metrics["roc_auc"] = float(roc_auc_score(y_test, pred_proba_test))
    except Exception:
        metrics["roc_auc"] = None

    # Re-score full dataset for DB output.
    pred_proba_full = pipeline.predict_proba(X)[:, 1]
    pred_label_full = (pred_proba_full >= 0.5).astype(int)

    model = pipeline.named_steps["model"]

    if model_kind == "logistic_regression":
        importance = dict(zip(FEATURE_COLUMNS, model.coef_[0].tolist()))
    else:
        importance = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))

    return TrainResult(
        model=model,
        pipeline=pipeline,
        pred_proba=pred_proba_full,
        pred_label=pred_label_full,
        feature_importance=importance,
        metrics=metrics,
    )


# ============================================================
# Save predictions
# ============================================================

def upsert_predictions(cursor, df: pd.DataFrame, model_id: int, run_id: str, model_version: str):
    rows = []
    for _, row in df.iterrows():
        rows.append(
            (
                int(row["color_id"]),
                str(row["season"]),
                int(row["year"]),
                model_id,
                model_version,
                float(row["probability_high_impact"]),
                bool(row["predicted_label"]),
                str(row["predicted_adoption_curve"]),
                Json(row["feature_importance_json"]),
                run_id,
            )
        )

    sql = """
    INSERT INTO model_predictions (
        color_id,
        season,
        year,
        model_id,
        model_version,
        probability_high_impact,
        predicted_label,
        adoption_curve,
        feature_importance_json,
        run_id
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (color_id, season, year, model_version, run_id)
    DO UPDATE SET
        model_id = EXCLUDED.model_id,
        probability_high_impact = EXCLUDED.probability_high_impact,
        predicted_label = EXCLUDED.predicted_label,
        adoption_curve = EXCLUDED.adoption_curve,
        feature_importance_json = EXCLUDED.feature_importance_json
    """

    execute_batch(cursor, sql, rows, page_size=200)


# ============================================================
# Main
# ============================================================

def main():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        params = {
            "model_reference": "Model 3",
            "baseline_model": "logistic_regression",
            "final_model": "random_forest",
            "label_type": "proxy_high_impact",
            "model_version": MODEL_VERSION,
        }
        run_id = start_run(
            cursor,
            PIPELINE_NAME,
            params,
            notes="Model 3 aligned binary classifier using proxy high-impact labels from engineered features."
        )
        model_id = ensure_model_row(cursor)
        conn.commit()

        df = load_engineered_features(conn)
        if df.empty:
            raise ValueError("No rows found in engineered_features.")

        df = add_proxy_label(df)

        # Optional baseline for reporting only
        baseline_result = train_model(df, model_kind="logistic_regression")
        final_result = train_model(df, model_kind="random_forest")

        df["probability_high_impact"] = final_result.pred_proba
        df["predicted_label"] = final_result.pred_label.astype(bool)
        df["predicted_adoption_curve"] = derive_adoption_curve(df)
        df["feature_importance_json"] = [final_result.feature_importance] * len(df)

        upsert_predictions(cursor, df, model_id, run_id, MODEL_VERSION)

        # Store run metrics in the run notes for quick inspection.
        summary = {
            "row_count": int(len(df)),
            "positive_labels": int(df["is_high_impact"].sum()),
            "baseline_metrics": baseline_result.metrics,
            "final_metrics": final_result.metrics,
        }

        cursor.execute(
            """
            UPDATE runs
            SET params_json = params_json || %s::jsonb
            WHERE run_id = %s
            """,
            (json.dumps({"training_summary": summary}), run_id),
        )

        end_run(cursor, run_id)
        conn.commit()

        print("Model prediction run completed.")
        print(f"run_id: {run_id}")
        print(json.dumps(summary, indent=2))

    except Exception as e:
        conn.rollback()
        print(f"Error in build_model_predictions.py: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
