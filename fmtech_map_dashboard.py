import os, time
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, HeatMap, Fullscreen
from streamlit_autorefresh import st_autorefresh  # auto-refresh every 30s

FMTECH_BLUE = "#0b5394"
RIYADH = (24.7136, 46.6753)

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="FMTECH — Live Dashboard", layout="wide")

# ---------- STYLES: fixed header + white bg ----------
st.markdown(f"""
<style>
/* Fixed FMTECH blue header bar */
#fmtech-header {{
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 56px;
  background: {FMTECH_BLUE};
  color: #fff;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px;
  z-index: 1000;
  font-family: Segoe UI, sans-serif;
}}
#fmtech-title {{
  font-weight: 700; letter-spacing: 0.2px;
}}
#fmtech-status {{
  display: inline-flex; align-items: center; gap: 8px; font-size: 13px;
}}
.fmtech-dot {{
  width: 10px; height: 10px; border-radius: 50%;
  display: inline-block; vertical-align: middle;
}}
/* push content below fixed header */
.block-container {{
  padding-top: 72px !important;
}}
/* keep background white */
html, body, [data-testid="stAppViewContainer"] {{
  background: #fff !important;
}}
</style>
""", unsafe_allow_html=True)

# ---------- DATA SOURCE ----------
# Preferred (Cloud): secrets; Fallback: env; Final fallback: hard-coded (your live sheet)
DATA_CSV_URL = st.secrets.get(
    "DATA_CSV_URL",
    os.getenv(
        "DATA_CSV_URL",
        "https://docs.google.com/spreadsheets/d/1P7zg-1RSwOhADBCytCj3d2N16ZkGqTam/export?format=csv"
    )
)

# ---------- HELPERS ----------
def status_color(status: str) -> str:
    """Color-code by Job Status."""
    if not status: return FMTECH_BLUE
    s = str(status).strip().lower()
    if "open" in s:        return "red"
    if "progress" in s:    return "orange"
    if "hold" in s:        return "yellow"
    if "completed" in s:   return "green"
    if "closed" in s:      return "gray"
    return FMTECH_BLUE

@st.cache_data(ttl=25)
def fetch_data(csv_url: str) -> pd.DataFrame:
    """Fetch CSV → DataFrame. (Cached 25s; autorefresh drives re-renders every 30s)"""
    df = pd.read_csv(csv_url)
    # Normalize core columns if present
    # Required for plotting: Latitude & Longitude
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        raise ValueError("Missing required columns: Latitude and/or Longitude")

    # Coerce numeric coords
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude"]).copy()

    # Stringify some useful columns if present
    for c in ["Job Order No.", "Job Status", "Impact", "Problem Description",
              "Location Description", "Floor Description"]:
        if c in df.columns:
            df[c] = df[c].astype(str)

    return df

def build_map(df: pd.DataFrame, add_heat: bool, basemap: str) -> folium.Map:
    tiles = {
        "OpenStreetMap": "OpenStreetMap",
        "CartoDB Positron": "CartoDB positron",
        "Stamen Terrain": "Stamen Terrain",
        "Stamen Toner": "Stamen Toner",
    }
    # Always center on Riyadh as requested
    m = folium.Map(location=RIYADH, zoom_start=12, tiles=tiles.get(basemap, "OpenStreetMap"))
    Fullscreen(position='topleft').add_to(m)
    cluster = MarkerCluster(name="Observations").add_to(m)

    heat = []
    for _, r in df.iterrows():
        lat, lon = float(r["Latitude"]), float(r["Longitude"])
        heat.append([lat, lon])

        # Tooltip = Job Order No. (if available)
        tooltip = str(r.get("Job Order No.", "")).strip() or None

        # Popup: include all columns neatly
        lines = []
        for col in df.columns:
            val = r.get(col, "")
            if pd.isna(val): val = ""
            lines.append(f"<b>{col}:</b> {val}")
        popup_html = "<div style='font-family:Segoe UI; font-size:12px; min-width:280px;'>" + "<br/>".join(lines) + "</div>"

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=status_color(r.get("Job Status", "")),
            fill=True,
            fill_opacity=0.9,
            tooltip=tooltip,
            popup=folium.Popup(popup_html, max_width=360),
        ).add_to(cluster)

    if add_heat and heat:
        HeatMap(heat, name="Heatmap", radius=14, blur=18, min_opacity=0.25).add_to(m)

    # Legend for Job Status
    legend = """
    <div style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;
      background: white; padding: 10px 12px; border: 1px solid #999; border-radius: 8px;
      font-family: Segoe UI; font-size: 12px;">
      <b>Status Legend</b><br>
      <span style="color:red;">●</span> Open &nbsp;
      <span style="color:orange;">●</span> In Progress &nbsp;
      <span style="color:gold;">●</span> On Hold &nbsp;
      <span style="color:green;">●</span> Completed &nbsp;
      <span style="color:gray;">●</span> Closed
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend))
    return m

# ---------- AUTO-REFRESH (every 30s) ----------
st_autorefresh(interval=30_000, key="fmtech_auto_refresh")

# ---------- HEADER (fixed) ----------
# We will set the live-status dot color after we attempt data load.
st.markdown("""
<div id="fmtech-header">
  <div id="fmtech-title">FMTECH — Live Dashboard</div>
  <div id="fmtech-status">
    <span id="fmtech-dot" class="fmtech-dot" style="background:#bbb;"></span>
    <span id="fmtech-status-text">Checking data…</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------- SIDEBAR OPTIONS ----------
st.sidebar.title("Map Options")
basemap = st.sidebar.selectbox("Base map", ["OpenStreetMap","CartoDB Positron","Stamen Terrain","Stamen Toner"], index=0)
heat = st.sidebar.checkbox("Show Heatmap", value=False)

# ---------- MAIN / LOAD DATA ----------
status_ok = True
error_msg = ""
try:
    df = fetch_data(DATA_CSV_URL)
except Exception as e:
    status_ok = False
    error_msg = str(e)
    df = pd.DataFrame()

# Push header status dot color via a tiny script block
dot_color = "#28a745" if status_ok else "#e03c31"  # green / red
status_text = "Online (auto-refresh 30s)" if status_ok else "Offline — check data source"
st.markdown(f"""
<script>
var dot = window.parent.document.getElementById("fmtech-dot");
var txt = window.parent.document.getElementById("fmtech-status-text");
if (dot) dot.style.background = "{dot_color}";
if (txt) txt.textContent = "{status_text}";
</script>
""", unsafe_allow_html=True)

# ---------- RENDER ----------
if not status_ok:
    st.error(f"Data load failed: {error_msg}")
    st.stop()

# Optional quick stats (top row)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Records", f"{len(df):,}")
with col2:
    if "Job Status" in df.columns:
        st.metric("Open", f"{(df['Job Status'].str.lower().str.contains('open')).sum():,}")
with col3:
    if "Job Status" in df.columns:
        st.metric("In Progress", f"{(df['Job Status'].str.lower().str.contains('progress')).sum():,}")
with col4:
    if "Job Status" in df.columns:
        st.metric("Completed", f"{(df['Job Status'].str.lower().str.contains('completed')).sum():,}")

# Build & show map
map_obj = build_map(df, add_heat=heat, basemap=basemap)
st_folium(map_obj, width="100%", height=680)

# Footer
st.markdown(
    "<div style='text-align:center; color:#777; font-family:Segoe UI; font-size:12px; padding:8px 0;'>"
    "Developed by Eng. ANMAR — FMTECH © 2025</div>",
    unsafe_allow_html=True
)
