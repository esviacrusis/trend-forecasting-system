"""
train_trend_model.py

Purpose
- Train a first real machine learning model for fashion color trend prediction
- Use engineered_features as input
- Keep existing pipeline files untouched
- Export scored results to CSV for inspection

What it does
- Loads engineered_features joined with colors
- Expands features_json into numeric columns
- Creates a temporary binary label for MVP training
- Builds a structured feature matrix
- Trains a Logistic Regression classifier
- Evaluates with classification metrics
- Scores the full dataset
- Exports predictions to CSV

Notes
- This first version uses structured features only
- It does NOT yet write to model_predictions
- It does NOT yet include TF-IDF
- The temporary label should later be replaced with a stronger label
  using Google Trends and/or editorial confirmation
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import psycopg2

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
)


DB_CONFIG = {
    "host": "tfashion-agents-db.cub6mk4och1j.us-east-1.rds.amazonaws.com",
    "dbname": "postgres",
    "user": "postgres_admin",
    "password": "passw0rd",
    "port": "5432"
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def fetch_engineered_features(conn) -> pd.DataFrame:
    """
    Load engineered features joined with color name.
    """
    sql = """
        SELECT
            ef.feature_id,
            ef.color_id,
            c.color_name,
            ef.season,
            ef.year,
            ef.cross_platform_coverage,
            ef.avg_velocity_score,
            ef.avg_persistence_score,
            ef.adoption_curve,
            ef.features_json
        FROM engineered_features ef
        JOIN colors c
            ON ef.color_id = c.color_id
        ORDER BY ef.feature_id
    """
    return pd.read_sql(sql, conn)


def safe_json_load(value: Any) -> Dict[str, Any]:
    """
    Safely parse JSON-like values into a Python dict.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def expand_feature_json(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand features_json into numeric columns used by the first ML model.
    """
    expanded = df.copy()

    expanded["parsed_features"] = expanded["features_json"].apply(safe_json_load)

    expanded["total_mentions"] = expanded["parsed_features"].apply(
        lambda x: float(x.get("total_mentions", 0) or 0)
    )
    expanded["avg_sentiment"] = expanded["parsed_features"].apply(
        lambda x: float(x.get("avg_sentiment", 0) or 0)
    )
    expanded["active_days"] = expanded["parsed_features"].apply(
        lambda x: float(x.get("active_days", 0) or 0)
    )

    numeric_cols = [
        "cross_platform_coverage",
        "avg_velocity_score",
        "avg_persistence_score",
        "total_mentions",
        "avg_sentiment",
        "active_days",
    ]

    for col in numeric_cols:
        expanded[col] = pd.to_numeric(expanded[col], errors="coerce").fillna(0)

    return expanded


def create_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a temporary binary label for MVP training.

    This is NOT the final production label.
    Later it should be replaced with Google Trends / editorial confirmation.

    Current rule:
    high_impact = 1 if at least 2 of the following are true:
      - total_mentions >= median
      - avg_persistence_score >= median
      - cross_platform_coverage >= 2
      - avg_velocity_score >= median
    else 0
    """
    labeled = df.copy()

    mention_threshold = labeled["total_mentions"].median()
    persistence_threshold = labeled["avg_persistence_score"].median()
    velocity_threshold = labeled["avg_velocity_score"].median()

    conditions_met = (
        (labeled["total_mentions"] >= mention_threshold).astype(int)
        + (labeled["avg_persistence_score"] >= persistence_threshold).astype(int)
        + (labeled["cross_platform_coverage"] >= 2).astype(int)
        + (labeled["avg_velocity_score"] >= velocity_threshold).astype(int)
    )

    labeled["label"] = (conditions_met >= 2).astype(int)

    return labeled


def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Build X and y for structured-feature Logistic Regression.
    """
    feature_names = [
        "total_mentions",
        "avg_sentiment",
        "active_days",
        "cross_platform_coverage",
        "avg_velocity_score",
        "avg_persistence_score",
    ]

    X = df[feature_names].copy()
    y = df["label"].copy()

    return X, y, feature_names


def split_data(X: pd.DataFrame, y: pd.Series):
    """
    Train/test split for MVP.
    Uses stratify when possible.
    """
    class_counts = y.value_counts()
    use_stratify = class_counts.min() >= 2 if len(class_counts) > 1 else False

    return train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y if use_stratify else None,
    )


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LogisticRegression:
    """
    Train baseline Logistic Regression classifier.
    """
    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series) -> None:
    """
    Print evaluation metrics for the holdout set.
    """
    y_pred = model.predict(X_test)

    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    else:
        y_prob = None

    print("\n=== MODEL EVALUATION ===")
    print(f"Accuracy  : {accuracy_score(y_test, y_pred):.4f}")
    print(f"Precision : {precision_score(y_test, y_pred, zero_division=0):.4f}")
    print(f"Recall    : {recall_score(y_test, y_pred, zero_division=0):.4f}")
    print(f"F1 Score  : {f1_score(y_test, y_pred, zero_division=0):.4f}")

    if y_prob is not None and len(np.unique(y_test)) > 1:
        print(f"ROC-AUC   : {roc_auc_score(y_test, y_prob):.4f}")
    else:
        print("ROC-AUC   : skipped (need both classes in test set)")

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))


def score_dataset(model, df: pd.DataFrame, X: pd.DataFrame) -> pd.DataFrame:
    """
    Score the full dataset and append probabilities/predictions.
    """
    scored = df.copy()

    if hasattr(model, "predict_proba"):
        scored["predicted_probability"] = model.predict_proba(X)[:, 1]
    else:
        scored["predicted_probability"] = 0.0

    scored["predicted_probability"] = scored["predicted_probability"].round(4)
    scored["predicted_label"] = (scored["predicted_probability"] >= 0.50).astype(int)

    return scored


def export_results(df: pd.DataFrame, path: str = "trend_model_scores.csv") -> None:
    """
    Export scored results to CSV for manual inspection.
    """
    export_cols = [
        "feature_id",
        "color_id",
        "color_name",
        "season",
        "year",
        "total_mentions",
        "avg_sentiment",
        "active_days",
        "cross_platform_coverage",
        "avg_velocity_score",
        "avg_persistence_score",
        "label",
        "predicted_probability",
        "predicted_label",
    ]

    available_cols = [col for col in export_cols if col in df.columns]
    df[available_cols].to_csv(path, index=False)
    print(f"\nExported scored results to: {path}")


def print_feature_coefficients(model, feature_names: List[str]) -> None:
    """
    Print Logistic Regression coefficients for interpretability.
    """
    if not hasattr(model, "coef_"):
        return

    coef_df = pd.DataFrame({
        "feature": feature_names,
        "coefficient": model.coef_[0],
    }).sort_values("coefficient", ascending=False)

    print("\n=== FEATURE COEFFICIENTS ===")
    print(coef_df.to_string(index=False))


def main():
    conn = get_connection()

    try:
        df = fetch_engineered_features(conn)
        print(f"Loaded {len(df)} engineered feature rows")

        if df.empty:
            raise ValueError("No rows found in engineered_features")

        df = expand_feature_json(df)
        df = create_label(df)

        label_counts = df["label"].value_counts().to_dict()
        print(f"Label distribution: {label_counts}")

        if df["label"].nunique() < 2:
            raise ValueError("Training requires at least two label classes")

        X, y, feature_names = build_feature_matrix(df)

        X_train, X_test, y_train, y_test = split_data(X, y)
        print(f"Training rows: {len(X_train)}")
        print(f"Testing rows : {len(X_test)}")

        model = train_model(X_train, y_train)
        print("Trained Logistic Regression model")

        evaluate_model(model, X_test, y_test)
        print_feature_coefficients(model, feature_names)

        scored_df = score_dataset(model, df, X)
        export_results(scored_df)

        print("\nModel training complete")

    except Exception as e:
        print(f"\nError training model: {e}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()