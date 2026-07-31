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
# Mimics a physical cockpit instrument: metal bezel, glass highlight,
# tick marks with numbers, a glowing needle with a pivot cap.
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
        ticks.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#cfe8f5" stroke-width="2.4" stroke-linecap="round"/>')
        val = vmin + (vmax - vmin) * i / n_major
        vtxt = f"{val:.0f}" if (vmax - vmin) >= 10 else f"{val:.1f}"
        lx, ly = pt(a, r_label)
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9" fill="#7ea6c4" text-anchor="middle" dominant-baseline="middle" font-family="Share Tech Mono, monospace">{vtxt}</text>')

    n_minor = n_major * 4
    minors = []
    for i in range(n_minor + 1):
        if i % 4 == 0:
            continue
        a = start_angle + (sweep * i / n_minor)
        x1, y1 = pt(a, r_tick_in_minor)
        x2, y2 = pt(a, r_tick_out)
        minors.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#5a89a8" stroke-width="1" stroke-linecap="round"/>')

    arc_x1, arc_y1 = pt(start_angle, r_tick_out + 6)
    arc_x2, arc_y2 = pt(needle_angle, r_tick_out + 6)
    large_arc = 1 if (needle_angle - start_angle) > 180 else 0
    progress_arc = (f'<path d="M {arc_x1:.1f} {arc_y1:.1f} A {r_tick_out+6} {r_tick_out+6} 0 {large_arc} 1 '
                    f'{arc_x2:.1f} {arc_y2:.1f}" fill="none" stroke="{accent}" stroke-width="3.5" '
                    f'stroke-linecap="round" opacity="0.85"/>')

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
      <stop offset="0%" stop-color="#3a4a5c"/><stop offset="55%" stop-color="#1a2634"/><stop offset="100%" stop-color="#0a1420"/>
    </radialGradient>
    <radialGradient id="face-{uid}" cx="40%" cy="35%" r="70%">
      <stop offset="0%" stop-color="#0f2438"/><stop offset="70%" stop-color="#071626"/><stop offset="100%" stop-color="#030b14"/>
    </radialGradient>
    <linearGradient id="glass-{uid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.10"/><stop offset="35%" stop-color="#ffffff" stop-opacity="0.02"/><stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glow-{uid}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.9"/><stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="url(#bezel-{uid})" stroke="#4a5d70" stroke-width="1.5"/>
  <circle cx="{cx}" cy="{cy}" r="{r_face}" fill="url(#face-{uid})" stroke="rgba(34,211,238,0.25)" stroke-width="1"/>
  {"".join(minors)}
  {"".join(ticks)}
  {progress_arc}
  {"".join(labels)}
  <circle cx="{cx}" cy="{cy}" r="30" fill="url(#glow-{uid})" opacity="0.35"/>
  <polygon points="{tip_x:.1f},{tip_y:.1f} {left_x:.1f},{left_y:.1f} {back_x:.1f},{back_y:.1f} {right_x:.1f},{right_y:.1f}" fill="{accent}" stroke="#ffffff" stroke-width="0.4" opacity="0.95"/>
  <circle cx="{cx}" cy="{cy}" r="7" fill="#0d1b28" stroke="{accent}" stroke-width="2"/>
  <circle cx="{cx}" cy="{cy}" r="2.4" fill="{accent}"/>
  <circle cx="{cx}" cy="{cy}" r="{r_face}" fill="url(#glass-{uid})"/>
  <text x="100" y="150" font-size="20" fill="#e0f2fe" text-anchor="middle" font-family="Share Tech Mono, monospace" font-weight="bold">{vtxt_display}</text>
  <text x="100" y="164" font-size="9" fill="#7ea6c4" text-anchor="middle" font-family="Share Tech Mono, monospace" letter-spacing="1">{unit}</text>
  <text x="100" y="196" font-size="10" fill="#9cc4de" text-anchor="middle" font-family="Share Tech Mono, monospace" letter-spacing="0.5">{label}</text>
</svg>
'''


# ------------------------------------------------------------------
# MACHINE-IN-USE VISUAL — an animated turbine icon whose spin speed,
# color, and "wear" ring react to how much of the engine's recorded
# life has been consumed by the simulation below. This is what gives
# the "I used the engine, its life is going down" feeling on screen.
# ------------------------------------------------------------------
def build_engine_visual_svg(status_class, accent, wear_pct, running):
    wear_pct = max(0.0, min(100.0, wear_pct))
    cx = cy = 110
    r_body = 92
    # wear ring: how much of the circle is "consumed" (drawn in red/accent),
    # the remainder still shows the healthy green track underneath.
    circumference = 2 * math.pi * 78
    consumed_len = circumference * (wear_pct / 100.0)
    remaining_len = circumference - consumed_len

    spin_dur = "0.6s" if status_class == "critical" else ("1.1s" if status_class == "warning" else "1.8s"
                                                            ) if running else "0s"
    spin_rule = f"animation: spinfan {spin_dur} linear infinite;" if running else "animation: none;"

    blades = []
    for i in range(6):
        angle = i * 60
        blades.append(
            f'<g transform="rotate({angle} {cx} {cy})">'
            f'<path d="M {cx} {cy} L {cx-9} {cy-58} Q {cx} {cy-70} {cx+9} {cy-58} Z" '
            f'fill="{accent}" opacity="0.85" stroke="#0a1420" stroke-width="1"/>'
            f'</g>'
        )

    smoke = ""
    if status_class == "critical" and running:
        smoke = f'''
        <circle cx="{cx+55}" cy="{cy-70}" r="6" fill="#94a3b8" opacity="0.5">
            <animate attributeName="cy" values="{cy-70};{cy-110}" dur="1.6s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.55;0" dur="1.6s" repeatCount="indefinite"/>
            <animate attributeName="r" values="5;14" dur="1.6s" repeatCount="indefinite"/>
        </circle>
        <circle cx="{cx+40}" cy="{cy-65}" r="5" fill="#94a3b8" opacity="0.4">
            <animate attributeName="cy" values="{cy-65};{cy-105}" dur="1.9s" repeatCount="indefinite" begin="0.5s"/>
            <animate attributeName="opacity" values="0.45;0" dur="1.9s" repeatCount="indefinite" begin="0.5s"/>
            <animate attributeName="r" values="4;12" dur="1.9s" repeatCount="indefinite" begin="0.5s"/>
        </circle>'''

    return f'''
<svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" width="100%">
  <defs>
    <radialGradient id="mbody" cx="35%" cy="30%" r="75%">
      <stop offset="0%" stop-color="#22344a"/><stop offset="60%" stop-color="#0f2135"/><stop offset="100%" stop-color="#050d18"/>
    </radialGradient>
    <style>
      @keyframes spinfan {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
      .fanhub {{ transform-origin: {cx}px {cy}px; {spin_rule} }}
    </style>
  </defs>

  <circle cx="{cx}" cy="{cy}" r="{r_body}" fill="url(#mbody)" stroke="#4a5d70" stroke-width="2"/>

  <!-- wear ring: consumed life (accent/red) vs remaining life (green) -->
  <circle cx="{cx}" cy="{cy}" r="78" fill="none" stroke="rgba(52,211,153,0.25)" stroke-width="8"/>
  <circle cx="{cx}" cy="{cy}" r="78" fill="none" stroke="{accent}" stroke-width="8"
          stroke-dasharray="{consumed_len:.1f} {remaining_len:.1f}" stroke-linecap="round"
          transform="rotate(-90 {cx} {cy})"/>

  <g class="fanhub">
    {"".join(blades)}
  </g>
  <circle cx="{cx}" cy="{cy}" r="16" fill="#0a1420" stroke="{accent}" stroke-width="3"/>
  <circle cx="{cx}" cy="{cy}" r="5" fill="{accent}"/>

  {smoke}

  <text x="{cx}" y="{cy+108}" font-size="13" fill="#e0f2fe" text-anchor="middle"
        font-family="Orbitron, sans-serif" font-weight="700" letter-spacing="1">
        {"RUNNING" if running else "IDLE"}
  </text>
  <text x="{cx}" y="{cy+126}" font-size="10" fill="#7ea6c4" text-anchor="middle"
        font-family="Share Tech Mono, monospace">
        Life used: {wear_pct:.1f}%
  </text>
</svg>
'''


# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Turbofan RUL Control Room",
    page_icon="🛩️",
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
# THEME — deep ocean blue, blueprint / control-room styling
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Share+Tech+Mono&display=swap');

:root {
    --abyss: #020617;
    --deep: #071a2f;
    --ocean: #0c4a6e;
    --cyan: #22d3ee;
    --cyan-glow: #67e8f9;
    --green: #34d399;
    --amber: #fbbf24;
    --red: #f87171;
    --mist: #7dd3fc;
    --text: #e0f2fe;
}

.stApp {
    background:
        radial-gradient(circle at 15% 10%, rgba(34,211,238,0.08), transparent 40%),
        radial-gradient(circle at 85% 90%, rgba(12,74,110,0.35), transparent 45%),
        linear-gradient(160deg, var(--abyss) 0%, var(--deep) 45%, #030a1a 100%);
    background-attachment: fixed;
}

/* blueprint grid overlay */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(34,211,238,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(34,211,238,0.045) 1px, transparent 1px);
    background-size: 42px 42px;
    pointer-events: none;
    z-index: 0;
}

html, body, [class*="css"] {
    color: var(--text) !important;
    font-family: 'Share Tech Mono', monospace;
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
    border-bottom: 1px solid rgba(34,211,238,0.25);
    margin-bottom: 26px;
}
.hero-title {
    font-size: 34px;
    font-weight: 900;
    background: linear-gradient(90deg, var(--mist), var(--cyan-glow), var(--mist));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(34,211,238,0.35);
    margin-bottom: 4px;
}
.hero-sub {
    color: #7ea6c4;
    font-size: 13px;
    letter-spacing: 3px;
    text-transform: uppercase;
}

/* ---- glass panels ---- */
.panel {
    background: linear-gradient(160deg, rgba(12,42,68,0.55), rgba(2,10,25,0.65));
    border: 1px solid rgba(34,211,238,0.22);
    border-radius: 16px;
    padding: 20px 22px;
    box-shadow: 0 0 25px rgba(2,10,25,0.6), inset 0 0 40px rgba(34,211,238,0.03);
    backdrop-filter: blur(6px);
    margin-bottom: 18px;
}

.panel-label {
    font-size: 11px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--cyan);
    opacity: 0.8;
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
    color: #7ea6c4;
    margin-left: 4px;
}

/* ---- status badge ---- */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    border-radius: 999px;
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
.healthy { color: var(--green); border-color: var(--green); background: rgba(52,211,153,0.08); }
.warning { color: var(--amber); border-color: var(--amber); background: rgba(251,191,36,0.08); }
.critical { color: var(--red); border-color: var(--red); background: rgba(248,113,113,0.08); }

/* selectbox tweak */
div[data-baseweb="select"] > div {
    background-color: rgba(2,10,25,0.7) !important;
    border-color: rgba(34,211,238,0.35) !important;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #04101f, #030a17);
    border-right: 1px solid rgba(34,211,238,0.15);
}

.footer-note {
    text-align: center;
    color: #3f6b87;
    font-size: 11px;
    letter-spacing: 1.5px;
    margin-top: 30px;
    padding-top: 14px;
    border-top: 1px solid rgba(34,211,238,0.12);
}

.blink-live {
    color: var(--green);
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
    <div class="hero-title">⛴ TURBOFAN ENGINE — RUL CONTROL ROOM</div>
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
        f"<span style='color:#5a89a8;font-size:12px'>Snapshot: {datetime.now().strftime('%d %b %Y — %H:%M')}</span>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.caption("Model: LightGBM Regressor")
    st.caption(f"Features tracked: {len(feature_columns)}")

# ------------------------------------------------------------------
# USAGE SIMULATION STATE — this is the "I used the engine, so its
# remaining life should go down" part. We keep a pointer (cycle_idx)
# into this engine's recorded cycles. Every time the user clicks
# "Run", we move the pointer forward, re-run the model on that
# cycle's real sensor readings, and the RUL prediction updates live.
# ------------------------------------------------------------------
if "sim_engine" not in st.session_state:
    st.session_state.sim_engine = None
if "cycle_idx" not in st.session_state:
    st.session_state.cycle_idx = 0

if st.session_state.sim_engine != selected_engine:
    st.session_state.sim_engine = selected_engine
    st.session_state.cycle_idx = 0

engine_data = test_data[test_data["unit_nr"] == selected_engine].sort_values("time_cycles").reset_index(drop=True)
max_idx = len(engine_data) - 1
st.session_state.cycle_idx = min(st.session_state.cycle_idx, max_idx)
cycle_idx = st.session_state.cycle_idx

current_row = engine_data.iloc[[cycle_idx]]
X = current_row[feature_columns]
predicted_rul = float(model.predict(X)[0])
current_cycle = int(current_row["time_cycles"].values[0])
is_at_end = cycle_idx >= max_idx

if predicted_rul < 30:
    status, status_class, status_msg, accent = "CRITICAL", "critical", "Maintenance jald zaroori hai", "#f87171"
elif predicted_rul < 80:
    status, status_class, status_msg, accent = "WARNING", "warning", "Monitor karo — degradation detected", "#fbbf24"
else:
    status, status_class, status_msg, accent = "HEALTHY", "healthy", "Engine operating within normal range", "#34d399"

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
        <div class="metric-value">{current_cycle}<span class="metric-unit">/ {int(engine_data['time_cycles'].max())} cycles</span></div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="panel">
        <div class="panel-label">System Status</div>
        <div class="status-pill {status_class}">
            <span class="dot"></span>{status}
        </div>
        <div style="color:#9cc4de;font-size:12px;margin-top:8px;">{status_msg}</div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# MACHINE-IN-USE SIMULATOR — animated engine + run/reset controls
# ------------------------------------------------------------------
sim_col, gauge_col = st.columns([1, 1])

with sim_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">Machine In Use — Run The Engine</div>', unsafe_allow_html=True)

    wear_pct = (cycle_idx / max_idx * 100) if max_idx > 0 else 0.0
    engine_svg = build_engine_visual_svg(status_class, accent, wear_pct, running=not is_at_end)
    st.markdown(engine_svg, unsafe_allow_html=True)

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("▶ Run 1", use_container_width=True, disabled=is_at_end):
            st.session_state.cycle_idx = min(cycle_idx + 1, max_idx)
            st.rerun()
    with b2:
        if st.button("⏩ Run 10", use_container_width=True, disabled=is_at_end):
            st.session_state.cycle_idx = min(cycle_idx + 10, max_idx)
            st.rerun()
    with b3:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.cycle_idx = 0
            st.rerun()

    if is_at_end:
        st.markdown(
            "<div style='color:#f87171;font-size:12px;margin-top:6px;'>"
            "⚠ Engine ke recorded cycles yahi tak hain — is se aage real sensor data available nahi hai."
            "</div>", unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='color:#7ea6c4;font-size:12px;margin-top:6px;'>"
            f"Har 'Run' click par engine ek ya zyada cycle aage chalta hai, uske real sensor readings model ko "
            f"diye jaate hain, aur RUL usi hisaab se update hoti hai."
            f"</div>", unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

with gauge_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">Predicted Remaining Useful Life</div>', unsafe_allow_html=True)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(predicted_rul, 1),
        number={"suffix": " cycles", "font": {"size": 34, "color": "#e0f2fe", "family": "Orbitron"}},
        gauge={
            "axis": {"range": [0, 150], "tickcolor": "#7ea6c4", "tickfont": {"color": "#7ea6c4"}},
            "bar": {"color": accent, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(248,113,113,0.18)"},
                {"range": [30, 80], "color": "rgba(251,191,36,0.15)"},
                {"range": [80, 150], "color": "rgba(52,211,153,0.15)"},
            ],
            "threshold": {
                "line": {"color": "#22d3ee", "width": 3},
                "thickness": 0.85,
                "value": round(predicted_rul, 1)
            }
        }
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e0f2fe"},
        height=280,
        margin=dict(l=20, r=20, t=30, b=10)
    )
    st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# SENSOR TRENDS — full historical record for this engine, with a
# marker showing where the simulation currently is.
# ------------------------------------------------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<div class="panel-label">Sensor Telemetry Over Time</div>', unsafe_allow_html=True)

fig_trend = go.Figure()
sensor_colors = {
    "T24": "#60a5fa",
    "T50": "#f472b6",
    "Ps30": "#34d399",
    "Nc": "#fbbf24",
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

fig_trend.add_vline(
    x=current_cycle,
    line_width=2,
    line_dash="dash",
    line_color="#22d3ee",
    annotation_text="engine now",
    annotation_font_color="#22d3ee",
    annotation_position="top"
)

fig_trend.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"color": "#9cc4de"},
    height=280,
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", y=1.18, font=dict(color="#e0f2fe")),
    xaxis=dict(title="Cycle", gridcolor="rgba(34,211,238,0.08)", zerolinecolor="rgba(34,211,238,0.1)"),
    yaxis=dict(
        title="Relative trend (%)",
        range=[-5, 105],
        gridcolor="rgba(34,211,238,0.08)",
        zerolinecolor="rgba(34,211,238,0.1)"
    ),
    hovermode="x unified"
)
st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# LIVE INSTRUMENT CLUSTER — analog cockpit-style dials per sensor,
# reading the CURRENT simulated cycle, not just the last recorded one.
# ------------------------------------------------------------------
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<div class="panel-label">Live Instrument Cluster — Current Simulated Reading</div>', unsafe_allow_html=True)

# Realistic operating bands pulled from the dataset itself, with a little
# headroom on each side so the needle never pins at the edge.
instrument_specs = {
    "T24": {"label": "T24 · Fan Inlet Temp", "unit": "°R", "range": [636, 649], "color": "#60a5fa"},
    "T50": {"label": "T50 · LPT Outlet Temp", "unit": "°R", "range": [1378, 1440], "color": "#f472b6"},
    "Ps30": {"label": "Ps30 · HPC Static Pressure", "unit": "psia", "range": [46.0, 49.0], "color": "#34d399"},
    "Nc": {"label": "Nc · Core Speed", "unit": "rpm", "range": [9000, 9180], "color": "#fbbf24"},
}

dial_cols = st.columns(4)
for col, (sensor, spec) in zip(dial_cols, instrument_specs.items()):
    reading = float(current_row[sensor].values[0])
    lo, hi = spec["range"]
    with col:
        svg = build_gauge_svg(reading, lo, hi, spec["label"], spec["unit"], spec["color"])
        st.markdown(svg, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# RAW SENSOR SNAPSHOT (expandable) — current simulated cycle's row
# ------------------------------------------------------------------
with st.expander("📟 View raw sensor snapshot (current simulated cycle)"):
    display_cols = ["time_cycles", "T24", "T30", "T50", "P30", "Nf", "Nc", "Ps30", "Phi", "BPR"]
    display_cols = [c for c in display_cols if c in current_row.columns]
    st.dataframe(current_row[display_cols].reset_index(drop=True), use_container_width=True)

st.markdown("""
<div class="footer-note">
    ⛴ TURBOFAN RUL CONTROL ROOM &nbsp;·&nbsp; LightGBM inference engine &nbsp;·&nbsp; NASA C-MAPSS dataset
</div>
""", unsafe_allow_html=True)
