from co2_capture.process_model import (
    ProcessInputs,
    co2_equilibrium_partial_pressure_kpa,
    run_process_model,
)
from co2_capture.techno_economics import cost_sensitivity_tornado, run_techno_economics


def test_baseline_reboiler_duty_in_published_range():
    inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    out = run_process_model(inputs)
    assert 2.5 <= out.reboiler_duty_gj_per_ton <= 4.5


def test_baseline_rich_loading_in_plausible_range():
    inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    out = run_process_model(inputs)
    assert inputs.lean_loading < out.rich_loading <= 0.50


def test_equilibrium_pressure_increases_with_loading_and_temperature():
    p_low_loading = co2_equilibrium_partial_pressure_kpa(0.20, 313.15)
    p_high_loading = co2_equilibrium_partial_pressure_kpa(0.45, 313.15)
    assert p_high_loading > p_low_loading

    p_absorber_temp = co2_equilibrium_partial_pressure_kpa(0.30, 313.15)
    p_stripper_temp = co2_equilibrium_partial_pressure_kpa(0.30, 393.15)
    assert p_stripper_temp > p_absorber_temp


def test_higher_capture_rate_increases_duty():
    low = run_process_model(ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0, target_capture_rate=0.80))
    high = run_process_model(ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0, target_capture_rate=0.95))
    assert high.reboiler_duty_gj_per_ton > low.reboiler_duty_gj_per_ton


def test_very_lean_loading_increases_duty_vs_baseline():
    baseline = run_process_model(ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0, lean_loading=0.20))
    very_lean = run_process_model(ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0, lean_loading=0.12))
    assert very_lean.reboiler_duty_gj_per_ton > baseline.reboiler_duty_gj_per_ton


def test_reboiler_duty_components_sum_to_total():
    out = run_process_model(ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0))
    component_sum = (
        out.duty_sensible_heat_gj_per_ton
        + out.duty_heat_of_desorption_gj_per_ton
        + out.duty_stripping_steam_gj_per_ton
    )
    assert abs(component_sum - out.reboiler_duty_gj_per_ton) < 1e-6


def test_co2_mass_balance():
    inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0, target_capture_rate=0.90)
    out = run_process_model(inputs)
    expected_captured = inputs.flue_gas_flow_kmol_h * (inputs.co2_mol_pct / 100.0) * 0.90
    assert abs(out.co2_captured_kmol_h - expected_captured) < 1e-6


def test_cost_per_ton_is_positive_and_reasonable():
    inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    out = run_process_model(inputs)
    econ = run_techno_economics(out)
    assert econ.cost_usd_per_ton_co2_avoided > 0
    assert econ.cost_usd_per_ton_co2_avoided < 200


def test_capex_breakdown_components_sum_to_total():
    inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    econ = run_techno_economics(run_process_model(inputs))
    capex = econ.capex
    direct = capex.absorber_usd + capex.stripper_usd + capex.reboiler_usd + capex.cross_exchanger_usd + capex.pumps_and_aux_usd
    assert abs(direct - capex.direct_equipment_usd) < 1.0
    assert abs(capex.direct_equipment_usd + capex.indirect_and_installation_usd - capex.total_capex_usd) < 1.0


def test_larger_plant_costs_more_in_absolute_terms_but_can_be_cheaper_per_ton():
    small = run_techno_economics(run_process_model(ProcessInputs(flue_gas_flow_kmol_h=2000, co2_mol_pct=13.0)))
    large = run_techno_economics(run_process_model(ProcessInputs(flue_gas_flow_kmol_h=10000, co2_mol_pct=13.0)))
    assert large.capex.total_capex_usd > small.capex.total_capex_usd


def test_tornado_sensitivity_returns_ranked_entries():
    base = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    entries = cost_sensitivity_tornado(base, run_process_model)
    assert len(entries) == 4
    spreads = [e.high_cost_usd_per_ton - e.low_cost_usd_per_ton for e in entries]
    assert spreads == sorted(spreads, reverse=True)
    assert all(s >= 0 for s in spreads)
