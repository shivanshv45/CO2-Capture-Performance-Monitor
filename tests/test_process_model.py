from co2_capture.process_model import ProcessInputs, run_process_model
from co2_capture.techno_economics import run_techno_economics


def test_baseline_reboiler_duty_in_published_range():
    inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
    out = run_process_model(inputs)
    assert 2.5 <= out.reboiler_duty_gj_per_ton <= 4.5


def test_higher_capture_rate_increases_duty():
    low = run_process_model(ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0, target_capture_rate=0.80))
    high = run_process_model(ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0, target_capture_rate=0.95))
    assert high.reboiler_duty_gj_per_ton > low.reboiler_duty_gj_per_ton


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
    assert econ.cost_usd_per_ton_co2_avoided < 500
