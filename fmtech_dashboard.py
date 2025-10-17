import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FMTECH — Operation Dashboard",
    page_icon="fmtech_logo.jpg",
    layout="wide"
)

# --- HEADER STYLE ---
st.markdown("""
<style>
#fmtech-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 85px;
    background-color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 30px;
    border-bottom: 2px solid #0b5394;
    z-index: 1000;
}
#fmtech-header img {
    height: 60px;
}
.dashboard-title {
    font-size: 28px;
    color: #c5a46d;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 600;
}
.block-container { padding-top: 110px !important; }
</style>

<div id="fmtech-header">
    <img src="fmtech_logo.jpg" alt="FMTECH Logo">
    <div class="dashboard-title">Operation Dashboard</div>
</div>
""", unsafe_allow_html=True)

# --- AUTO REFRESH ---
st_autorefresh(interval=30 * 1000, key="data_refresh")

# --- LOAD DATA ---
try:
    DATA_CSV_URL = st.secrets["DATA_CSV_URL"]
    df = pd.read_csv(DATA_CSV_URL)
except Exception as e:
    st.error(f"⚠️ Failed to load data: {e}")
    st.stop()

# --- CLEAN & FIX COORDINATES ---
for col in ['Latitude', 'Longitude']:
    df[col] = df[col].astype(str).str.replace('٫', '.').astype(float)

# --- FILTERS ---
floor_options = ['ALL'] + sorted(df['Floor Description'].dropna().unique().tolist())
status_options = ['ALL'] + sorted(df['Job Status'].dropna().unique().tolist())

col1, col2, col3 = st.columns([1, 1, 2])
selected_floor = col1.selectbox("Floor Description", options=floor_options, index=0)
selected_status = col2.selectbox("Job Status", options=status_options, index=0)
search_job = col3.text_input("Search Job Order No.")

filtered_df = df.copy()

if search_job:
    filtered_df = df[df['Job Order No.'].astype(str).str.contains(search_job, case=False, na=False)]
else:
    if selected_floor != 'ALL':
        filtered_df = filtered_df[filtered_df['Floor Description'] == selected_floor]
    if selected_status != 'ALL':
        filtered_df = filtered_df[filtered_df['Job Status'] == selected_status]

# --- SUMMARY METRICS ---
st.markdown("### Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Records", len(filtered_df))
col2.metric("Open", len(filtered_df[filtered_df['Job Status'] == 'Open']))
col3.metric("Attended", len(filtered_df[filtered_df['Job Status'] == 'Attended']))
col4.metric("Completed", len(filtered_df[filtered_df['Job Status'] == 'Completed']))
col5.metric("Closed", len(filtered_df[filtered_df['Job Status'] == 'Closed']))

# --- MAP ---
center = [24.7136, 46.6753]
m = folium.Map(location=center, zoom_start=12, tiles=None)
folium.TileLayer("CartoDB positron").add_to(m)

status_colors = {
    'Open': 'red',
    'Attended': 'orange',
    'Completed': 'green',
    'Closed': 'blue'
}

# --- ADD MARKERS ---
for _, row in filtered_df.iterrows():
    color = status_colors.get(row['Job Status'], 'gray')
    popup_html = f"""
    <b>Job Status:</b> {row['Job Status']}<br>
    <b>CAFM Link:</b> <a href='{row['CAFM LINK']}' target='_blank'>Open Link</a><br>
    <b>Floor Description:</b> {row['Floor Description']}<br>
    <b>Location:</b> {row['Location Description']}<br>
    """
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        popup=popup_html
    ).add_to(m)

st_folium(m, width=1400, height=600)

st.markdown("<p style='text-align:center; color:gray; font-size:13px;'>Developed by Eng. Anmar — FMTECH</p>", unsafe_allow_html=True)
