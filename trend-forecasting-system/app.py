import pandas as pd
import psycopg2
import streamlit as st
import plotly.express as px

from config import Config

st.set_page_config(page_title="Fashion Trend Forecasting Dashboard", layout="wide")

def get_connection():
    return psycopg2.connect(**Config.from_env().db_connection_params())


@st.cache_data
def load_top_predictions():
    conn = get_connection()
    query = """
        WITH latest_run AS (
            SELECT run_id
            FROM model_predictions
            WHERE run_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        )
        SELECT
            c.color_name,
            mp.season,
            mp.year,
            mp.probability_high_impact,
            mp.predicted_label,
            mp.adoption_curve
        FROM model_predictions mp
        JOIN latest_run lr
            ON mp.run_id = lr.run_id
        JOIN colors c
            ON mp.color_id = c.color_id
        ORDER BY mp.probability_high_impact DESC, c.color_name
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data
def load_signal_strength():
    conn = get_connection()
    query = """
        SELECT
            c.color_name,
            SUM(COALESCE(pcs.mention_count, 0)) AS total_mentions,
            AVG(pcs.avg_sentiment) AS avg_sentiment
        FROM platform_color_signal pcs
        JOIN colors c
            ON pcs.color_id = c.color_id
        GROUP BY c.color_name
        HAVING SUM(COALESCE(pcs.mention_count, 0)) > 0
        ORDER BY total_mentions DESC, c.color_name
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data
def load_signal_timeseries():
    conn = get_connection()
    query = """
        SELECT
            pcs.time_bucket_start,
            c.color_name,
            SUM(COALESCE(pcs.mention_count, 0)) AS color_strength
        FROM platform_color_signal pcs
        JOIN colors c
            ON pcs.color_id = c.color_id
        GROUP BY pcs.time_bucket_start, c.color_name
        HAVING SUM(COALESCE(pcs.mention_count, 0)) > 0
        ORDER BY pcs.time_bucket_start, c.color_name
    """
    df = pd.read_sql(query, conn)
    conn.close()
    if not df.empty:
        df["time_bucket_start"] = pd.to_datetime(df["time_bucket_start"])
    return df


@st.cache_data
def load_insights():
    conn = get_connection()
    query = """
        WITH latest_run AS (
            SELECT run_id
            FROM model_predictions
            WHERE run_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        )
        SELECT DISTINCT
            c.color_name,
            ti.insight_type,
            ti.insight_text
        FROM trend_insights ti
        JOIN model_predictions mp
            ON ti.prediction_id = mp.prediction_id
        JOIN latest_run lr
            ON mp.run_id = lr.run_id
        JOIN colors c
            ON mp.color_id = c.color_id
        ORDER BY c.color_name, ti.insight_type, ti.insight_text
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data
def load_engineered_features():
    conn = get_connection()
    query = """
        SELECT
            c.color_name,
            ef.season,
            ef.year,
            ef.cross_platform_coverage,
            ef.avg_velocity_score,
            ef.avg_persistence_score,
            ef.features_json
        FROM engineered_features ef
        JOIN colors c
            ON ef.color_id = c.color_id
        ORDER BY ef.year, ef.season, c.color_name
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


st.title("Fashion Trend Forecasting Dashboard")
st.caption("Synthetic pipeline: social -> NLP -> signals -> features -> predictions -> insights")

try:
    predictions_df = load_top_predictions()
    signals_df = load_signal_strength()
    timeseries_df = load_signal_timeseries()
    insights_df = load_insights()
    features_df = load_engineered_features()

    st.subheader("Top Predicted Colors")
    st.dataframe(predictions_df, use_container_width=True)

    st.subheader("Color Strength Over Time")

    if timeseries_df.empty:
        st.warning("No time-series signal data found in platform_color_signal.")
    else:
        available_colors = sorted(timeseries_df["color_name"].unique())
        default_colors = available_colors[:3] if len(available_colors) >= 3 else available_colors

        selected_colors = st.multiselect(
            "Select colors for the line chart",
            options=available_colors,
            default=default_colors
        )

        chart_df = timeseries_df[timeseries_df["color_name"].isin(selected_colors)]

        if not chart_df.empty:
            pivot_df = chart_df.pivot(
                index="time_bucket_start",
                columns="color_name",
                values="color_strength"
            ).fillna(0)

            plot_df = pivot_df.reset_index()

            fig = px.line(
                plot_df,
                x="time_bucket_start",
                y=plot_df.columns[1:],
                markers=True,
            )

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Color Strength",
                legend_title="Color",
                margin=dict(l=20, r=20, t=40, b=20),
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select at least one color to display the line chart.")

    st.subheader("Signal Strength by Color")
    if signals_df.empty:
        st.warning("No aggregated signal data found in platform_color_signal.")
    else:
        st.dataframe(signals_df, use_container_width=True)

    st.subheader("Trend Insights")
    if insights_df.empty:
        st.warning("No insight rows found for the latest prediction run.")
    else:
        selected_color = st.selectbox(
            "Select a color to view insights",
            options=sorted(insights_df["color_name"].unique())
        )

        selected_insights = insights_df[insights_df["color_name"] == selected_color]

        for _, row in selected_insights.iterrows():
            st.markdown(f"**{row['insight_type'].replace('_', ' ').title()}**")
            st.write(row["insight_text"])

    st.subheader("Engineered Features")
    if features_df.empty:
        st.warning("No engineered feature rows found.")
    else:
        st.dataframe(features_df, use_container_width=True)

except Exception as e:
    st.error(f"Error loading dashboard data: {e}")
