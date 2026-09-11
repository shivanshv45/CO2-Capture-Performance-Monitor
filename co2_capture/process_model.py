"""
Absorber/stripper process model for a simplified amine (MEA) CO2 capture unit.

This is NOT a rigorous rate-based mass transfer model (no HTU/NTU, no packed
column hydraulics, no full stage-by-stage VLE solve). It combines:

  1. A Kent-Eisenberg-style equilibrium relation for CO2 partial pressure over
     loaded MEA solution, used to back out rich loading from absorber
     operating conditions instead of assuming a fixed number.
  2. A first-principles decomposition of reboiler duty into its three
     physically real components (sensible heat, heat of CO2 desorption,
     stripping steam heat of vaporization) rather than a single lumped
     correlation, since that is how the number is actually built up in
     process literature and it is what lets each design lever move duty
     through a distinct physical mechanism.

References (open literature, no proprietary or licensed simulator data):
  - Kent, R.L. and Eisenberg, B., "Better Data for Amine Treating",
    Hydrocarbon Processing, 1976 - equilibrium constant framework for
    CO2/H2S over aqueous amine solutions.
  - Freeman, S.A. and Rochelle, G.T. (UT Austin, Texas Carbon Management
    Program) - reboiler duty breakdown into sensible heat, heat of reaction,
    and stripping steam for 30 wt% MEA; reported total reboiler duty of
    roughly 3.0-4.0 GJ/ton CO2 for conventional 30 wt% MEA at ~90% capture.
  - Heat of CO2 absorption in 30 wt% MEA commonly cited around 1.8-2.0
    GJ/ton CO2 (approx 82 kJ/mol) at typical stripper loadings.

Where literature reports a range, a single representative value is picked
and cited in comments rather than blending multiple sources.
"""

import math
from dataclasses import dataclass

# --- Physical constants -----------------------------------------------------

CO2_MOLAR_MASS = 44.01     # kg/kmol
MEA_MOLAR_MASS = 61.08     # kg/kmol
WATER_MOLAR_MASS = 18.02   # kg/kmol
R_GAS_CONST = 8.314        # J/mol.K

# --- Kent-Eisenberg equilibrium parameters ----------------------------------
# Simplified two-parameter form of the Kent-Eisenberg relation:
#   ln(P*_CO2 [kPa]) = A - B/T[K] + C * loading + D * loading^2
# Fitted qualitatively to reproduce published 30 wt% MEA VLE behavior at
# 313-393 K (40-120 C) and loadings of 0.10-0.50 mol CO2/mol MEA: partial
# pressure rises steeply above ~0.45 loading (the "knee" of the curve that
# limits practical rich loading) and rises with temperature at fixed loading.
KE_A = 20.755
KE_B = 7200.0
KE_C = 5.72
KE_D = 10.0

ABSORBER_TEMP_K = 313.15   # ~40 C, typical absorber operating temperature
STRIPPER_TEMP_K = 393.15   # ~120 C, typical stripper reboiler temperature

# --- Reboiler duty component references -------------------------------------
# Heat of CO2 desorption in 30 wt% MEA, GJ/ton CO2 (~82 kJ/mol CO2).
HEAT_OF_DESORPTION_GJ_PER_TON = 1.86
# Specific heat of 30 wt% aqueous MEA solution, kJ/kg.K (typical literature value).
SOLVENT_SPECIFIC_HEAT_KJ_PER_KG_K = 3.8
# Approach temperature swing the lean/rich exchanger leaves unrecovered, K.
LEAN_RICH_EXCHANGER_APPROACH_K = 10.0
# Latent heat of stripping steam at stripper conditions, kJ/kg.
STRIPPING_STEAM_LATENT_HEAT_KJ_KG = 2200.0
# Stripping steam ratio: kg steam per kg CO2 released, typical for 30wt% MEA.
BASELINE_STRIPPING_STEAM_RATIO = 0.30


@dataclass
class ProcessInputs:
    flue_gas_flow_kmol_h: float        # total flue gas molar flow rate
    co2_mol_pct: float                 # CO2 mole fraction in flue gas, percent (e.g. 13.0)
    mea_wt_pct: float = 30.0           # lean MEA concentration, wt%
    lean_loading: float = 0.20         # mol CO2 / mol MEA in lean solvent
    target_capture_rate: float = 0.90  # fraction of inlet CO2 to be captured
    absorber_temp_k: float = ABSORBER_TEMP_K
    stripper_temp_k: float = STRIPPER_TEMP_K


@dataclass
class ProcessOutputs:
    flue_gas_flow_kmol_h: float
    co2_in_kmol_h: float
    co2_captured_kmol_h: float
    co2_captured_ton_per_day: float
    capture_rate: float
    rich_loading: float
    lean_loading: float
    co2_partial_pressure_rich_kpa: float
    solvent_circulation_kmol_h: float
    solvent_circulation_m3_h: float
    reboiler_duty_gj_per_ton: float
    reboiler_duty_total_gj_h: float
    duty_sensible_heat_gj_per_ton: float
    duty_heat_of_desorption_gj_per_ton: float
    duty_stripping_steam_gj_per_ton: float


def co2_equilibrium_partial_pressure_kpa(loading: float, temp_k: float) -> float:
    """
    Kent-Eisenberg-style equilibrium CO2 partial pressure (kPa) above an
    aqueous MEA solution at a given loading and temperature. Monotonic
    increasing in both loading and temperature, matching the qualitative
    shape of published CO2-MEA VLE data.
    """
    ln_p = KE_A - KE_B / temp_k + KE_C * loading + KE_D * loading**2
    return math.exp(ln_p)


def _solve_rich_loading(lean_loading: float, co2_mol_pct: float, total_pressure_kpa: float,
                         absorber_temp_k: float) -> float:
    """
    Estimate rich loading by finding the loading at which the equilibrium
    CO2 partial pressure (Kent-Eisenberg) equals the CO2 partial pressure
    actually present in the flue gas at absorber conditions. This is the
    thermodynamic pinch point the absorber approaches at its bottom (richest)
    end, standard shortcut logic for approximating maximum achievable rich
    loading, then applying a practical approach factor since a real column
    does not reach full equilibrium at the bottom stage.
    """
    co2_partial_pressure_kpa = total_pressure_kpa * (co2_mol_pct / 100.0)

    lo, hi = lean_loading, 0.55
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        p_mid = co2_equilibrium_partial_pressure_kpa(mid, absorber_temp_k)
        if p_mid < co2_partial_pressure_kpa:
            lo = mid
        else:
            hi = mid
    equilibrium_max_loading = lo

    # A real absorber approaches, but does not reach, the equilibrium pinch.
    approach_factor = 0.85
    rich_loading = lean_loading + (equilibrium_max_loading - lean_loading) * approach_factor
    return min(rich_loading, 0.50)


def _reboiler_duty_components(lean_loading: float, rich_loading: float,
                               capture_rate: float, mea_wt_pct: float) -> tuple[float, float, float]:
    """
    Decompose reboiler duty into its three standard physical components:

      1. Sensible heat: heating the circulating solvent from absorber to
         stripper temperature, net of lean/rich cross-exchanger recovery
         (only the unrecovered approach-temperature portion needs reboiler
         heat).
      2. Heat of desorption: breaking the CO2-amine chemical bond, a near
         fixed GJ/ton CO2 figure for a given amine.
      3. Stripping steam: steam used to strip CO2 out of solution in the
         stripper. Driving the lean loading down (deeper regeneration) needs
         more stripping steam per ton of CO2 handled, and pushing target
         capture rate up needs a lower CO2 partial pressure at the absorber
         top, which is achieved by driving lean loading down further, so
         both design levers act through the same physical mechanism here.
    """
    loading_swing = max(rich_loading - lean_loading, 0.02)

    # Sensible heat: solvent must be heated across the unrecovered approach
    # temperature on every pass through the loop. Expressed per ton CO2 by
    # dividing solvent mass flow (per ton CO2, via loading swing) into the
    # temperature rise.
    mea_moles_per_ton_co2 = 1000.0 / (loading_swing * CO2_MOLAR_MASS)
    mea_kg_per_ton_co2 = mea_moles_per_ton_co2 * MEA_MOLAR_MASS
    solution_kg_per_ton_co2 = mea_kg_per_ton_co2 / (mea_wt_pct / 100.0)
    sensible_heat_kj = (
        solution_kg_per_ton_co2 * SOLVENT_SPECIFIC_HEAT_KJ_PER_KG_K * LEAN_RICH_EXCHANGER_APPROACH_K
    )
    sensible_heat_gj_per_ton = sensible_heat_kj / 1e6

    # Heat of desorption is approximately constant per ton CO2 for a given amine.
    desorption_gj_per_ton = HEAT_OF_DESORPTION_GJ_PER_TON

    # Stripping steam scales up as lean loading is driven down (deeper
    # regeneration strips more CO2 out of a given amount of solvent, which
    # needs proportionally more steam per ton of CO2 handled) and as target
    # capture rate is pushed higher (a tighter capture spec needs a leaner,
    # more thoroughly stripped solvent to hit the required absorber driving
    # force at the top of the column). The lean-loading dependence is the
    # dominant term here, consistent with Freeman & Rochelle's finding that
    # stripper energy is driven primarily by how deep the lean end is
    # regenerated, more so than by absorber-side conditions.
    baseline_lean_loading = 0.20
    lean_depth_factor = (baseline_lean_loading / max(lean_loading, 0.05)) ** 1.8
    capture_depth_factor = 1.0 + max(capture_rate - 0.70, 0.0) * 1.8
    steam_ratio = BASELINE_STRIPPING_STEAM_RATIO * lean_depth_factor * capture_depth_factor
    steam_kg_per_ton_co2 = steam_ratio * 1000.0
    steam_heat_kj = steam_kg_per_ton_co2 * STRIPPING_STEAM_LATENT_HEAT_KJ_KG
    steam_gj_per_ton = steam_heat_kj / 1e6

    # MEA concentration has a shallow U-shaped effect on practical duty: too
    # dilute wastes sensible heat carrying excess water through the loop
    # (already captured above via solution mass), while pushing much above
    # the conventional 30 wt% ceiling brings corrosion-driven derating and
    # degradation losses that are commonly cited as the reason plants don't
    # simply run more concentrated MEA, modeled here as a small penalty
    # above the practical 30-35 wt% ceiling.
    if mea_wt_pct > 35.0:
        steam_gj_per_ton *= 1.0 + (mea_wt_pct - 35.0) * 0.02

    return sensible_heat_gj_per_ton, desorption_gj_per_ton, steam_gj_per_ton


def run_process_model(inputs: ProcessInputs, total_pressure_kpa: float = 110.0) -> ProcessOutputs:
    co2_in_kmol_h = inputs.flue_gas_flow_kmol_h * (inputs.co2_mol_pct / 100.0)
    co2_captured_kmol_h = co2_in_kmol_h * inputs.target_capture_rate

    rich_loading = _solve_rich_loading(
        inputs.lean_loading, inputs.co2_mol_pct, total_pressure_kpa, inputs.absorber_temp_k
    )
    co2_partial_pressure_rich_kpa = co2_equilibrium_partial_pressure_kpa(
        rich_loading, inputs.absorber_temp_k
    )
    loading_swing = max(rich_loading - inputs.lean_loading, 0.02)

    # Solvent circulation from a CO2 mass balance across the absorber:
    # mol CO2 absorbed = mol MEA circulated * loading swing.
    mea_circulation_kmol_h = co2_captured_kmol_h / loading_swing
    mea_circulation_kg_h = mea_circulation_kmol_h * MEA_MOLAR_MASS
    solution_kg_h = mea_circulation_kg_h / (inputs.mea_wt_pct / 100.0)
    solution_density_kg_m3 = 1010.0  # typical for 30 wt% aqueous MEA, roughly water-like
    solvent_circulation_m3_h = solution_kg_h / solution_density_kg_m3

    sensible, desorption, steam = _reboiler_duty_components(
        inputs.lean_loading, rich_loading, inputs.target_capture_rate, inputs.mea_wt_pct
    )
    reboiler_duty_gj_per_ton = sensible + desorption + steam

    co2_captured_ton_per_h = co2_captured_kmol_h * CO2_MOLAR_MASS / 1000.0
    co2_captured_ton_per_day = co2_captured_ton_per_h * 24.0
    reboiler_duty_total_gj_h = reboiler_duty_gj_per_ton * co2_captured_ton_per_h

    return ProcessOutputs(
        flue_gas_flow_kmol_h=inputs.flue_gas_flow_kmol_h,
        co2_in_kmol_h=co2_in_kmol_h,
        co2_captured_kmol_h=co2_captured_kmol_h,
        co2_captured_ton_per_day=co2_captured_ton_per_day,
        capture_rate=inputs.target_capture_rate,
        rich_loading=rich_loading,
        lean_loading=inputs.lean_loading,
        co2_partial_pressure_rich_kpa=co2_partial_pressure_rich_kpa,
        solvent_circulation_kmol_h=mea_circulation_kmol_h,
        solvent_circulation_m3_h=solvent_circulation_m3_h,
        reboiler_duty_gj_per_ton=reboiler_duty_gj_per_ton,
        reboiler_duty_total_gj_h=reboiler_duty_total_gj_h,
        duty_sensible_heat_gj_per_ton=sensible,
        duty_heat_of_desorption_gj_per_ton=desorption,
        duty_stripping_steam_gj_per_ton=steam,
    )


if __name__ == "__main__":
    demo = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    result = run_process_model(demo)
    print(result)
