"""
Module D + E - Monitoring dashboard and scenario explorer.

Streamlit app with two views:
  - Live monitor: advances a synthetic plant data stream through the process
    model and techno-economics module, showing rolling KPI trends and simple
    threshold-based flags.
  - Scenario explorer: lets you change amine concentration, target capture
    rate, and flue gas composition and immediately see the recalculated KPIs,
    to show the process-design trade-off (capture rate up => energy penalty
    and cost up).

Run with: streamlit run dashboard.py
"""

import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from co2_capture.process_model import ProcessInputs, run_process_model
from co2_capture.synthetic_plant import SyntheticPlant
from co2_capture.techno_economics import run_techno_economics

st.set_page_config(page_title="CO2 Capture Monitor", layout="wide")

CAPTURE_RATE_FLAG_THRESHOLD = 0.85
REBOILER_DUTY_FLAG_THRESHOLD = 4.2  # GJ/ton

st.title("MEA CO2 Capture - Process Model & Monitoring Dashboard")
st.caption(
    "All flue gas data on this page is synthetically generated for demonstration "
    "purposes. No real or confidential plant data is used anywhere in this project. "
    "The process model is a simplified correlation-based approximation, not a "
    "rigorous rate-based simulation - see the README for assumptions and sources."
)

tab_monitor, tab_explorer = st.tabs(["Live Monitor", "Scenario Explorer"])

with tab_monitor:
    st.subheader("Live synthetic plant monitor")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        base_flow = st.number_input("Base flue gas flow (kmol/h)", 1000.0, 20000.0, 5000.0, step=100.0)
    with col_b:
        base_co2 = st.number_input("Base CO2 mole % in flue gas", 5.0, 20.0, 13.0, step=0.5)
    with col_c:
        n_points = st.slider("Number of points to display", 20, 200, 96)

    if "plant" not in st.session_state or st.button("Reset stream"):
        st.session_state.plant = SyntheticPlant(base_flow_kmol_h=base_flow, base_co2_mol_pct=base_co2)
        st.session_state.history = []
        st.session_state.t = 0.0

    plant = st.session_state.plant

    lean_loading = st.slider("Lean loading (mol CO2/mol MEA)", 0.10, 0.35, 0.20, step=0.01, key="mon_lean")
    target_capture = st.slider("Target capture rate", 0.70, 0.98, 0.90, step=0.01, key="mon_capture")
    mea_conc = st.slider("MEA concentration (wt%)", 20.0, 40.0, 30.0, step=1.0, key="mon_mea")

    advance = st.button("Advance stream by one step")

    if advance or len(st.session_state.history) == 0:
        snapshot = plant.sample(st.session_state.t)
        st.session_state.t += 0.25

        proc_in = ProcessInputs(
            flue_gas_flow_kmol_h=snapshot.flue_gas_flow_kmol_h,
            co2_mol_pct=snapshot.co2_mol_pct,
            mea_wt_pct=mea_conc,
            lean_loading=lean_loading,
            target_capture_rate=target_capture,
        )
        proc_out = run_process_model(proc_in)
        econ_out = run_techno_economics(proc_out)

        st.session_state.history.append(
            {
                "t_h": snapshot.timestamp_h,
                "flow_kmol_h": snapshot.flue_gas_flow_kmol_h,
                "co2_pct": snapshot.co2_mol_pct,
                "capture_rate": proc_out.capture_rate,
                "reboiler_duty_gj_per_ton": proc_out.reboiler_duty_gj_per_ton,
                "rich_loading": proc_out.rich_loading,
                "cost_per_ton": econ_out.cost_usd_per_ton_co2_avoided,
            }
        )
        st.session_state.history = st.session_state.history[-n_points:]

    df = pd.DataFrame(st.session_state.history)

    if not df.empty:
        latest = df.iloc[-1]

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Capture rate", f"{latest['capture_rate']*100:.1f}%")
        kpi2.metric("Reboiler duty", f"{latest['reboiler_duty_gj_per_ton']:.2f} GJ/ton")
        kpi3.metric("Rich loading", f"{latest['rich_loading']:.3f}")
        kpi4.metric("Cost", f"${latest['cost_per_ton']:.0f}/ton CO2 avoided")

        flags = []
        if latest["capture_rate"] < CAPTURE_RATE_FLAG_THRESHOLD:
            flags.append("Capture rate below target threshold")
        if latest["reboiler_duty_gj_per_ton"] > REBOILER_DUTY_FLAG_THRESHOLD:
            flags.append("Reboiler duty above normal operating range")

        if flags:
            for f in flags:
                st.warning(f"Flag: {f} (threshold-based check, not predictive)")
        else:
            st.success("No flags - operating within normal thresholds")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["t_h"], y=df["capture_rate"] * 100, name="Capture rate (%)"))
        fig.update_layout(title="Capture rate over time", xaxis_title="Time (h)", yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df["t_h"], y=df["reboiler_duty_gj_per_ton"], name="Reboiler duty"))
        fig2.update_layout(title="Reboiler duty over time", xaxis_title="Time (h)", yaxis_title="GJ/ton CO2")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=df["t_h"], y=df["cost_per_ton"], name="Cost per ton"))
        fig3.update_layout(title="Cost per ton CO2 avoided over time", xaxis_title="Time (h)", yaxis_title="USD/ton")
        st.plotly_chart(fig3, use_container_width=True)

        st.dataframe(df, use_container_width=True)

with tab_explorer:
    st.subheader("Scenario explorer")
    st.write(
        "Change process design inputs and see the recalculated KPIs. This is the "
        "core trade-off in amine capture: pushing capture rate higher costs more "
        "energy and money."
    )

    col1, col2 = st.columns(2)
    with col1:
        exp_flow = st.number_input("Flue gas flow (kmol/h)", 1000.0, 20000.0, 5000.0, step=100.0, key="exp_flow")
        exp_co2 = st.slider("CO2 mole % in flue gas", 5.0, 20.0, 13.0, step=0.5, key="exp_co2")
        exp_mea = st.slider("MEA concentration (wt%)", 20.0, 40.0, 30.0, step=1.0, key="exp_mea")
    with col2:
        exp_lean = st.slider("Lean loading (mol CO2/mol MEA)", 0.10, 0.35, 0.20, step=0.01, key="exp_lean")
        exp_capture = st.slider("Target capture rate", 0.70, 0.98, 0.90, step=0.01, key="exp_capture_rate")

    exp_inputs = ProcessInputs(
        flue_gas_flow_kmol_h=exp_flow,
        co2_mol_pct=exp_co2,
        mea_wt_pct=exp_mea,
        lean_loading=exp_lean,
        target_capture_rate=exp_capture,
    )
    exp_out = run_process_model(exp_inputs)
    exp_econ = run_techno_economics(exp_out)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("CO2 captured", f"{exp_out.co2_captured_ton_per_day:.0f} ton/day")
    m2.metric("Reboiler duty", f"{exp_out.reboiler_duty_gj_per_ton:.2f} GJ/ton")
    m3.metric("Solvent circulation", f"{exp_out.solvent_circulation_kmol_h:.0f} kmol/h")
    m4.metric("Cost", f"${exp_econ.cost_usd_per_ton_co2_avoided:.0f}/ton CO2 avoided")

    st.write("### Capture rate vs. energy penalty and cost")
    capture_rates = [x / 100 for x in range(70, 99)]
    duties = []
    costs = []
    for cr in capture_rates:
        inp = ProcessInputs(
            flue_gas_flow_kmol_h=exp_flow,
            co2_mol_pct=exp_co2,
            mea_wt_pct=exp_mea,
            lean_loading=exp_lean,
            target_capture_rate=cr,
        )
        out = run_process_model(inp)
        econ = run_techno_economics(out)
        duties.append(out.reboiler_duty_gj_per_ton)
        costs.append(econ.cost_usd_per_ton_co2_avoided)

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(x=[c * 100 for c in capture_rates], y=duties, name="Reboiler duty (GJ/ton)"))
    fig_sens.update_layout(
        title="Reboiler duty vs. target capture rate",
        xaxis_title="Target capture rate (%)",
        yaxis_title="GJ/ton CO2",
    )
    st.plotly_chart(fig_sens, use_container_width=True)

    fig_cost = go.Figure()
    fig_cost.add_trace(go.Scatter(x=[c * 100 for c in capture_rates], y=costs, name="Cost (USD/ton)"))
    fig_cost.update_layout(
        title="Cost vs. target capture rate",
        xaxis_title="Target capture rate (%)",
        yaxis_title="USD/ton CO2 avoided",
    )
    st.plotly_chart(fig_cost, use_container_width=True)

    st.caption(
        "Cost figures are illustrative and order-of-magnitude only, based on "
        "published ranges for MEA post-combustion capture retrofits. They are "
        "not a bankable techno-economic estimate."
    )
