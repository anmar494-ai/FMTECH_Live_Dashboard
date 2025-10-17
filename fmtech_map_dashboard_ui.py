import base64
from io import BytesIO
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

FMTECH_BLUE = "#0b5394"
FMTECH_GOLD = "#b59b3b"
RIYADH = (24.7136, 46.6753)

# ---------------- Page Config ----------------
st.set_page_config(
    page_title="FMTECH — Operation Dashboard",
    page_icon="FMTECH_logo.ico",
    layout="wide"
)

# ---------------- Styles & Fixed Header ----------------
st.markdown(
    f"""
    <style>
      /* Fixed header bar */
      #fmtech-header {{
        position: fixed; top: 0; left: 0; right: 0; height: 88px;
        background: {FMTECH_BLUE}; display: flex; align-items: center;
        justify-content: center; z-index: 1000; box-shadow: 0 2px 6px rgba(0,0,0,.08);
      }}
      #fmtech-inner {{
        width: 100%; max-width: 1600px; display: flex; align-items: center;
        justify-content: center; position: relative; padding: 0 20px;
      }}
      /* Left logo (original size contained in bar height) */
      #fmtech-logo {{
        position: absolute; left: 20px; top: 50%; transform: translateY(-50%);
        display: flex; align-items: center;
      }}
      #fmtech-logo img {{
        height: 72px; object-fit: contain;  /* يحافظ على الشكل بدون قص */
      }}
      /* Center title */
      #fmtech-title {{
        color: #fff; font-weight: 800; font-size: 24px; letter-spacing: .5px;
        font-family: Segoe UI, sans-serif;
      }}
      /* Right actions (fixed in header) */
      #fmtech-actions {{
        position: absolute; right: 20px; top: 50%; transform: translateY(-50%);
        display: flex; gap: 10px;
      }}
      .fm-btn {{
        background: #fff; color: {FMTECH_GOLD}; border: 1.5px solid {FMTECH_GOLD};
        border-radius: 10px; padding: 6px 12px; text-decoration: none;
        font-family: Segoe UI, sans-serif; font-weight: 600; font-size: 13px;
        box-shadow: 0 1px 2px rgba(0,0,0,.06);
      }}
      .fm-btn:hover {{
        background: {FMTECH_GOLD}; color: #fff;
      }}

      /* Push page content below fixed header */
      .block-container {{ padding-top: 120px !important; }}

      /* General text color */
      h1, h2, h3, h4, h5, h6, p, div, span, label {{ color:#4b4b4b !important; }}

      /* Footer */
      #fmtech-footer {{
        text-align:center; color:#9aa0a6; font-size:12px; margin: 24px 0 6px;
        font-family: Segoe UI, sans-serif;
      }}

      /* Hide OSM attribution completely */
      .leaflet-control-attribution {{ display: none !important; }}
    </style>

    <div id="fmtech-header">
      <div id="fmtech-inner">
        <div id="fmtech-logo">
          <img src="https://files.fmtech.sa/logo.png" alt="FMTECH Logo">
        </div>
        <div id="fmtech-title">Operation Dashboard</div>
        <div id="fmtech-actions">
          <!-- سيتم حقن روابط التحميل والريفريش هنا ديناميكياً لاحقاً -->
          <span id="dl-csv"></span>
          <span id="dl-xlsx"></span>
          <a href="#" id="refresh-btn" class="fm-btn">🔁 Refresh</a>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------- Auto Refresh (60s) ----------------
st_autorefresh(interval=60_000, key="fmtech_auto_refresh")

# ---------------- Load Data ----------------
try:
    DATA_CSV_URL = st.secrets["DATA_CSV_URL"]
    df = pd.read_csv(DATA_CSV_URL)

    # Normalize coords (Arabic decimal separator + commas)
    for c in ["Latitude", "Longitude"]:
        if c in df.columns:
            df[c] = (
                df[c].astype(str)
                     .str.replace("٫", ".", regex=False)
                     .str.replace(",", ".", regex=False)
            )
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["Latitude", "Longitude"]).copy()

    # Stringify important columns (if exist)
    for c in [
        "Job Order No.", "Job Status", "Impact", "Floor Description",
        "Trade", "Request Date", "Location Description", "CAFM LINK"
    ]:
        if c in df.columns:
            df[c] = df[c].astype(str).fillna("")

except Exception as e:
    st.error(f"⚠️ Failed to load data: {e}")
    st.stop()

# ---------------- Sidebar Filters ----------------
st.sidebar.header("Filters")

# Normalize and map Job Status (In Progress -> Attended)
if "Job Status" in df.columns:
    df["Job Status"] = df["Job Status"].str.strip().str.title().replace({"In Progress": "Attended"})

all_statuses = sorted(set(df["Job Status"])) if "Job Status" in df.columns else []
selected_statuses = st.sidebar.multiselect("Job Status", options=all_statuses, default=all_statuses)

floors = sorted([f for f in df.get("Floor Description", pd.Series(dtype=str)).dropna().unique() if str(f).strip() != ""])
selected_floors = st.sidebar.multiselect("Floor Description", options=floors, default=floors)

job_query = st.sidebar.text_input("Search Job Order No.", value="", placeholder="Type to search…").strip()

# Apply filters
df_f = df.copy()
if selected_statuses and "Job Status" in df_f.columns:
    df_f = df_f[df_f["Job Status"].isin(selected_statuses)]
if selected_floors and "Floor Description" in df_f.columns:
    df_f = df_f[df_f["Floor Description"].isin(selected_floors)]
if job_query and "Job Order No." in df_f.columns:
    df_f = df_f[df_f["Job Order No."].str.contains(job_query, case=False, na=False)]

# ---------------- KPIs ----------------
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Records", f"{len(df_f):,}")
if "Job Status" in df_f.columns:
    col2.metric("Open", f"{(df_f['Job Status']=='Open').sum():,}")
    col3.metric("Attended", f"{(df_f['Job Status']=='Attended').sum():,}")
    col4.metric("Completed", f"{(df_f['Job Status']=='Completed').sum():,}")
    col5.metric("Closed", f"{(df_f['Job Status']=='Closed').sum():,}")

# ---------------- Build smart filenames ----------------
def safe_part(val: str, all_label: str):
    if not val:
        return all_label
    # unify spaces and special chars to underscores
    s = str(val).strip() or all_label
    return s.replace("/", "-").replace("\\", "-").replace(" ", "_")

# Determine name parts
if selected_floors and len(selected_floors) == 1:
    floor_part = safe_part(selected_floors[0], "AllFloors")
else:
    floor_part = "AllFloors"

if selected_statuses and len(selected_statuses) == 1:
    status_part = safe_part(selected_statuses[0], "AllStatus")
else:
    status_part = "AllStatus"

csv_name = f"FMTECH_Operations_{floor_part}_{status_part}.csv"
xlsx_name = f"FMTECH_Operations_{floor_part}_{status_part}.xlsx"

# ---------------- Prepare downloads (CSV + Excel) ----------------
csv_bytes = df_f.to_csv(index=False).encode("utf-8-sig")

# Excel in-memory
xlsx_buffer = BytesIO()
with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
    df_f.to_excel(writer, sheet_name="Filtered", index=False)
xlsx_bytes = xlsx_buffer.getvalue()

csv_b64 = base64.b64encode(csv_bytes).decode("utf-8")
xlsx_b64 = base64.b64encode(xlsx_bytes).decode("utf-8")

# Inject header download links + JS refresh
st.markdown(
    f"""
    <script>
      // Inject CSV/XLSX links into header action placeholders
      const csvSpan = window.parent.document.querySelector('#dl-csv');
      const xlsxSpan = window.parent.document.querySelector('#dl-xlsx');
      if (csvSpan && xlsxSpan) {{
        csvSpan.innerHTML = `<a class="fm-btn" download="{csv_name}" href="data:text/csv;base64,{csv_b64}">📥 CSV</a>`;
        xlsxSpan.innerHTML = `<a class="fm-btn" download="{xlsx_name}" href="data:application/octet-stream;base64,{xlsx_b64}">📊 Excel</a>`;
      }}
      const refreshBtn = window.parent.document.querySelector('#refresh-btn');
      if (refreshBtn) {{
        refreshBtn.onclick = function(e) {{
          e.preventDefault();
          window.location.reload();
          return false;
        }};
      }}
    </script>
    """,
    unsafe_allow_html=True
)

# ---------------- Map ----------------
center_choice = st.radio(
    "Map Center",
    ["Fit to filtered data", "Center on Riyadh"],
    horizontal=True,
    index=0
)

# Base map + controls
m = folium.Map(location=RIYADH, zoom_start=12, tiles="OpenStreetMap")
Fullscreen(position="topleft").add_to(m)
cluster = MarkerCluster(name="Observations").add_to(m)

def status_color(s: str) -> str:
    s = (s or "").strip().title()
    if s == "Open": return "red"
    if s == "Attended": return "orange"
    if s == "Completed": return "green"
    if s == "Closed": return "gray"
    return "blue"

def build_popup(row) -> str:
    def tr(label, val):
        v = "" if pd.isna(val) else str(val)
        return f"<tr><td><b>{label}</b></td><td>{v}</td></tr>"
    cafm_html = ""
    link = row.get("CAFM LINK", "")
    if isinstance(link, str) and link.startswith(("http://", "https://")):
        cafm_html = f'''<tr><td><b>CAFM LINK</b></td><td><a href="{link}" target="_blank" rel="noopener">Open in CAFM</a></td></tr>'''

    rows = []
    for label in [
        "Job Order No.", "Job Status", "Impact", "Trade",
        "Request Date", "Floor Description", "Location Description"
    ]:
        if label in df_f.columns:
            rows.append(tr(label, row.get(label, "")))
    if cafm_html:
        rows.append(cafm_html)

    html = f"""
    <div style="font-family: Segoe UI, sans-serif; font-size:12px; min-width:300px;">
      <table style="border-collapse:collapse; width:100%;">{''.join(rows)}</table>
    </div>
    """
    return html

bounds = []
for _, r in df_f.iterrows():
    try:
        lat, lon = float(r["Latitude"]), float(r["Longitude"])
        bounds.append((lat, lon))
        color = status_color(r.get("Job Status", ""))

        tooltip = str(r.get("Job Order No.", "")).strip() or None
        popup_html = build_popup(r)

        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=color,
            fill=True,
            fill_opacity=0.9,
            fill_color=color,
            tooltip=tooltip,
            popup=folium.Popup(popup_html, max_width=360),
        ).add_to(cluster)
    except Exception:
        continue

if center_choice == "Fit to filtered data" and bounds:
    m.fit_bounds(bounds, padding=(20, 20))
else:
    m.location = RIYADH
    m.zoom_start = 12

st_folium(m, width="100%", height=700)

# ---------------- Footer ----------------
st.markdown("<div id='fmtech-footer'>Developed by Eng. Anmar — FMTECH</div>", unsafe_allow_html=True)
