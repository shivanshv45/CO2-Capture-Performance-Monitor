"""
Absorber/stripper process model for a simplified amine (MEA) CO2 capture unit.

This is NOT a rigorous rate-based mass transfer model. It is a correlation and
mass-balance based approximation intended to reproduce the right order of
magnitude and the right qualitative trends (capture rate vs. energy penalty vs.
solvent circulation), not a bankable process design.

Correlations and reference numbers are drawn from open literature on 30 wt%
MEA post-combustion capture, in particular:
  - Rochelle group (UT Austin) published pilot/process data on MEA reboiler
    duty, typically 3.0-4.0 GJ/ton CO2 for conventional 30wt% MEA.
  - Freeman & Rochelle correlations relating lean/rich loading to reboiler duty.
  - Standard CO2-MEA equilibrium loading trends (Kent-Eisenberg type behavior):
    loading capacity increases with partial pressure of CO2, decreases with
    temperature.

Where literature reports a range, we pick a single representative correlation
and cite it in comments rather than blending multiple sources, per project
scope decisions.
"""

from dataclasses import dataclass

# Molar mass of CO2, kg/kmol
CO2_MOLAR_MASS = 44.01
# Molar mass of MEA, kg/kmol
MEA_MOLAR_MASS = 61.08

# Reference reboiler duty at a "baseline" operating point (30 wt% MEA,
# 90% capture, 0.20 mol CO2 / mol MEA lean loading), GJ per ton CO2 captured.
# Consistent with published pilot-plant figures in the 3.0-3.5 GJ/ton range.
BASELINE_REBOILER_DUTY_GJ_PER_TON = 3.3
BASELINE_LEAN_LOADING = 0.20
BASELINE_CAPTURE_RATE = 0.90
BASELINE_MEA_WT_PCT = 30.0


@dataclass
class ProcessInputs:
    flue_gas_flow_kmol_h: float       # total flue gas molar flow rate
    co2_mol_pct: float                # CO2 mole fraction in flue gas, in percent (e.g. 13.0)
    mea_wt_pct: float = 30.0          # lean MEA concentration, wt%
    lean_loading: float = 0.20        # mol CO2 / mol MEA in lean solvent
    target_capture_rate: float = 0.90 # fraction of inlet CO2 to be captured


@dataclass
class ProcessOutputs:
    co2_in_kmol_h: float
    co2_captured_kmol_h: float
    co2_captured_ton_per_day: float
    capture_rate: float
    rich_loading: float
    lean_loading: float
    solvent_circulation_kmol_h: float
    reboiler_duty_gj_per_ton: float
    reboiler_duty_total_gj_h: float


def _equilibrium_rich_loading(lean_loading: float, co2_mol_pct: float) -> float:
    """
    Rough Kent-Eisenberg-style trend: rich loading rises with lean loading and
    with CO2 partial pressure, saturating toward a practical upper bound of
    ~0.50 mol CO2/mol MEA for 30 wt% MEA systems (typical industrial ceiling
    before corrosion/degradation concerns dominate).

    This is a simplified monotonic approximation of the real VLE curve shape,
    not a fitted thermodynamic model.
    """
    pco2_effect = min(co2_mol_pct / 15.0, 1.3)  # normalize against a "typical" flue gas of ~15% CO2
    max_rich = 0.50
    delta = (max_rich - lean_loading) * 0.55 * pco2_effect
    rich_loading = lean_loading + delta
    return min(rich_loading, max_rich)


def _reboiler_duty_gj_per_ton(lean_loading: float, capture_rate: float, mea_wt_pct: float) -> float:
    """
    Reboiler duty scales up as:
      - lean loading is driven lower (more solvent regeneration => more energy)
      - target capture rate is pushed higher (more absorption driving force needed)
      - MEA concentration deviates from the 30 wt% sweet spot (dilute solvent
        means more sensible heat carried per mole CO2; overly concentrated
        solvent increases corrosion-driven duty penalties in practice)

    Coefficients are chosen so the model reproduces the ~3.0-3.5 GJ/ton
    baseline at 30 wt% MEA / 90% capture / 0.20 lean loading, and pushes
    into the ~3.5-4.5 GJ/ton range as capture rate approaches 95%+, consistent
    with the qualitative trend reported in Rochelle et al. pilot studies.
    """
    lean_loading_penalty = (BASELINE_LEAN_LOADING - lean_loading) * 6.0
    capture_rate_penalty = (capture_rate - BASELINE_CAPTURE_RATE) * 9.0
    conc_penalty = abs(mea_wt_pct - BASELINE_MEA_WT_PCT) * 0.02

    duty = (
        BASELINE_REBOILER_DUTY_GJ_PER_TON
        + lean_loading_penalty
        + capture_rate_penalty
        + conc_penalty
    )
    return max(duty, 1.5)  # floor to keep the model in a physically plausible range


def run_process_model(inputs: ProcessInputs) -> ProcessOutputs:
    co2_in_kmol_h = inputs.flue_gas_flow_kmol_h * (inputs.co2_mol_pct / 100.0)
    co2_captured_kmol_h = co2_in_kmol_h * inputs.target_capture_rate

    rich_loading = _equilibrium_rich_loading(inputs.lean_loading, inputs.co2_mol_pct)
    delta_loading = max(rich_loading - inputs.lean_loading, 0.01)

    # Solvent circulation from a CO2 mass balance across the absorber:
    # mol CO2 absorbed = mol MEA circulated * delta_loading
    mea_circulation_kmol_h = co2_captured_kmol_h / delta_loading

    reboiler_duty_gj_per_ton = _reboiler_duty_gj_per_ton(
        inputs.lean_loading, inputs.target_capture_rate, inputs.mea_wt_pct
    )
    co2_captured_ton_per_h = co2_captured_kmol_h * CO2_MOLAR_MASS / 1000.0
    co2_captured_ton_per_day = co2_captured_ton_per_h * 24.0
    reboiler_duty_total_gj_h = reboiler_duty_gj_per_ton * co2_captured_ton_per_h

    return ProcessOutputs(
        co2_in_kmol_h=co2_in_kmol_h,
        co2_captured_kmol_h=co2_captured_kmol_h,
        co2_captured_ton_per_day=co2_captured_ton_per_day,
        capture_rate=inputs.target_capture_rate,
        rich_loading=rich_loading,
        lean_loading=inputs.lean_loading,
        solvent_circulation_kmol_h=mea_circulation_kmol_h,
        reboiler_duty_gj_per_ton=reboiler_duty_gj_per_ton,
        reboiler_duty_total_gj_h=reboiler_duty_total_gj_h,
    )


if __name__ == "__main__":
    demo = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    result = run_process_model(demo)
    print(result)
