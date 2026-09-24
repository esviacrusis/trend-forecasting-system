import streamlit as st
from db import DataProvider
#, get_trends, get_insights

st.set_page_config(page_title="Capstone Landing Page", layout="wide")

# ---------- Simple page state for top navigation ----------
if "active_menu" not in st.session_state:
    st.session_state.active_menu = "HOME"


def set_menu(menu_name: str) -> None:
    st.session_state.active_menu = menu_name


# ---------- Basic styling ----------
st.markdown(
    """
    <style>
        .main {
            padding-top: 0.5rem;
        }

        .hero-box {
            background: linear-gradient(135deg, #0f172a, #1e293b);
            color: white;
            padding: 3rem 2.5rem;
            border-radius: 20px;
            margin-top: 1rem;
            margin-bottom: 1.5rem;
        }

        .hero-title {
            font-size: 2.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .hero-subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
            line-height: 1.6;
        }

        .section-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 1.25rem;
            border-radius: 18px;
            min-height: 180px;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
            color: #0f172a;
        }

        .section-text {
            color: #334155;
            line-height: 1.6;
        }

        .top-gap {
            height: 0.4rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Top navigation ----------
left_spacer, c1, c2, c3, c4, c5, right_spacer = st.columns([1.2, 1, 1, 1, 1, 1, 1.2])

with c1:
    if st.button("HOME", use_container_width=True):
        set_menu("HOME")
with c2:
    if st.button("BRANDS", use_container_width=True):
        set_menu("BRANDS")
with c3:
    if st.button("TRENDS", use_container_width=True):
        set_menu("TRENDS")
with c4:
    if st.button("INSIGHTS", use_container_width=True):
        set_menu("INSIGHTS")
with c5:
    if st.button("REPORTS", use_container_width=True):
        set_menu("REPORTS")

st.markdown('<div class="top-gap"></div>', unsafe_allow_html=True)

active = st.session_state.active_menu




# ---------- Shared header ----------
st.markdown(
    f"""
    <div class="hero-box">
        <div class="hero-title">{active.title()}</div>
        <div class="hero-subtitle">
            A clean Streamlit landing page with clickable top menus for your capstone project.
            You can replace this text with your project description, branding message, or dashboard intro.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------- Data provider ----------
data_provider = DataProvider()



# ---------- Page content ----------
if active == "HOME":
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Welcome</div>
                <div class="section-text">
                    Use this page as the main entry point to your capstone. Add a logo, a summary,
                    and buttons that guide users into your app.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Highlights</div>
                <div class="section-text">
                    Show featured content, key metrics, latest uploads, or recommended actions for users.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Next Steps</div>
                <div class="section-text">
                    Add quick links to reports, trend dashboards, brand profiles, or image-based analysis.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif active == "BRANDS":

    query, df = data_provider.get_brands()

    #st.code(query, language="sql")
    #st.dataframe(df)

    st.subheader("Brand Explorer")

    # brand = st.selectbox("Select a brand", ["Nike", "Apple", "Zara", "Adidas", "Custom Brand"])
    # brand

    brand = st.selectbox("Select a brand", df["brand_name"].tolist())

    st.write(f"You selected: **{brand}**")
    st.info("Use this section for brand summaries, positioning, logos, colors, and visual identity analysis.")

elif active == "TRENDS":
    st.subheader("Trend Tracker")
    trend_type = st.selectbox("Choose trend category", ["Fashion", "Technology", "Consumer Behavior", "Social Media"])
    st.write(f"Current category: **{trend_type}**")
    st.info("Use this section for trend charts, uploaded images, seasonal analysis, or competitor trend comparisons.")

elif active == "INSIGHTS":
    st.subheader("Insights Dashboard")
    st.markdown(
        """
        - Add key findings here.
        - Summarize what the data means.
        - Highlight recommendations for users or decision-makers.
        """
    )
    st.success("This section works well for conclusions, summaries, and decision support.")

elif active == "REPORTS":
    st.subheader("Reports Center")
    report_name = st.text_input("Report name", placeholder="Enter report title")
    uploaded_file = st.file_uploader("Upload report preview image or PDF", type=["png", "jpg", "jpeg", "pdf"])

    if report_name:
        st.write(f"Preparing report: **{report_name}**")

    if uploaded_file is not None:
        st.write(f"Uploaded file: **{uploaded_file.name}**")
        if uploaded_file.type.startswith("image/"):
            st.image(uploaded_file, use_container_width=True)

    st.info("Use this section for downloadable reports, image previews, exports, and summaries.")
