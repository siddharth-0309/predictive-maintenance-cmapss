import streamlit as st
import pandas as pd
import joblib
import plotly.graph_objects as go
from datetime import datetime
import os

# Resolve paths relative to this script's own folder, NOT the process's
# working directory. Streamlit Cloud runs apps with the repo root as the
# working directory even when app.py lives in a subfolder, so plain
# relative paths like "model/rul_model.pkl" break there. This fixes it.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------
# REALISTIC ANALOG GAUGE — hand-drawn SVG, not a flat chart-library gauge.
# Mimics a physical mission-control instrument: metal bezel, glass
# highlight, tick marks with numbers, a glowing needle with a pivot cap.
# ------------------------------------------------------------------
import math


def build_gauge_svg(value, vmin, vmax, label, unit, accent):
    frac = max(0.0, min(1.0, (value - vmin) / (vmax - vmin))) if vmax > vmin else 0.5
    sweep = 250
    start_angle = -125
    needle_angle = start_angle + frac * sweep
    cx = cy = 100
    r_outer, r_face = 96, 84
    r_tick_out, r_tick_in, r_tick_in_minor, r_label = 78, 68, 72, 58

    def pt(angle_deg, radius):
        rad = math.radians(angle_deg)
        return cx + radius * math.sin(rad), cy - radius * math.cos(rad)

    n_major = 6
    ticks, labels = [], []
    for i in range(n_major + 1):
        a = start_angle + (sweep * i / n_major)
        x1, y1 = pt(a, r_tick_in)
        x2, y2 = pt(a, r_tick_out)
        ticks.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#7a5230" stroke-width="2.4" stroke-linecap="round"/>')
        val = vmin + (vmax - vmin) * i / n_major
        vtxt = f"{val:.0f}" if (vmax - vmin) >= 10 else f"{val:.1f}"
        lx, ly = pt(a, r_label)
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9" fill="#c98a4b" text-anchor="middle" dominant-baseline="middle" font-family="Roboto Mono, monospace">{vtxt}</text>')

    n_minor = n_major * 4
    minors = []
    for i in range(n_minor + 1):
        if i % 4 == 0:
            continue
        a = start_angle + (sweep * i / n_minor)
        x1, y1 = pt(a, r_tick_in_minor)
        x2, y2 = pt(a, r_tick_out)
        minors.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#5c3f24" stroke-width="1" stroke-linecap="round"/>')

    arc_x1, arc_y1 = pt(start_angle, r_tick_out + 6)
    arc_x2, arc_y2 = pt(needle_angle, r_tick_out + 6)
    large_arc = 1 if (needle_angle - start_angle) > 180 else 0
    progress_arc = (f'<path d="M {arc_x1:.1f} {arc_y1:.1f} A {r_tick_out+6} {r_tick_out+6} 0 {large_arc} 1 '
                    f'{arc_x2:.1f} {arc_y2:.1f}" fill="none" stroke="{accent}" stroke-width="3.5" '
                    f'stroke-linecap="round" opacity="0.9"/>')

    tip_x, tip_y = pt(needle_angle, 62)
    left_x, left_y = pt(needle_angle - 90, 4)
    right_x, right_y = pt(needle_angle + 90, 4)
    back_x, back_y = pt(needle_angle + 180, 14)
    vtxt_display = f"{value:.1f}" if (vmax - vmin) < 10 else f"{value:.0f}"
    uid = label.replace(" ", "").replace(".", "")

    return f'''
<svg viewBox="0 0 200 210" xmlns="http://www.w3.org/2000/svg" width="100%">
  <defs>
    <radialGradient id="bezel-{uid}" cx="35%" cy="30%" r="75%">
      <stop offset="0%" stop-color="#2a2a2a"/><stop offset="55%" stop-color="#141414"/><stop offset="100%" stop-color="#000000"/>
    </radialGradient>
    <radialGradient id="face-{uid}" cx="40%" cy="35%" r="70%">
      <stop offset="0%" stop-color="#141414"/><stop offset="70%" stop-color="#0a0a0a"/><stop offset="100%" stop-color="#000000"/>
    </radialGradient>
    <linearGradient id="glass-{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.08"/><stop offset="35%" stop-color="#ffffff" stop-opacity="0.02"/><stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glow-{uid}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.9"/><stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="url(#bezel-{uid})" stroke="#3a3a3a" stroke-width="1.5"/>
  <circle cx="{cx}" cy="{cy}" r="{r_face}" fill="url(#face-{uid})" stroke="rgba(252,61,33,0.3)" stroke-width="1"/>
  {"".join(minors)}
  {"".join(ticks)}
  {progress_arc}
  {"".join(labels)}
  <circle cx="{cx}" cy="{cy}" r="30" fill="url(#glow-{uid})" opacity="0.3"/>
  <polygon points="{tip_x:.1f},{tip_y:.1f} {left_x:.1f},{left_y:.1f} {back_x:.1f},{back_y:.1f} {right_x:.1f},{right_y:.1f}" fill="{accent}" stroke="#ffffff" stroke-width="0.4" opacity="0.95"/>
  <circle cx="{cx}" cy="{cy}" r="7" fill="#0a0a0a" stroke="{accent}" stroke-width="2"/>
  <circle cx="{cx}" cy="{cy}" r="2.4" fill="{accent}"/>
  <circle cx="{cx}" cy="{cy}" r="{r_face}" fill="url(#glass-{uid})"/>
  <text x="100" y="150" font-size="20" fill="#ffb347" text-anchor="middle" font-family="Roboto Mono, monospace" font-weight="bold">{vtxt_display}</text>
  <text x="100" y="164" font-size="9" fill="#c98a4b" text-anchor="middle" font-family="Roboto Mono, monospace" letter-spacing="1">{unit}</text>
  <text x="100" y="196" font-size="10" fill="#e0a768" text-anchor="middle" font-family="Roboto Mono, monospace" letter-spacing="0.5">{label}</text>
</svg>
'''

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Turbofan RUL Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------
# LOAD ARTIFACTS (cached so it only happens once)
# ------------------------------------------------------------------
@st.cache_resource
def load_artifacts():
    model = joblib.load(os.path.join(BASE_DIR, "model", "rul_model.pkl"))
    feature_columns = joblib.load(os.path.join(BASE_DIR, "model", "feature_columns.pkl"))
    return model, feature_columns

@st.cache_data
def load_data():
    return pd.read_csv(os.path.join(BASE_DIR, "data", "test_last.csv"))

model, feature_columns = load_artifacts()
test_data = load_data()
engine_ids = sorted(test_data["unit_nr"].unique().tolist())

# ------------------------------------------------------------------
# THEME — NASA Mission Control: matte black consoles, amber/orange
# telemetry text, a faint scanline/grid overlay like an old CRT console.
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Roboto+Mono:wght@400;500;700&display=swap');

:root {
    --void: #000000;
    --panel-bg: #0d0d0d;
    --console: #141414;
    --amber: #FFA500;
    --amber-bright: #FFC04D;
    --nasa-orange: #FC3D21;
    --nasa-blue: #0B3D91;
    --green: #4ADE80;
    --warn: #FFB020;
    --red: #FC3D21;
    --text: #F5E6D3;
}

.stApp {
    background:
        radial-gradient(circle at 20% 0%, rgba(252,61,33,0.06), transparent 45%),
        radial-gradient(circle at 80% 100%, rgba(11,61,145,0.10), transparent 45%),
        linear-gradient(180deg, #000000 0%, #0a0a0a 50%, #000000 100%);
    background-attachment: fixed;
}

/* faint scanline / console grid overlay */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(255,165,0,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,165,0,0.035) 1px, transparent 1px);
    background-size: 38px 38px;
    pointer-events: none;
    z-index: 0;
}

html, body, [class*="css"] {
    color: var(--text) !important;
    font-family: 'Roboto Mono', monospace;
}

h1, h2, h3, .hero-title {
    font-family: 'Orbitron', sans-serif !important;
    letter-spacing: 1px;
}

#MainMenu, footer, header {visibility: hidden;}

/* ---- Hero header ---- */
.hero {
    text-align: center;
    padding: 18px 10px 26px 10px;
    border-bottom: 2px solid rgba(255,165,0,0.35);
    margin-bottom: 26px;
}
.hero-title {
    font-size: 34px;
    font-weight: 900;
    background: linear-gradient(90deg, var(--nasa-orange), var(--amber-bright), var(--nasa-orange));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(255,165,0,0.3);
    margin-bottom: 4px;
}
.hero-sub {
    color: #c98a4b;
    font-size: 13px;
    letter-spacing: 3px;
    text-transform: uppercase;
}

/* ---- console panels ---- */
.panel {
    background: linear-gradient(160deg, rgba(20,20,20,0.9), rgba(0,0,0,0.85));
    border: 1px solid rgba(255,165,0,0.3);
    border-radius: 10px;
    padding: 20px 22px;
    box-shadow: 0 0 25px rgba(0,0,0,0.7), inset 0 0 30px rgba(255,165,0,0.02);
    margin-bottom: 18px;
}

.panel-label {
    font-size: 11px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--amber);
    opacity: 0.85;
    margin-bottom: 6px;
}

.metric-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 30px;
    font-weight: 700;
    color: var(--text);
}

.metric-unit {
    font-size: 12px;
    color: #c98a4b;
    margin-left: 4px;
}

/* ---- status badge ---- */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    border-radius: 4px;
    font-family: 'Orbitron', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    border: 1px solid;
}
.dot {
    width: 9px; height: 9px; border-radius: 50%;
    box-shadow: 0 0 10px currentColor;
    animation: pulse 1.4s infinite;
}
@keyframes pulse {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.45; transform: scale(1.35); }
    100% { opacity: 1; transform: scale(1); }
}
.healthy { color: var(--green); border-color: var(--green); background: rgba(74,222,128,0.08); }
.warning { color: var(--warn); border-color: var(--warn); background: rgba(255,176,32,0.08); }
.critical { color: var(--red); border-color: var(--red); background: rgba(252,61,33,0.1); }

/* selectbox tweak */
div[data-baseweb="select"] > div {
    background-color: rgba(0,0,0,0.8) !important;
    border-color: rgba(255,165,0,0.4) !important;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #050505, #000000);
    border-right: 1px solid rgba(255,165,0,0.2);
}

.footer-note {
    text-align: center;
    color: #6b4a2a;
    font-size: 11px;
    letter-spacing: 1.5px;
    margin-top: 30px;
    padding-top: 14px;
    border-top: 1px solid rgba(255,165,0,0.15);
}

.blink-live {
    color: var(--nasa-orange);
    font-size: 11px;
    letter-spacing: 2px;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# HERO
# ------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="hero-title">🛰️ TURBOFAN ENGINE — MISSION CONTROL</div>
    <div class="hero-sub">NASA C-MAPSS Predictive Maintenance · Remaining Useful Life Telemetry</div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# SIDEBAR — engine selector
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔧 FLEET SELECTOR")
    st.caption(f"{len(engine_ids)} engines online in fleet")
    selected_engine = st.selectbox(
        "Select engine unit",
        options=engine_ids,
        format_func=lambda x: f"Engine #{x:03d}",
        index=0
    )
    st.markdown("---")
    st.markdown(
        f"<span class='blink-live'>● LIVE FEED</span><br>"
        f"<span style='color:#6b4a2a;font-size:12px'>Snapshot: {datetime.now().strftime('%d %b %Y — %H:%M')}</span>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.caption("Model: LightGBM Regressor")
    st.caption(f"Features tracked: {len(feature_columns)}")

# ------------------------------------------------------------------
# PREDICTION LOGIC — last recorded cycle for this engine (matches the
# official CMAPSS test-set setup: a truncated mid-life snapshot)
# ------------------------------------------------------------------
engine_data = test_data[test_data["unit_nr"] == selected_engine].sort_values("time_cycles")
last_row = engine_data.iloc[[-1]]
X = last_row[feature_columns]
predicted_rul = float(model.predict(X)[0])
current_cycle = int(last_row["time_cycles"].values[0])

if predicted_rul < 30:
    status, status_class, status_msg, accent = "CRITICAL", "critical", "Maintenance jald zaroori hai", "#FC3D21"
elif predicted_rul < 80:
    status, status_class, status_msg, accent = "WARNING", "warning", "Monitor karo — degradation detected", "#FFB020"
else:
    status, status_class, status_msg, accent = "HEALTHY", "healthy", "Engine operating within normal range", "#4ADE80"

# ------------------------------------------------------------------
# TOP METRIC ROW
# ------------------------------------------------------------------
col1, col2, col3 = st.columns([1, 1, 1.2])

with col1:
    st.markdown(f"""
    <div class="panel">
        <div class="panel-label">Engine Unit</div>
        <div class="metric-value">#{selected_engine:03d}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="panel">
        <div class="panel-label">Current Cycle</div>
        <div class="metric-value">{current_cycle}<span class="metric-unit">cycles</span></div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="panel">
        <div class="panel-label">System Status</div>
        <div class="status-pill {status_class}">
            <span class="dot"></span>{status}
        </div>
        <div style="color:#c98a4b;font-size:12px;margin-top:8px;">{status_msg}</div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# GAUGE + SENSOR TRENDS
# ------------------------------------------------------------------
gcol, tcol = st.columns([1, 1.6])

with gcol:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">Predicted Remaining Useful Life</div>', unsafe_allow_html=True)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(predicted_rul, 1),
        number={"suffix": " cycles", "font": {"size": 34, "color": "#F5E6D3", "family": "Orbitron"}},
        gauge={
            "axis": {"range": [0, 150], "tickcolor": "#c98a4b", "tickfont": {"color": "#c98a4b"}},
            "bar": {"color": accent, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(252,61,33,0.18)"},
                {"range": [30, 80], "color": "rgba(255,176,32,0.15)"},
                {"range": [80, 150], "color": "rgba(74,222,128,0.15)"},
            ],
            "threshold": {
                "line": {"color": "#FFA500", "width": 3},
                "thickness": 0.85,
                "value": round(predicted_rul, 1)
            }
        }
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#F5E6D3"},
        height=280,
        margin=dict(l=20, r=20, t=30, b=10)
    )
    st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with tcol:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">Sensor Telemetry Over Time</div>', unsafe_allow_html=True)

    fig_trend = go.Figure()
    sensor_colors = {
        "T24": "#FFA500",
        "T50": "#FC3D21",
        "Ps30": "#4ADE80",
        "Nc": "#5B8FE8",
    }
    # Each sensor lives on a very different scale (Nc ~9000, T50 ~1400,
    # T24 ~640, Ps30 ~47). Plotting raw values on one shared axis makes the
    # smaller-range sensors look like flat lines. So we normalize each
    # sensor to its own 0-100% range for the visual trend, while showing
    # the true raw value in the hover tooltip via customdata.
    for sensor, color in sensor_colors.items():
        raw = engine_data[sensor]
        s_min, s_max = raw.min(), raw.max()
        span = (s_max - s_min) or 1  # avoid divide-by-zero if flat
        normalized = (raw - s_min) / span * 100

        fig_trend.add_trace(go.Scatter(
            x=engine_data["time_cycles"],
            y=normalized,
            mode="lines",
            name=sensor,
            line=dict(color=color, width=2),
            customdata=raw,
            hovertemplate=f"{sensor}: %{{customdata:.2f}}<br>Cycle: %{{x}}<extra></extra>"
        ))

    fig_trend.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#c98a4b"},
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=1.18, font=dict(color="#F5E6D3")),
        xaxis=dict(title="Cycle", gridcolor="rgba(255,165,0,0.08)", zerolinecolor="rgba(255,165,0,0.1)"),
        yaxis=dict(
            title="Relative trend (%)",
            range=[-5, 105],
            gridcolor="rgba(255,165,0,0.08)",
            zerolinecolor="rgba(255,165,0,0.1)"
        ),
        hovermode="x unified"
    )
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# LIVE INSTRUMENT CLUSTER — analog cockpit-style dials per sensor
# ------------------------------------------------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<div class="panel-label">Live Instrument Cluster — Latest Reading</div>', unsafe_allow_html=True)

# Realistic operating bands pulled from the dataset itself, with a little
# headroom on each side so the needle never pins at the edge.
instrument_specs = {
    "T24": {"label": "T24 · Fan Inlet Temp", "unit": "°R", "range": [636, 649], "color": "#FFA500"},
    "T50": {"label": "T50 · LPT Outlet Temp", "unit": "°R", "range": [1378, 1440], "color": "#FC3D21"},
    "Ps30": {"label": "Ps30 · HPC Static Pressure", "unit": "psia", "range": [46.0, 49.0], "color": "#4ADE80"},
    "Nc": {"label": "Nc · Core Speed", "unit": "rpm", "range": [9000, 9180], "color": "#5B8FE8"},
}

dial_cols = st.columns(4)
for col, (sensor, spec) in zip(dial_cols, instrument_specs.items()):
    reading = float(last_row[sensor].values[0])
    lo, hi = spec["range"]
    with col:
        svg = build_gauge_svg(reading, lo, hi, spec["label"], spec["unit"], spec["color"])
        st.markdown(svg, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# RAW SENSOR SNAPSHOT (expandable)
# ------------------------------------------------------------------
with st.expander("📟 View raw sensor snapshot (latest cycle)"):
    display_cols = ["time_cycles", "T24", "T30", "T50", "P30", "Nf", "Nc", "Ps30", "Phi", "BPR"]
    display_cols = [c for c in display_cols if c in last_row.columns]
    st.dataframe(last_row[display_cols].reset_index(drop=True), use_container_width=True)

st.markdown("""
<div class="footer-note">
    🛰️ TURBOFAN RUL MISSION CONTROL &nbsp;·&nbsp; LightGBM inference engine &nbsp;·&nbsp; NASA C-MAPSS dataset
</div>
""", unsafe_allow_html=True)
