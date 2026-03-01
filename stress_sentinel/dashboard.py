"""
StressSentinel — Enhanced Realtime Dashboard

A read-only Streamlit dashboard that visualizes live system metrics
by reading from a rolling JSON file produced by metrics_collector.py.

Usage:
    streamlit run dashboard.py

Dependencies:
    pip install streamlit-autorefresh
"""

import json
import os
from typing import Optional, Tuple
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh
# ── Configuration ────────────────────────────────────────
_LIVE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "live_metrics.json"
)
_ANOMALY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "anomaly_results.json"
)
_REFRESH_INTERVAL = 1  # seconds

st_autorefresh(interval=_REFRESH_INTERVAL * 1000, key="data_refresh")

st.session_state.setdefault("last_refresh", datetime.now())
st.session_state["last_refresh"] = datetime.now()
# Color schemes
_WARM_COLORS = {"cpu": "#FF6B6B", "process_cpu": "#FFA726"}
_COOL_COLORS = {"threads": "#42A5F5", "load": "#66BB6A"}


# ── Page Setup ───────────────────────────────────────────
st.set_page_config(
    page_title="StressSentinel Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Dark theme background */
    .stApp {
        background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
    }
    
    /* Header styling */
    .dashboard-header {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border: 1px solid #3a3a5c;
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    /* Status badge styling */
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: 600;
        font-size: 0.9rem;
        margin-left: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-healthy {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        color: white;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
    }
    
    .status-stress {
        background: linear-gradient(135deg, #FF9800, #F57C00);
        color: white;
        box-shadow: 0 4px 15px rgba(255, 152, 0, 0.3);
    }
    
    .status-anomaly {
        background: linear-gradient(135deg, #F44336, #D32F2F);
        color: white;
        box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3);
    }
    
    /* Enhanced metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border: 1px solid #3a3a5c;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.4);
    }
    
    div[data-testid="stMetric"] label {
        color: #a0a0c0;
        font-size: 0.9rem;
        font-weight: 500;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #e0e0ff;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: 5px;
        background: rgba(255,255,255,0.1);
    }
    
    /* Chart container styling */
    .stPlotlyChart, div[data-testid="stVegaLiteChart"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #3a3a5c;
        border-radius: 15px;
        padding: 1rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border-right: 1px solid #3a3a5c;
    }
    
    /* Insights section */
    .insights-container {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border: 1px solid #3a3a5c;
        border-radius: 15px;
        padding: 1.5rem;
        margin-top: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    
    .insight-item {
        background: rgba(255,255,255,0.05);
        border-left: 4px solid #42A5F5;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: background 0.2s ease;
    }
    
    .insight-item:hover {
        background: rgba(255,255,255,0.08);
    }
    
    .insight-text {
        color: #e0e0ff;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    
    /* Custom selectbox styling */
    .stSelectbox > div > div {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border: 1px solid #3a3a5c;
        border-radius: 8px;
    }
    
    /* Divider styling */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #3a3a5c, transparent);
        margin: 2rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helper Functions ───────────────────────────────────────
def load_live_metrics() -> Optional[pd.DataFrame]:
    """Load the rolling live metrics JSON file into a DataFrame."""
    if not os.path.exists(_LIVE_FILE):
        return None
    try:
        with open(_LIVE_FILE, "r") as f:
            data = json.load(f)
        if not data:
            return None
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        return df
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def load_anomaly_results() -> Optional[dict]:
    """Load anomaly detection results if available."""
    if not os.path.exists(_ANOMALY_FILE):
        return None
    try:
        with open(_ANOMALY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None


def get_system_status(df: pd.DataFrame, anomaly_data: Optional[dict]) -> Tuple[str, str]:
    """Determine system status based on metrics and anomaly data."""
    if anomaly_data and anomaly_data.get("anomaly_detected"):
        return "Anomaly Detected", "status-anomaly"
    
    if len(df) < 5:
        return "Initializing", "status-healthy"
    
    recent_cpu = df["cpu_percent"].tail(10).mean()
    recent_load = df["load_avg"].tail(10).mean()
    
    if recent_cpu > 70 or recent_load > 2.0:
        return "Under Stress", "status-stress"
    
    return "Healthy", "status-healthy"


def get_rolling_window_data(df: pd.DataFrame, window_seconds: int) -> pd.DataFrame:
    """Filter data to the specified rolling window."""
    if df.empty:
        return df
    
    cutoff_time = df["time"].iloc[-1] - pd.Timedelta(seconds=window_seconds)
    return df[df["time"] >= cutoff_time].copy()


def generate_insights(df: pd.DataFrame) -> list:
    """Generate textual insights from recent data."""
    if len(df) < 5:
        return ["Collecting data..."]
    
    insights = []
    
    # CPU analysis
    recent_cpu = df["cpu_percent"].tail(10)
    cpu_trend = "increasing" if recent_cpu.is_monotonic_increasing else "decreasing" if recent_cpu.is_monotonic_decreasing else "stable"
    cpu_volatility = recent_cpu.std()
    
    if cpu_volatility > 20:
        insights.append(f"🔥 **CPU volatility high** ({cpu_volatility:.1f}% std) - system experiencing fluctuating load")
    elif cpu_trend == "increasing" and recent_cpu.iloc[-1] > 50:
        insights.append(f"📈 **CPU trending upward** - current usage at {recent_cpu.iloc[-1]:.1f}%")
    elif cpu_trend == "stable":
        insights.append(f"✅ **CPU stable** - averaging {recent_cpu.mean():.1f}% with low volatility")
    
    # Process CPU analysis
    process_cpu = df["process_cpu_percent"].tail(10)
    if process_cpu.mean() > 10:
        insights.append(f"⚙️ **Process CPU elevated** - averaging {process_cpu.mean():.1f}%")
    
    # Thread count analysis
    thread_changes = df["thread_count"].tail(10).diff().dropna()
    if thread_changes.abs().sum() > 0:
        insights.append(f"🧵 **Thread activity detected** - {thread_changes.abs().sum()} changes observed")
    else:
        insights.append(f"🧵 **Thread count unchanged** - stable at {df['thread_count'].iloc[-1]} threads")
    
    # Load average analysis
    load_trend = df["load_avg"].tail(10)
    if load_trend.is_monotonic_increasing and load_trend.iloc[-1] > load_trend.iloc[0] * 1.2:
        insights.append(f"📊 **Load average drifting upward** - from {load_trend.iloc[0]:.2f} to {load_trend.iloc[-1]:.2f}")
    elif load_trend.mean() > 1.5:
        insights.append(f"📊 **Load average elevated** - averaging {load_trend.mean():.2f}")
    
    return insights[:4]  # Return top 4 insights


def create_enhanced_chart(df: pd.DataFrame, metric: str, title: str, color: str, height: int = 300):
    """Create an enhanced line chart with better styling."""
    chart_data = df[metric]
    
    # Create a more detailed chart using Streamlit's native line_chart with custom styling
    st.subheader(f"**{title}**")
    
    # Add some statistics
    latest_val = chart_data.iloc[-1]
    avg_val = chart_data.mean()
    max_val = chart_data.max()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current", f"{latest_val:.1f}")
    with col2:
        st.metric("Average", f"{avg_val:.1f}")
    with col3:
        st.metric("Peak", f"{max_val:.1f}")
    
    # The actual chart
    st.line_chart(chart_data, color=color, height=height)


# ── Main UI ──────────────────────────────────────────────
# Header with status
df = load_live_metrics()
anomaly_data = load_anomaly_results()

if df is not None and not df.empty:
    status_text, status_class = get_system_status(df, anomaly_data)
    
    st.markdown(f"""
    <div class="dashboard-header">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <h1 style="color: #e0e0ff; margin: 0; font-size: 2.5rem; font-weight: 700;">🛡️ StressSentinel</h1>
                <p style="color: #a0a0c0; margin: 0.5rem 0; font-size: 1.1rem;">Real-time System Monitoring Dashboard</p>
            </div>
            <div class="status-badge {status_class}">
                {status_text}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="dashboard-header">
        <h1 style="color: #e0e0ff; margin: 0; font-size: 2.5rem; font-weight: 700;">🛡️ StressSentinel</h1>
        <p style="color: #a0a0c0; margin: 0.5rem 0; font-size: 1.1rem;">Real-time System Monitoring Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar controls
with st.sidebar:
    st.markdown("### 📊 Display Settings")
    
    # Rolling window selector
    window_options = {
        "Last 30 seconds": 30,
        "Last 60 seconds": 60,
        "Last 120 seconds": 120
    }
    
    selected_window = st.selectbox(
        "Time Window",
        options=list(window_options.keys()),
        index=0,
        help="Select the time window to display in charts"
    )
    
    window_seconds = window_options[selected_window]
    
    st.markdown("---")
    st.markdown("### 📋 System Info")
    st.caption(f"Refresh Rate: {_REFRESH_INTERVAL}s")
    st.caption(f"Data Source: live_metrics.json")
    
    if anomaly_data:
        st.markdown("### 🚨 Anomaly Status")
        if anomaly_data.get("anomaly_detected"):
            st.error("Anomaly Detected")
            st.json(anomaly_data)
        else:
            st.success("No Anomalies")

# Main content area
if df is None or df.empty:
    st.warning(
        "⏳ Waiting for live metrics…\n\n"
        "Start the collector with `--live-output data/live_metrics.json` "
        "to begin streaming data."
    )
    st.stop()

# Apply rolling window
filtered_df = get_rolling_window_data(df, window_seconds)

if filtered_df.empty:
    st.warning("No data available for the selected time window.")
    st.stop()

# ── Summary Cards ────────────────────────────────────────
latest = filtered_df.iloc[-1]
prev = filtered_df.iloc[-2] if len(filtered_df) > 1 else latest

col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    delta_color = "normal" if abs(latest['cpu_percent'] - prev['cpu_percent']) < 5 else "inverse"
    st.metric(
        label="🔥 System CPU %",
        value=f"{latest['cpu_percent']:.1f}%",
        delta=f"{latest['cpu_percent'] - prev['cpu_percent']:+.1f}%",
        delta_color=delta_color
    )

with col2:
    delta_color = "normal" if abs(latest['process_cpu_percent'] - prev['process_cpu_percent']) < 5 else "inverse"
    st.metric(
        label="⚙️ Process CPU %",
        value=f"{latest['process_cpu_percent']:.1f}%",
        delta=f"{latest['process_cpu_percent'] - prev['process_cpu_percent']:+.1f}%",
        delta_color=delta_color
    )

with col3:
    delta_color = "normal" if latest["thread_count"] == prev["thread_count"] else "inverse"
    st.metric(
        label="🧵 Thread Count",
        value=int(latest["thread_count"]),
        delta=int(latest["thread_count"] - prev["thread_count"]),
        delta_color=delta_color
    )

with col4:
    delta_color = "normal" if abs(latest['load_avg'] - prev['load_avg']) < 0.1 else "inverse"
    st.metric(
        label="📊 Load Avg (1m)",
        value=f"{latest['load_avg']:.2f}",
        delta=f"{latest['load_avg'] - prev['load_avg']:+.2f}",
        delta_color=delta_color
    )

st.markdown("---")

# ── Realtime Charts ──────────────────────────────────────
chart_df = filtered_df.set_index("time")

# CPU metrics (warm colors)
col1, col2 = st.columns(2)

with col1:
    create_enhanced_chart(chart_df, "cpu_percent", "� System CPU Usage", _WARM_COLORS["cpu"])

with col2:
    create_enhanced_chart(chart_df, "process_cpu_percent", "⚙️ Process CPU Usage", _WARM_COLORS["process_cpu"])

# System metrics (cool colors)
col3, col4 = st.columns(2)

with col3:
    create_enhanced_chart(chart_df, "thread_count", "🧵 Thread Count", _COOL_COLORS["threads"])

with col4:
    create_enhanced_chart(chart_df, "load_avg", "� Load Average (1m)", _COOL_COLORS["load"])

# ── Insights Section ─────────────────────────────────────
st.markdown("---")

insights = generate_insights(filtered_df)

st.markdown("""
<div class="insights-container">
    <h3 style="color: #e0e0ff; margin-bottom: 1rem;">💡 System Insights</h3>
""", unsafe_allow_html=True)

for insight in insights:
    st.markdown(f"""
    <div class="insight-item">
        <div class="insight-text">{insight}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────
st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"📊 Showing {len(filtered_df)} samples")

with footer_col2:
    if not filtered_df.empty:
        st.caption(f"⏰ Last update: {filtered_df['time'].iloc[-1].strftime('%H:%M:%S')}")

with footer_col3:
    st.caption(f"🔄 Auto-refresh: {_REFRESH_INTERVAL}s")

# ── Auto-refresh ─────────────────────────────────────────
# Use streamlit-autorefresh for smooth realtime updates

