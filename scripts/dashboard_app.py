"""Streamlit dashboard rendering the 6 panels defined in config/dashboard.yaml.

Run with:
    streamlit run scripts/dashboard_app.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"

st.set_page_config(page_title="K4-L3A Day 13 Monitoring", layout="wide")


@st.cache_data(ttl=5)
def load_config() -> dict:
    return yaml.safe_load(DASHBOARD_CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]


@st.cache_data(ttl=5)
def load_events(mtime: float) -> pd.DataFrame:
    if not LOG_PATH.exists():
        return pd.DataFrame()
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df


def in_window(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if df.empty:
        return df
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return df[df["ts"] >= cutoff]


def threshold_status(value: float | None, threshold: dict) -> str:
    if value is None or pd.isna(value):
        return "—"
    op = threshold["operator"]
    limit = threshold["value"]
    ok = value <= limit if op == "lte" else value >= limit
    return "🟢 OK" if ok else "🔴 BREACH"


def percentile(series: pd.Series, q: float) -> float | None:
    series = series.dropna()
    return float(series.quantile(q / 100)) if not series.empty else None


config = load_config()
mtime = LOG_PATH.stat().st_mtime if LOG_PATH.exists() else 0.0
df_all = load_events(mtime)
df = in_window(df_all, config["time_range_minutes"])

st.title(config["title"])
st.caption(
    f"Time range: last {config['time_range_minutes']} min · "
    f"Refresh: every {config['refresh_seconds']}s · Source: {LOG_PATH}"
)


@st.fragment(run_every=config["refresh_seconds"])
def render_dashboard() -> None:
    mtime = LOG_PATH.stat().st_mtime if LOG_PATH.exists() else 0.0
    df_all = load_events(mtime)
    df = in_window(df_all, config["time_range_minutes"])
    panels = {p["id"]: p for p in config["panels"]}

    if df.empty:
        st.warning("Chưa có log nào trong cửa sổ thời gian hiện tại. Hãy chạy scripts/load_test.py.")
        return

    responses = df[df["event"] == "response_sent"]
    requests = df[df["event"] == "request_received"]
    failed = df[df["event"] == "request_failed"]

    # --- Panel: latency ---
    p = panels["latency"]
    p50 = percentile(responses["latency_ms"], 50)
    p95 = percentile(responses["latency_ms"], 95)
    p99 = percentile(responses["latency_ms"], 99)
    ttft_p95 = percentile(responses["ttft_ms"], 95)
    with st.container(border=True):
        st.subheader(f"{p['title']} ({p['unit']})")
        with st.container(horizontal=True):
            st.metric("P50", f"{p50:.0f}" if p50 is not None else "—", border=True)
            st.metric("P95", f"{p95:.0f}" if p95 is not None else "—", border=True)
            st.metric("P99", f"{p99:.0f}" if p99 is not None else "—", border=True)
            st.metric("TTFT P95", f"{ttft_p95:.0f}" if ttft_p95 is not None else "—", border=True)
        st.caption(
            f"Threshold {p['threshold']['aggregation']} {p['threshold']['operator']} "
            f"{p['threshold']['value']}{p['unit']} → {threshold_status(p95, p['threshold'])}"
        )
        if not responses.empty:
            chart_df = responses.set_index("ts")[["latency_ms", "ttft_ms"]].sort_index()
            st.line_chart(chart_df)

    col_a, col_b = st.columns(2)

    # --- Panel: traffic ---
    p = panels["traffic"]
    with col_a:
        with st.container(border=True):
            st.subheader(f"{p['title']} ({p['unit']})")
            count = len(requests)
            rate_per_min = count / max(config["time_range_minutes"], 1)
            st.metric("Requests in window", count, border=True)
            st.caption(
                f"~{rate_per_min:.2f} req/min · Threshold "
                f"{p['threshold']['operator']} {p['threshold']['value']} → "
                f"{threshold_status(rate_per_min, p['threshold'])}"
            )
            if not requests.empty:
                per_minute = requests.set_index("ts").resample("1min").size()
                st.bar_chart(per_minute)

    # --- Panel: errors ---
    p = panels["errors"]
    with col_b:
        with st.container(border=True):
            st.subheader(f"{p['title']} ({p['unit']})")
            error_rate = (len(failed) / len(requests) * 100) if len(requests) else 0.0
            tool_events = df[df["tool_success"].notna()] if "tool_success" in df.columns else pd.DataFrame()
            retrieval_success = (
                (tool_events["tool_success"].sum() / len(tool_events) * 100)
                if not tool_events.empty
                else None
            )
            with st.container(horizontal=True):
                st.metric("Error rate", f"{error_rate:.1f}%", border=True)
                st.metric(
                    "Retrieval success",
                    f"{retrieval_success:.1f}%" if retrieval_success is not None else "—",
                    border=True,
                )
            st.caption(
                f"Threshold {p['threshold']['operator']} {p['threshold']['value']}% → "
                f"{threshold_status(error_rate, p['threshold'])}"
            )
            if not failed.empty and "error_type" in failed.columns:
                st.dataframe(failed["error_type"].value_counts().rename("count"))

    col_c, col_d, col_e = st.columns(3)

    # --- Panel: cost ---
    p = panels["cost"]
    with col_c:
        with st.container(border=True):
            st.subheader(f"{p['title']} ({p['unit']})")
            total_cost = responses["cost_usd"].sum() if "cost_usd" in responses.columns else 0.0
            st.metric("Total cost", f"${total_cost:.4f}", border=True)
            st.caption(
                f"Threshold {p['threshold']['operator']} {p['threshold']['value']} → "
                f"{threshold_status(total_cost, p['threshold'])}"
            )
            if not responses.empty:
                per_minute_cost = responses.set_index("ts").resample("1min")["cost_usd"].sum()
                st.line_chart(per_minute_cost)

    # --- Panel: tokens ---
    p = panels["tokens"]
    with col_d:
        with st.container(border=True):
            st.subheader(f"{p['title']} ({p['unit']})")
            tokens_in = int(responses["tokens_in"].sum()) if "tokens_in" in responses.columns else 0
            tokens_out = int(responses["tokens_out"].sum()) if "tokens_out" in responses.columns else 0
            total_tokens = tokens_in + tokens_out
            st.metric("In / Out", f"{tokens_in} / {tokens_out}", border=True)
            st.caption(
                f"Threshold {p['threshold']['operator']} {p['threshold']['value']} → "
                f"{threshold_status(total_tokens, p['threshold'])}"
            )

    # --- Panel: quality ---
    p = panels["quality"]
    with col_e:
        with st.container(border=True):
            st.subheader(f"{p['title']} ({p['unit']})")
            mean_quality = (
                responses["quality_score"].mean() if "quality_score" in responses.columns else None
            )
            st.metric(
                "Mean quality",
                f"{mean_quality:.2f}" if mean_quality is not None else "—",
                border=True,
            )
            st.caption(
                f"Threshold {p['threshold']['operator']} {p['threshold']['value']} → "
                f"{threshold_status(mean_quality, p['threshold'])}"
            )

    with st.expander("Raw events in window"):
        st.dataframe(df.sort_values("ts", ascending=False), hide_index=True)


render_dashboard()
