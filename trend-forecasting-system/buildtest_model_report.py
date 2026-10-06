import os
import uuid
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree

from config import Config

# ---------------------------
# DB CONFIG
# ---------------------------
db_config = Config.from_env()
DB_URI = URL.create(
    drivername="postgresql+psycopg2",
    username=db_config.db_user,
    password=db_config.db_password,
    host=db_config.db_host,
    port=db_config.db_port,
    database=db_config.db_name,
)

engine = create_engine(DB_URI)

# ---------------------------
# SETTINGS
# ---------------------------
SOURCE_TABLE = "engineered_features"
TARGET_COL = "editorial_label"
EXCLUDE_COLS = [
    "feature_id",
    "run_id",
    "season",
    "year",
    "feature_window_start",
    "feature_window_end",
    "created_at",
]

DATASET_VERSION = "engineered_features_plus_editorial_ground_truth_v1"
FEATURE_SET_VERSION = "feature_set_v1"
RUN_NOTES = "Model report + visualization run using engineered_features joined with editorial_ground_truth"

REPORT_TABLE = "model_report_history"
CONFUSION_TABLE = "model_confusion_matrix_history"
IMPORTANCE_TABLE = "model_feature_importance_history"

PLOTS_DIR = "model_plots"
TOP_N_FEATURES = 15


# ---------------------------
# HELPERS
# ---------------------------
def ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def ensure_history_tables() -> None:
    ddl_statements = [
        f"""
        CREATE TABLE IF NOT EXISTS {REPORT_TABLE} (
            run_id TEXT NOT NULL,
            run_timestamp TIMESTAMPTZ NOT NULL,
            source_table TEXT NOT NULL,
            dataset_version TEXT,
            feature_set_version TEXT,
            target_col TEXT NOT NULL,
            row_count INTEGER,
            train_row_count INTEGER,
            test_row_count INTEGER,
            feature_count INTEGER,
            positive_class_ratio DOUBLE PRECISION,
            model_name TEXT NOT NULL,
            accuracy DOUBLE PRECISION,
            precision DOUBLE PRECISION,
            recall DOUBLE PRECISION,
            f1_score DOUBLE PRECISION,
            roc_auc DOUBLE PRECISION,
            notes TEXT
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {CONFUSION_TABLE} (
            run_id TEXT NOT NULL,
            run_timestamp TIMESTAMPTZ NOT NULL,
            model_name TEXT NOT NULL,
            actual_0_pred_0 INTEGER,
            actual_0_pred_1 INTEGER,
            actual_1_pred_0 INTEGER,
            actual_1_pred_1 INTEGER
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {IMPORTANCE_TABLE} (
            run_id TEXT NOT NULL,
            run_timestamp TIMESTAMPTZ NOT NULL,
            model_name TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            importance DOUBLE PRECISION
        );
        """,
    ]

    with engine.begin() as conn:
        for ddl in ddl_statements:
            conn.execute(text(ddl))


def load_data() -> pd.DataFrame:
    query = """
        SELECT
            ef.*,
            gt.editorial_label
        FROM engineered_features ef
        JOIN editorial_ground_truth gt
            ON ef.feature_id = gt.feature_id
    """
    return pd.read_sql(query, engine)


def prepare_data(df: pd.DataFrame):
    if TARGET_COL not in df.columns:
        raise ValueError(f"Target column '{TARGET_COL}' not found in joined dataset.")

    working = df.dropna(subset=[TARGET_COL]).copy()

    X = working.drop(columns=[c for c in EXCLUDE_COLS + [TARGET_COL] if c in working.columns])
    X = X.select_dtypes(include=["number", "bool"]).copy()
    X = X.dropna(axis=1, how="all")
    X = X.fillna(0)

    y = working[TARGET_COL].astype(int)

    if X.empty:
        raise ValueError("No numeric/boolean feature columns found after preprocessing.")

    if y.nunique() != 2:
        raise ValueError(
            f"Target column '{TARGET_COL}' must be binary for this script. "
            f"Found {y.nunique()} unique values."
        )

    return working, X, y


def build_models():
    return {
        "LogisticRegression": LogisticRegression(max_iter=1000),
        "DecisionTree": DecisionTreeClassifier(max_depth=5, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
    }


def split_data(X: pd.DataFrame, y: pd.Series):
    """
    For very small datasets, fall back to preview mode.
    Be careful interpreting metrics in this mode because train=test.
    """
    if len(y) < 10:
        print("Warning: very small dataset detected. Using all rows for training/testing preview mode.")
        return X, X, y, y

    return train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )


def sanitize_filename(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in name)


def save_confusion_matrix_plot(model_name: str, y_test, y_pred, run_dir: str) -> None:
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=[0, 1])
    disp.plot(ax=ax, colorbar=False)
    ax.set_title(f"{model_name} - Confusion Matrix")
    fig.tight_layout()

    out_path = os.path.join(run_dir, f"{sanitize_filename(model_name)}_confusion_matrix.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_roc_curve_plot(model_name: str, y_test, y_prob, roc_auc, run_dir: str) -> None:
    if y_prob is None:
        print(f"Skipping ROC plot for {model_name}: no probability scores available.")
        return

    if len(pd.Series(y_test).unique()) < 2:
        print(f"Skipping ROC plot for {model_name}: y_test has only one class.")
        return

    fpr, tpr, _ = roc_curve(y_test, y_prob)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc:.4f}" if roc_auc is not None else "ROC")
    ax.plot([0, 1], [0, 1], linestyle="--")
    ax.set_title(f"{model_name} - ROC Curve")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right")
    fig.tight_layout()

    out_path = os.path.join(run_dir, f"{sanitize_filename(model_name)}_roc_curve.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def get_feature_importance_df(model_name: str, model, feature_names) -> pd.DataFrame:
    if model_name == "LogisticRegression":
        importance_df = pd.DataFrame({
            "feature_name": feature_names,
            "importance": model.coef_[0],
        })
        importance_df["abs_importance"] = importance_df["importance"].abs()
        importance_df = importance_df.sort_values("abs_importance", ascending=False)
        return importance_df

    if hasattr(model, "feature_importances_"):
        importance_df = pd.DataFrame({
            "feature_name": feature_names,
            "importance": model.feature_importances_,
        })
        importance_df["abs_importance"] = importance_df["importance"].abs()
        importance_df = importance_df.sort_values("importance", ascending=False)
        return importance_df

    return pd.DataFrame(columns=["feature_name", "importance", "abs_importance"])


def save_feature_importance_plot(model_name: str, importance_df: pd.DataFrame, run_dir: str) -> None:
    if importance_df.empty:
        print(f"Skipping feature importance plot for {model_name}: no importance values available.")
        return

    plot_df = importance_df.head(TOP_N_FEATURES).copy()

    if model_name == "LogisticRegression":
        plot_df = plot_df.sort_values("importance", ascending=True)
        title = f"{model_name} - Top {len(plot_df)} Coefficients"
        xlabel = "Coefficient"
    else:
        plot_df = plot_df.sort_values("importance", ascending=True)
        title = f"{model_name} - Top {len(plot_df)} Feature Importances"
        xlabel = "Importance"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(plot_df["feature_name"], plot_df["importance"])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Feature")
    fig.tight_layout()

    out_path = os.path.join(run_dir, f"{sanitize_filename(model_name)}_feature_importance.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_decision_tree_structure_plot(model, feature_names, run_dir: str) -> None:
    fig, ax = plt.subplots(figsize=(24, 12))
    plot_tree(
        model,
        feature_names=list(feature_names),
        class_names=["0", "1"],
        filled=True,
        rounded=True,
        fontsize=8,
        ax=ax,
    )
    ax.set_title("DecisionTree - Tree Structure")
    fig.tight_layout()

    out_path = os.path.join(run_dir, "DecisionTree_structure.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_model_comparison_plot(report_df: pd.DataFrame, run_dir: str) -> None:
    metrics = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    plot_df = report_df[["model_name"] + metrics].copy().set_index("model_name")

    fig, ax = plt.subplots(figsize=(10, 6))
    plot_df.plot(kind="bar", ax=ax)
    ax.set_title("Model Performance Comparison")
    ax.set_ylabel("Score")
    ax.set_xlabel("Model")
    ax.legend(loc="best")
    fig.tight_layout()

    out_path = os.path.join(run_dir, "model_comparison_metrics.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------
# MAIN
# ---------------------------
def main():
    run_id = str(uuid.uuid4())
    run_timestamp = datetime.now(timezone.utc)

    ensure_output_dir(PLOTS_DIR)
    run_dir = os.path.join(PLOTS_DIR, f"run_{run_id}")
    ensure_output_dir(run_dir)

    print("Ensuring history tables exist...")
    ensure_history_tables()

    print("Loading source data from engineered_features + editorial_ground_truth...")
    df = load_data()

    print("Preparing features...")
    working, X, y = prepare_data(df)

    X_train, X_test, y_train, y_test = split_data(X, y)

    row_count = int(len(working))
    train_row_count = int(len(X_train))
    test_row_count = int(len(X_test))
    feature_count = int(X.shape[1])
    positive_class_ratio = float(y.mean())

    print(f"Rows: {row_count}, Features: {feature_count}")
    print(f"Train rows: {train_row_count}, Test rows: {test_row_count}")
    print(f"Target distribution:\n{y.value_counts(dropna=False).sort_index()}")

    report_rows = []
    confusion_rows = []
    importance_rows = []

    models = build_models()

    for model_name, model in models.items():
        print(f"\nTraining {model_name}...")

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        accuracy = accuracy_score(y_test, y_pred)

        y_prob = None
        roc_auc = None
        if hasattr(model, "predict_proba"):
            try:
                y_prob = model.predict_proba(X_test)[:, 1]
                if len(pd.Series(y_test).unique()) == 2:
                    roc_auc = roc_auc_score(y_test, y_prob)
            except Exception as e:
                print(f"Warning: could not compute probabilities/ROC-AUC for {model_name}: {e}")

        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        if cm.shape != (2, 2):
            raise ValueError(f"Expected 2x2 confusion matrix, got shape {cm.shape}.")

        print(classification_report(y_test, y_pred, zero_division=0))

        report_rows.append({
            "run_id": run_id,
            "run_timestamp": run_timestamp,
            "source_table": SOURCE_TABLE,
            "dataset_version": DATASET_VERSION,
            "feature_set_version": FEATURE_SET_VERSION,
            "target_col": TARGET_COL,
            "row_count": row_count,
            "train_row_count": train_row_count,
            "test_row_count": test_row_count,
            "feature_count": feature_count,
            "positive_class_ratio": positive_class_ratio,
            "model_name": model_name,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "roc_auc": roc_auc,
            "notes": RUN_NOTES,
        })

        confusion_rows.append({
            "run_id": run_id,
            "run_timestamp": run_timestamp,
            "model_name": model_name,
            "actual_0_pred_0": int(cm[0, 0]),
            "actual_0_pred_1": int(cm[0, 1]),
            "actual_1_pred_0": int(cm[1, 0]),
            "actual_1_pred_1": int(cm[1, 1]),
        })

        importance_df = get_feature_importance_df(model_name, model, X_train.columns)

        if not importance_df.empty:
            for _, row in importance_df.iterrows():
                importance_rows.append({
                    "run_id": run_id,
                    "run_timestamp": run_timestamp,
                    "model_name": model_name,
                    "feature_name": row["feature_name"],
                    "importance": float(row["importance"]),
                })

        # ---------------------------
        # VISUALIZATIONS
        # ---------------------------
        save_confusion_matrix_plot(model_name, y_test, y_pred, run_dir)
        save_roc_curve_plot(model_name, y_test, y_prob, roc_auc, run_dir)
        save_feature_importance_plot(model_name, importance_df, run_dir)

        if model_name == "DecisionTree":
            save_decision_tree_structure_plot(model, X_train.columns, run_dir)

    report_df = pd.DataFrame(report_rows)
    confusion_df = pd.DataFrame(confusion_rows)
    importance_df_all = pd.DataFrame(importance_rows)

    print("\nWriting history tables...")
    report_df.to_sql(REPORT_TABLE, engine, if_exists="append", index=False)
    confusion_df.to_sql(CONFUSION_TABLE, engine, if_exists="append", index=False)

    if not importance_df_all.empty:
        importance_df_all.to_sql(IMPORTANCE_TABLE, engine, if_exists="append", index=False)

    print("Saving model comparison chart...")
    save_model_comparison_plot(report_df, run_dir)

    print("\nRun completed.")
    print(f"run_id: {run_id}")
    print(f"Saved DB tables: {REPORT_TABLE}, {CONFUSION_TABLE}, {IMPORTANCE_TABLE}")
    print(f"Saved plots folder: {run_dir}")


if __name__ == "__main__":
    main()
