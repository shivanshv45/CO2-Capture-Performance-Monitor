"""
Module B - Techno-economics.

Applies simple, published order-of-magnitude cost correlations to the process
model outputs to produce a rough $/ton CO2 avoided figure. This is explicitly
NOT a bankable techno-economic study - no vendor quotes, no site-specific
capex, no detailed equipment sizing. It is meant to show commercial awareness
and reproduce the right shape of the cost-vs-capture-rate curve, which is the
part interviewers actually care about.

Reference ranges used:
  - IEAGHG / NETL studies on 30 wt% MEA post-combustion capture commonly
    quote total capture cost in the range of $50-100/ton CO2 avoided for
    large coal/gas power plant retrofits (varies heavily by fuel, scale,
    and financing assumptions).
  - Energy penalty (reboiler duty) is the single largest driver of opex in
    these studies, so opex here is modeled as strongly duty-dependent while
    capex is modeled as a function of throughput (column/exchanger sizing
    scales with flow, not with capture rate directly).
"""

from dataclasses import dataclass

from .process_model import ProcessOutputs

# Illustrative unit costs - NOT vendor-quoted, order-of-magnitude only.
STEAM_COST_USD_PER_GJ = 6.0          # rough industrial steam cost
CAPEX_USD_PER_TON_CO2_DAY_CAPACITY = 250_000.0  # rough capex per ton/day nameplate capacity
CAPEX_AMORTIZATION_YEARS = 20
FIXED_OPEX_FRACTION_OF_CAPEX = 0.03   # annual fixed O&M as a fraction of capex
OPERATING_HOURS_PER_YEAR = 8000       # allowing for planned downtime


@dataclass
class EconomicOutputs:
    capex_usd: float
    annualized_capex_usd_per_year: float
    fixed_opex_usd_per_year: float
    steam_cost_usd_per_year: float
    total_annual_cost_usd: float
    co2_avoided_ton_per_year: float
    cost_usd_per_ton_co2_avoided: float


def run_techno_economics(process: ProcessOutputs) -> EconomicOutputs:
    nameplate_ton_per_day = process.co2_captured_ton_per_day
    capex_usd = nameplate_ton_per_day * CAPEX_USD_PER_TON_CO2_DAY_CAPACITY
    annualized_capex = capex_usd / CAPEX_AMORTIZATION_YEARS
    fixed_opex = capex_usd * FIXED_OPEX_FRACTION_OF_CAPEX

    steam_cost_per_year = (
        process.reboiler_duty_total_gj_h * OPERATING_HOURS_PER_YEAR * STEAM_COST_USD_PER_GJ
    )

    total_annual_cost = annualized_capex + fixed_opex + steam_cost_per_year

    co2_avoided_ton_per_year = process.co2_captured_ton_per_day * (
        OPERATING_HOURS_PER_YEAR / 24.0
    )

    cost_per_ton = (
        total_annual_cost / co2_avoided_ton_per_year if co2_avoided_ton_per_year > 0 else float("nan")
    )

    return EconomicOutputs(
        capex_usd=capex_usd,
        annualized_capex_usd_per_year=annualized_capex,
        fixed_opex_usd_per_year=fixed_opex,
        steam_cost_usd_per_year=steam_cost_per_year,
        total_annual_cost_usd=total_annual_cost,
        co2_avoided_ton_per_year=co2_avoided_ton_per_year,
        cost_usd_per_ton_co2_avoided=cost_per_ton,
    )
