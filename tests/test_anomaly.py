from co2_capture.anomaly import rolling_zscore_flags, static_guardrail_flags
from co2_capture.synthetic_plant import SyntheticPlant


def test_no_flags_on_stable_series():
    stable = [100.0 + (i % 3) * 0.1 for i in range(30)]
    assert rolling_zscore_flags(stable, "test signal") == []


def test_flags_a_clear_spike():
    series = [100.0] * 25 + [500.0]
    flags = rolling_zscore_flags(series, "test signal")
    assert len(flags) == 1
    assert flags[0].severity == "alarm"


def test_static_guardrail_catches_low_capture_rate():
    flags = static_guardrail_flags(capture_rate=0.70, reboiler_duty_gj_per_ton=3.3)
    assert any("Capture rate" in f.message for f in flags)


def test_static_guardrail_catches_high_duty():
    flags = static_guardrail_flags(capture_rate=0.90, reboiler_duty_gj_per_ton=5.0)
    assert any("Reboiler duty" in f.message for f in flags)


def test_static_guardrail_clean_when_nominal():
    flags = static_guardrail_flags(capture_rate=0.90, reboiler_duty_gj_per_ton=3.3)
    assert flags == []


def test_synthetic_plant_occasionally_injects_upsets():
    plant = SyntheticPlant(upset_probability=1.0, seed=42)
    snapshots = plant.generate_series(hours=5.0, step_h=0.25)
    assert any(s.is_upset for s in snapshots)
