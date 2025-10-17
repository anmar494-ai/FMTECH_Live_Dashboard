import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FMTECH — Operation Dashboard",
    page_icon="FMTECH_logo.ico",
    layout="wide"
)

# --- STYLE & HEADER ---
st.markdown(
    """
    <style>
        /* Header bar */
        #fmtech-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 85px;
            background-color: #0b5394;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 40px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 1000;
        }

        /* Logo */
        #fmtech-header img {
            height: 60px;
        }

        /* Title in center */
        #fmtech-title {
            flex-grow: 1;
            text-align: center;
            color: white;
            font-size: 26px;
            font-weight: bold;
            font-family: 'Segoe UI', sans-serif;
            letter-spacing: 1px;
        }

        /* Main content padding */
        .block-container {
            padding-top: 120px !important;
        }

        /* Text colors */
        h1, h2, h3, h4, h5, h6, p, div, span, label {
            color: #4b4b4b !important;
        }

        /* Footer */
        #fmtech-footer {
            text-align: center;
            font-size: 13px;
            color: #a0a0a0;
            margin-top: 40px;
            font-family: 'Segoe UI', sans-serif;
        }

        /* Hide OSM label */
        .leaflet-control-attribution {
            opacity: 0 !important;
            pointer-events: none !important;
        }
    </style>

    <div id="fmtech-header">
        <div><img src="https://files.fmtech.sa/logo.png" alt="FMTECH Logo"></div>
        <div id="fmtech-title">Operation Dashboard</div>
        <div style="width:60px;"></div> <!-- to balance the layout -->
    </div>
    """,
    unsafe_allow_html=True
)

# --- AUTO REFRESH ---
st_autorefresh(interval=30 * 1000, key="data_refresh")

# --- LOAD DATA ---
try:
    DATA_CSV_URL = st.secrets["DATA_CSV_URL"]
    df = pd.read_csv(DATA_CSV_URL)

    # إصلاح القيم الرقمية للفواصل العربية
    df['Latitude'] = (
        df['Latitude']
        .astype(str)
        .str.replace('٫', '.')
        .str.replace(',', '.')
        .apply(lambda x: pd.to_numeric(x, errors='coerce'))
    )
    df['Longitude'] = (
        df['Longitude']
        .astype(str)
        .str.replace('٫', '.')
        .str.replace(',', '.')
        .apply(lambda x: pd.to_numeric(x, errors='coerce'))
    )
    df = df.dropna(subset=['Latitude', 'Longitude'])

except Exception as e:
    st.error(f"⚠️ Failed to load data: {e}")
    st.stop()

# --- METRICS ---
total_records = len(df)
open_count = len(df[df['Job Status'] == 'Open'])
in_progress = len(df[df['Job Status'] == 'In Progress'])
completed = len(df[df['Job Status'] == 'Completed'])
closed = len(df[df['Job Status'] == 'Closed'])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Records", total_records)
col2.metric("Open", open_count)
col3.metric("In Progress", in_progress)
col4.metric("Completed", completed)
col5.metric("Closed", closed)

# --- MAP ---
center = [24.7136, 46.6753]
m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

# Marker colors
status_colors = {
    'Open': 'red',
    'In Progress': 'orange',
    'Completed': 'green',
    'Closed': 'blue'
}

# Add map markers
for _, row in df.iterrows():
    try:
        color = status_colors.get(row['Job Status'], 'gray')
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            popup=f"<b>{row['Job Status']}</b><br>{row['Location Description']}"
        ).add_to(m)
    except Exception:
        continue

st_folium(m, width=1400, height=600)

# --- FOOTER SIGNATURE ---
st.markdown(
    "<div id='fmtech-footer'>Developed by Eng. Anmar — FMTECH</div>",
    unsafe_allow_html=True
)
