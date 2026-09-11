"""
Module B - Techno-economics.

Breaks capex into major equipment line items (absorber column, stripper
column, reboiler, lean/rich cross-exchanger, circulation pumps) using the
standard "six-tenths rule" style power-law cost scaling common in
preliminary chemical process cost estimation, rather than a single lumped
capex multiplier. Opex is still simple (fixed O&M fraction plus steam cost
driven by the process model's reboiler duty), since detailed opex needs
site-specific utility and labor rates that are out of scope here.

This is explicitly NOT a bankable techno-economic study. No vendor quotes,
no detailed equipment sizing calculations, no financing structure beyond a
flat amortization. It is scoped to show the right cost drivers and the
right qualitative shape of the cost curve.

Reference ranges used:
  - Equipment cost scaling with a power-law exponent (commonly 0.6-0.7 for
    process columns and heat exchangers) against a capacity or duty
    variable is a standard preliminary estimation technique (see Peters,
    Timmerhaus & West, "Plant Design and Economics for Chemical Engineers").
  - IEAGHG / NETL studies on 30 wt% MEA post-combustion capture commonly
    quote total capture cost in the range of $50-100/ton CO2 avoided for
    large coal/gas power plant retrofits (varies heavily by fuel, scale,
    and financing assumptions). The reference-case equipment cost anchors
    below were chosen so the model's baseline case lands inside that
    published range, not fitted to a specific published cost breakdown.
"""

from dataclasses import dataclass, field

from .process_model import ProcessOutputs

# --- Unit costs, illustrative only, not vendor-quoted -----------------------
STEAM_COST_USD_PER_GJ = 6.0
CAPEX_AMORTIZATION_YEARS = 20
FIXED_OPEX_FRACTION_OF_CAPEX = 0.03
OPERATING_HOURS_PER_YEAR = 8000

# --- Equipment cost reference anchors ---------------------------------------
# Reference case: absorber sized for 5000 kmol/h flue gas at 13% CO2, 90%
# capture, 30 wt% MEA, 0.20 lean loading (this project's baseline scenario).
# Each anchor cost is a rough order-of-magnitude figure for a unit at that
# reference scale, then scaled by a power law against the relevant sizing
# variable for other operating points.
REF_FLUE_GAS_FLOW_KMOL_H = 5000.0
REF_SOLVENT_CIRC_M3_H = 515.0
REF_REBOILER_DUTY_GJ_H = 85.0

ABSORBER_REF_COST_USD = 42_000_000.0
STRIPPER_REF_COST_USD = 22_000_000.0
REBOILER_REF_COST_USD = 14_000_000.0
CROSS_EXCHANGER_REF_COST_USD = 9_000_000.0
PUMPS_AND_AUX_REF_COST_USD = 7_000_000.0

# Power-law scaling exponents (six-tenths-rule family). Columns scale more
# gently with throughput than compact equipment like exchangers and pumps.
ABSORBER_SCALE_EXPONENT = 0.65
STRIPPER_SCALE_EXPONENT = 0.65
REBOILER_SCALE_EXPONENT = 0.68
CROSS_EXCHANGER_SCALE_EXPONENT = 0.68
PUMPS_SCALE_EXPONENT = 0.55

# Indirect costs (installation, piping, instrumentation, engineering,
# contingency) as a multiplier on total direct equipment cost, a standard
# "Lang factor" style approximation for preliminary estimates.
INDIRECT_COST_LANG_FACTOR = 1.9


@dataclass
class CapexBreakdown:
    absorber_usd: float
    stripper_usd: float
    reboiler_usd: float
    cross_exchanger_usd: float
    pumps_and_aux_usd: float
    direct_equipment_usd: float
    indirect_and_installation_usd: float
    total_capex_usd: float


@dataclass
class EconomicOutputs:
    capex: CapexBreakdown
    annualized_capex_usd_per_year: float
    fixed_opex_usd_per_year: float
    steam_cost_usd_per_year: float
    total_annual_cost_usd: float
    co2_avoided_ton_per_year: float
    cost_usd_per_ton_co2_avoided: float


def _scaled_cost(ref_cost: float, actual: float, reference: float, exponent: float) -> float:
    ratio = max(actual, 1e-6) / reference
    return ref_cost * ratio**exponent


def _build_capex(process: ProcessOutputs) -> CapexBreakdown:
    absorber = _scaled_cost(
        ABSORBER_REF_COST_USD, process.flue_gas_flow_kmol_h, REF_FLUE_GAS_FLOW_KMOL_H, ABSORBER_SCALE_EXPONENT
    )
    stripper = _scaled_cost(
        STRIPPER_REF_COST_USD, process.solvent_circulation_m3_h, REF_SOLVENT_CIRC_M3_H, STRIPPER_SCALE_EXPONENT
    )
    reboiler = _scaled_cost(
        REBOILER_REF_COST_USD, process.reboiler_duty_total_gj_h, REF_REBOILER_DUTY_GJ_H, REBOILER_SCALE_EXPONENT
    )
    cross_exchanger = _scaled_cost(
        CROSS_EXCHANGER_REF_COST_USD,
        process.solvent_circulation_m3_h,
        REF_SOLVENT_CIRC_M3_H,
        CROSS_EXCHANGER_SCALE_EXPONENT,
    )
    pumps = _scaled_cost(
        PUMPS_AND_AUX_REF_COST_USD, process.solvent_circulation_m3_h, REF_SOLVENT_CIRC_M3_H, PUMPS_SCALE_EXPONENT
    )

    direct_equipment = absorber + stripper + reboiler + cross_exchanger + pumps
    indirect = direct_equipment * (INDIRECT_COST_LANG_FACTOR - 1.0)
    total_capex = direct_equipment + indirect

    return CapexBreakdown(
        absorber_usd=absorber,
        stripper_usd=stripper,
        reboiler_usd=reboiler,
        cross_exchanger_usd=cross_exchanger,
        pumps_and_aux_usd=pumps,
        direct_equipment_usd=direct_equipment,
        indirect_and_installation_usd=indirect,
        total_capex_usd=total_capex,
    )


def run_techno_economics(process: ProcessOutputs) -> EconomicOutputs:
    capex = _build_capex(process)

    annualized_capex = capex.total_capex_usd / CAPEX_AMORTIZATION_YEARS
    fixed_opex = capex.total_capex_usd * FIXED_OPEX_FRACTION_OF_CAPEX

    steam_cost_per_year = (
        process.reboiler_duty_total_gj_h * OPERATING_HOURS_PER_YEAR * STEAM_COST_USD_PER_GJ
    )

    total_annual_cost = annualized_capex + fixed_opex + steam_cost_per_year

    co2_avoided_ton_per_year = process.co2_captured_ton_per_day * (OPERATING_HOURS_PER_YEAR / 24.0)

    cost_per_ton = (
        total_annual_cost / co2_avoided_ton_per_year if co2_avoided_ton_per_year > 0 else float("nan")
    )

    return EconomicOutputs(
        capex=capex,
        annualized_capex_usd_per_year=annualized_capex,
        fixed_opex_usd_per_year=fixed_opex,
        steam_cost_usd_per_year=steam_cost_per_year,
        total_annual_cost_usd=total_annual_cost,
        co2_avoided_ton_per_year=co2_avoided_ton_per_year,
        cost_usd_per_ton_co2_avoided=cost_per_ton,
    )


@dataclass
class TornadoEntry:
    variable: str
    low_cost_usd_per_ton: float
    high_cost_usd_per_ton: float


def cost_sensitivity_tornado(
    base_inputs, run_process_model_fn, swing_fraction: float = 0.15
) -> list[TornadoEntry]:
    """
    Builds a tornado-chart style sensitivity table: for each key process
    input, reruns the model with that input swung +/- swing_fraction (holding
    everything else at the base case) and records the resulting cost per ton
    CO2 avoided. Used by the dashboard to show which design lever the cost
    is most sensitive to.
    """
    from dataclasses import replace

    variables = ["target_capture_rate", "lean_loading", "mea_wt_pct", "flue_gas_flow_kmol_h"]
    results = []
    for var in variables:
        base_value = getattr(base_inputs, var)
        low_value = base_value * (1 - swing_fraction)
        high_value = base_value * (1 + swing_fraction)

        low_inputs = replace(base_inputs, **{var: low_value})
        high_inputs = replace(base_inputs, **{var: high_value})

        low_cost = run_techno_economics(run_process_model_fn(low_inputs)).cost_usd_per_ton_co2_avoided
        high_cost = run_techno_economics(run_process_model_fn(high_inputs)).cost_usd_per_ton_co2_avoided

        results.append(
            TornadoEntry(
                variable=var,
                low_cost_usd_per_ton=min(low_cost, high_cost),
                high_cost_usd_per_ton=max(low_cost, high_cost),
            )
        )

    results.sort(key=lambda r: r.high_cost_usd_per_ton - r.low_cost_usd_per_ton, reverse=True)
    return results
