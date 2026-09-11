"""
Module D + E - Monitoring dashboard and scenario explorer.

Streamlit app with three views:
  - Live Monitor: auto-advances a synthetic plant data stream through the
    process model, techno-economics module, and anomaly checker, showing
    rolling KPI trends, gauges, and a simple process schematic.
  - Scenario Explorer: sliders for amine concentration, target capture rate,
    and flue gas composition, with immediate KPI recalculation, a capex
    breakdown, and a tornado chart showing which lever the cost is most
    sensitive to.
  - About / Assumptions: a short in-app summary of what this model is and
    is not, so nobody mistakes it for a validated simulator.

Run with: streamlit run dashboard.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from co2_capture.anomaly import rolling_zscore_flags, static_guardrail_flags
from co2_capture.process_model import ProcessInputs, run_process_model
from co2_capture.synthetic_plant import SyntheticPlant
from co2_capture.techno_economics import cost_sensitivity_tornado, run_techno_economics

st.set_page_config(page_title="CO2 Capture Monitor", layout="wide", page_icon=":factory:")

MAX_HISTORY_POINTS = 200

st.title("MEA CO2 Capture Process Model and Monitoring Dashboard")
st.caption(
    "All flue gas data on this page is synthetically generated. No real or "
    "confidential plant data is used anywhere in this project. The process "
    "model is a correlation and mass-balance based approximation, not a "
    "rigorous rate-based simulation. See the Assumptions tab or methodology.md "
    "for sources and limitations."
)

tab_monitor, tab_explorer, tab_about = st.tabs(["Live Monitor", "Scenario Explorer", "Assumptions"])


def _init_stream_state(base_flow: float, base_co2: float):
    st.session_state.plant = SyntheticPlant(base_flow_kmol_h=base_flow, base_co2_mol_pct=base_co2)
    st.session_state.history = []
    st.session_state.t = 0.0


def _advance_stream(lean_loading, target_capture, mea_conc, n_points):
    plant = st.session_state.plant
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
            "circulation_m3_h": proc_out.solvent_circulation_m3_h,
            "cost_per_ton": econ_out.cost_usd_per_ton_co2_avoided,
            "is_upset": snapshot.is_upset,
        }
    )
    st.session_state.history = st.session_state.history[-n_points:]


def _gauge(value, title, value_range, target=None, suffix=""):
    steps = [
        {"range": [value_range[0], value_range[1] * 0.6], "color": "rgba(200,200,200,0.25)"},
        {"range": [value_range[1] * 0.6, value_range[1] * 0.85], "color": "rgba(255,200,80,0.35)"},
        {"range": [value_range[1] * 0.85, value_range[1]], "color": "rgba(255,90,90,0.35)"},
    ]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": suffix},
            title={"text": title},
            gauge={
                "axis": {"range": value_range},
                "bar": {"color": "rgba(30,120,220,0.85)"},
                "steps": steps,
                "threshold": {"line": {"color": "red", "width": 3}, "value": target} if target else None,
            },
        )
    )
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def _process_schematic(flow_kmol_h, co2_pct, capture_rate, lean_loading, rich_loading, circulation_m3_h):
    """
    A minimal block-flow schematic (not a scaled P&ID) showing the flue gas
    path through the absorber, the lean/rich solvent loop to the stripper,
    and where CO2 leaves for compression, annotated with the current live
    values so the numbers on the KPI cards have a physical home.
    """
    fig = go.Figure()

    boxes = {
        "Flue gas in": (0.02, 0.55, 0.16, 0.75),
        "Absorber": (0.22, 0.35, 0.38, 0.95),
        "Treated gas out": (0.44, 0.75, 0.60, 0.95),
        "Stripper": (0.62, 0.35, 0.78, 0.95),
        "CO2 to compression": (0.82, 0.75, 0.98, 0.95),
        "Reboiler": (0.62, 0.02, 0.78, 0.28),
    }
    for label, (x0, y0, x1, y1) in boxes.items():
        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            line=dict(color="rgba(120,120,120,0.9)"), fillcolor="rgba(120,170,230,0.18)",
        )
        fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=label, showarrow=False, font=dict(size=11))

    arrows = [
        ((0.16, 0.65), (0.22, 0.65)),
        ((0.38, 0.85), (0.44, 0.85)),
        ((0.38, 0.45), (0.62, 0.45)),
        ((0.78, 0.85), (0.82, 0.85)),
        ((0.70, 0.35), (0.70, 0.28)),
        ((0.62, 0.55), (0.38, 0.55)),
    ]
    for (x0, y0), (x1, y1) in arrows:
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=3, arrowcolor="rgba(80,80,80,0.8)",
        )

    fig.add_annotation(x=0.09, y=0.40, text=f"{flow_kmol_h:.0f} kmol/h<br>{co2_pct:.1f}% CO2", showarrow=False, font=dict(size=10))
    fig.add_annotation(x=0.50, y=0.42, text="lean solvent -&gt;", showarrow=False, font=dict(size=9))
    fig.add_annotation(x=0.50, y=0.58, text="&lt;- rich solvent", showarrow=False, font=dict(size=9))
    fig.add_annotation(
        x=0.30, y=0.20,
        text=f"lean loading {lean_loading:.2f}<br>rich loading {rich_loading:.2f}<br>circ {circulation_m3_h:.0f} m3/h",
        showarrow=False, font=dict(size=10),
    )
    fig.add_annotation(x=0.90, y=0.60, text=f"capture rate<br>{capture_rate*100:.1f}%", showarrow=False, font=dict(size=10))

    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)")
    return fig


with tab_monitor:
    st.subheader("Live synthetic plant monitor")

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        base_flow = st.number_input("Base flue gas flow (kmol/h)", 1000.0, 20000.0, 5000.0, step=100.0)
    with col_b:
        base_co2 = st.number_input("Base CO2 mole % in flue gas", 5.0, 20.0, 13.0, step=0.5)
    with col_c:
        n_points = st.slider("Points to display", 20, 200, 96)
    with col_d:
        auto_play = st.toggle("Auto-play stream", value=True)

    if "plant" not in st.session_state:
        _init_stream_state(base_flow, base_co2)

    reset_col, step_col = st.columns([1, 1])
    with reset_col:
        if st.button("Reset stream"):
            _init_stream_state(base_flow, base_co2)
    with step_col:
        manual_step = st.button("Advance one step")

    lean_loading = st.slider("Lean loading (mol CO2/mol MEA)", 0.10, 0.35, 0.20, step=0.01, key="mon_lean")
    target_capture = st.slider("Target capture rate", 0.70, 0.98, 0.90, step=0.01, key="mon_capture")
    mea_conc = st.slider("MEA concentration (wt%)", 20.0, 40.0, 30.0, step=1.0, key="mon_mea")

    if manual_step or len(st.session_state.history) == 0:
        _advance_stream(lean_loading, target_capture, mea_conc, n_points)

    @st.fragment(run_every=1.5 if auto_play else None)
    def _live_monitor_panel():
        if auto_play:
            _advance_stream(lean_loading, target_capture, mea_conc, n_points)

        df = pd.DataFrame(st.session_state.history)
        if df.empty:
            return
        latest = df.iloc[-1]

        gauge_cols = st.columns(4)
        with gauge_cols[0]:
            st.plotly_chart(_gauge(latest["capture_rate"] * 100, "Capture rate (%)", [50, 100], target=85), width='stretch')
        with gauge_cols[1]:
            st.plotly_chart(_gauge(latest["reboiler_duty_gj_per_ton"], "Reboiler duty (GJ/ton)", [0, 6], target=4.2), width='stretch')
        with gauge_cols[2]:
            st.plotly_chart(_gauge(latest["rich_loading"], "Rich loading", [0, 0.5], target=0.47), width='stretch')
        with gauge_cols[3]:
            st.plotly_chart(_gauge(latest["cost_per_ton"], "Cost (USD/ton)", [0, 200]), width='stretch')

        st.plotly_chart(
            _process_schematic(
                latest["flow_kmol_h"], latest["co2_pct"], latest["capture_rate"],
                lean_loading, latest["rich_loading"], latest["circulation_m3_h"],
            ),
            width='stretch',
        )

        flags = static_guardrail_flags(latest["capture_rate"], latest["reboiler_duty_gj_per_ton"])
        flags += rolling_zscore_flags(df["capture_rate"].tolist(), "Capture rate")
        flags += rolling_zscore_flags(df["reboiler_duty_gj_per_ton"].tolist(), "Reboiler duty")
        flags += rolling_zscore_flags(df["flow_kmol_h"].tolist(), "Flue gas flow")

        if latest["is_upset"]:
            st.info("Synthetic upset event currently injected into the feed (for demo purposes).")

        if flags:
            for f in flags:
                (st.error if f.severity == "alarm" else st.warning)(f"{f.message} (rolling stats / threshold check, not predictive)")
        else:
            st.success("No flags. Operating within normal thresholds and recent rolling statistics.")

        fig = make_subplots(rows=2, cols=2, subplot_titles=(
            "Capture rate (%)", "Reboiler duty (GJ/ton)", "Cost per ton CO2 avoided (USD)", "Flue gas flow (kmol/h)",
        ))
        fig.add_trace(go.Scatter(x=df["t_h"], y=df["capture_rate"] * 100, name="Capture rate"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["t_h"], y=df["reboiler_duty_gj_per_ton"], name="Reboiler duty"), row=1, col=2)
        fig.add_trace(go.Scatter(x=df["t_h"], y=df["cost_per_ton"], name="Cost per ton"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["t_h"], y=df["flow_kmol_h"], name="Flue gas flow"), row=2, col=2)

        upset_points = df[df["is_upset"]]
        if not upset_points.empty:
            marker_specs = [
                ("capture_rate", 100.0, 1, 1),
                ("reboiler_duty_gj_per_ton", 1.0, 1, 2),
                ("cost_per_ton", 1.0, 2, 1),
                ("flow_kmol_h", 1.0, 2, 2),
            ]
            for column, scale, row, col in marker_specs:
                fig.add_trace(
                    go.Scatter(
                        x=upset_points["t_h"], y=upset_points[column] * scale,
                        mode="markers", marker=dict(color="red", size=8, symbol="x"),
                        name="upset", showlegend=False,
                    ),
                    row=row, col=col,
                )
        fig.update_layout(height=520, showlegend=False, margin=dict(t=40, b=10))
        st.plotly_chart(fig, width='stretch')

        with st.expander("Raw stream data"):
            st.dataframe(df, width='stretch')

    _live_monitor_panel()

with tab_explorer:
    st.subheader("Scenario explorer")
    st.write(
        "Change process design inputs and see the recalculated KPIs. This is the "
        "core trade-off in amine capture: pushing capture rate higher costs more "
        "energy and money, and it shows up directly in the reboiler duty breakdown "
        "and the equipment cost breakdown below."
    )

    col1, col2 = st.columns(2)
    with col1:
        exp_flow = st.number_input("Flue gas flow (kmol/h)", 1000.0, 20000.0, 5000.0, step=100.0, key="exp_flow")
        exp_co2 = st.slider("CO2 mole % in flue gas", 5.0, 20.0, 13.0, step=0.5, key="exp_co2")
        exp_mea = st.slider("MEA concentration (wt%)", 20.0, 40.0, 30.0, step=1.0, key="exp_mea")
    with col2:
        exp_lean = st.slider("Lean loading (mol CO2/mol MEA)", 0.10, 0.35, 0.20, step=0.01, key="exp_lean_rate")
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
    m3.metric("Solvent circulation", f"{exp_out.solvent_circulation_m3_h:.0f} m3/h")
    m4.metric("Cost per ton CO2 avoided", f"${exp_econ.cost_usd_per_ton_co2_avoided:.0f}")

    st.write("#### Reboiler duty breakdown")
    duty_fig = go.Figure(
        go.Bar(
            x=["Sensible heat", "Heat of desorption", "Stripping steam"],
            y=[exp_out.duty_sensible_heat_gj_per_ton, exp_out.duty_heat_of_desorption_gj_per_ton, exp_out.duty_stripping_steam_gj_per_ton],
        )
    )
    duty_fig.update_layout(height=300, yaxis_title="GJ / ton CO2", margin=dict(t=20, b=10))
    st.plotly_chart(duty_fig, width='stretch')

    st.write("#### Capex breakdown")
    capex = exp_econ.capex
    capex_fig = go.Figure(
        go.Bar(
            x=["Absorber", "Stripper", "Reboiler", "Cross exchanger", "Pumps/aux", "Indirect/install"],
            y=[
                capex.absorber_usd, capex.stripper_usd, capex.reboiler_usd,
                capex.cross_exchanger_usd, capex.pumps_and_aux_usd, capex.indirect_and_installation_usd,
            ],
        )
    )
    capex_fig.update_layout(height=320, yaxis_title="USD", margin=dict(t=20, b=10))
    st.plotly_chart(capex_fig, width='stretch')
    st.caption(f"Total capex (order-of-magnitude): ${capex.total_capex_usd:,.0f}")

    st.write("#### Capture rate vs. energy penalty and cost")
    capture_rates = [x / 100 for x in range(70, 99)]
    duties, costs = [], []
    for cr in capture_rates:
        inp = ProcessInputs(
            flue_gas_flow_kmol_h=exp_flow, co2_mol_pct=exp_co2, mea_wt_pct=exp_mea,
            lean_loading=exp_lean, target_capture_rate=cr,
        )
        out = run_process_model(inp)
        econ = run_techno_economics(out)
        duties.append(out.reboiler_duty_gj_per_ton)
        costs.append(econ.cost_usd_per_ton_co2_avoided)

    trend_fig = make_subplots(rows=1, cols=2, subplot_titles=("Reboiler duty vs. capture rate", "Cost vs. capture rate"))
    trend_fig.add_trace(go.Scatter(x=[c * 100 for c in capture_rates], y=duties, name="Duty"), row=1, col=1)
    trend_fig.add_trace(go.Scatter(x=[c * 100 for c in capture_rates], y=costs, name="Cost"), row=1, col=2)
    trend_fig.update_xaxes(title_text="Target capture rate (%)")
    trend_fig.update_yaxes(title_text="GJ/ton CO2", row=1, col=1)
    trend_fig.update_yaxes(title_text="USD/ton CO2 avoided", row=1, col=2)
    trend_fig.update_layout(height=350, showlegend=False, margin=dict(t=40, b=10))
    st.plotly_chart(trend_fig, width='stretch')

    st.write("#### What is the cost most sensitive to?")
    tornado = cost_sensitivity_tornado(exp_inputs, run_process_model)
    tornado_fig = go.Figure()
    for entry in tornado:
        tornado_fig.add_trace(
            go.Bar(
                y=[entry.variable], x=[entry.high_cost_usd_per_ton - entry.low_cost_usd_per_ton],
                base=entry.low_cost_usd_per_ton, orientation="h", name=entry.variable,
            )
        )
    tornado_fig.update_layout(
        height=280, showlegend=False, xaxis_title="Cost per ton CO2 avoided (USD)",
        margin=dict(t=20, b=10),
    )
    st.plotly_chart(tornado_fig, width='stretch')
    st.caption("Each bar shows the cost range from swinging that one input +/- 15% around the current scenario, holding everything else fixed.")

    st.caption(
        "Cost figures are illustrative and order-of-magnitude only, built from a "
        "power-law equipment cost breakdown, not vendor quotes or a bankable "
        "techno-economic estimate."
    )

with tab_about:
    st.subheader("What this model is, and is not")
    st.markdown(
        """
        **What it is:** a correlation and mass-balance based approximation of a
        30 wt% MEA post-combustion CO2 capture unit, built entirely in open
        source Python. Rich loading comes from a simplified Kent-Eisenberg
        style equilibrium relation. Reboiler duty is broken into sensible
        heat, heat of desorption, and stripping steam, the same three
        components used to build up the number in real process literature.
        Capex is broken into major equipment line items scaled with standard
        power-law cost exponents.

        **What it is not:** a rigorous rate-based absorber/stripper design, a
        licensed process simulation, or a bankable techno-economic study. The
        anomaly checks on the Live Monitor tab are rolling control-chart
        style statistics and static thresholds, not machine learning and not
        predictive fault detection.

        **Data:** everything on this dashboard, including every number on the
        Live Monitor tab, is synthetically generated. No real or confidential
        plant data appears anywhere in this project.

        Full assumptions, cited sources, and known limitations are in
        `methodology.md` in the repository.
        """
    )
