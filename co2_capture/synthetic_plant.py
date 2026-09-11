"""
Module C - Synthetic plant data stream.

Generates a time series of flue gas flow rate and CO2 concentration with
drift and noise to mimic real plant load variability over a day (e.g. a power
plant ramping with grid demand). This is entirely synthetic - no real or
confidential plant data is used anywhere in this project.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class PlantSnapshot:
    timestamp_h: float
    flue_gas_flow_kmol_h: float
    co2_mol_pct: float
    is_upset: bool = False


class SyntheticPlant:
    """
    Produces a daily load curve for flue gas flow rate (mimicking demand
    ramps, e.g. morning/evening peaks) plus slow CO2 concentration drift and
    high-frequency sensor-like noise on top of both signals. Occasionally
    injects a short-lived "upset" (a CO2 slug or a flow surge) so a rolling
    anomaly check downstream has real events to catch, not just noise.
    """

    def __init__(
        self,
        base_flow_kmol_h: float = 5000.0,
        base_co2_mol_pct: float = 13.0,
        flow_noise_std: float = 60.0,
        co2_noise_std: float = 0.15,
        upset_probability: float = 0.03,
        seed: int | None = None,
    ):
        self.base_flow_kmol_h = base_flow_kmol_h
        self.base_co2_mol_pct = base_co2_mol_pct
        self.flow_noise_std = flow_noise_std
        self.co2_noise_std = co2_noise_std
        self.upset_probability = upset_probability
        self._rng = np.random.default_rng(seed)
        self._upset_steps_remaining = 0
        self._upset_co2_bump = 0.0
        self._upset_flow_bump = 0.0

    def _daily_load_factor(self, hour_of_day: float) -> float:
        """
        Two peaks (morning + evening) roughly mimicking a grid load curve,
        normalized to oscillate around 1.0.
        """
        morning_peak = 0.08 * np.exp(-0.5 * ((hour_of_day - 8.0) / 2.5) ** 2)
        evening_peak = 0.10 * np.exp(-0.5 * ((hour_of_day - 19.0) / 2.5) ** 2)
        night_dip = -0.06 * np.exp(-0.5 * ((hour_of_day - 3.0) / 3.0) ** 2)
        return 1.0 + morning_peak + evening_peak + night_dip

    def _maybe_trigger_upset(self) -> None:
        if self._upset_steps_remaining > 0:
            return
        if self._rng.random() < self.upset_probability:
            self._upset_steps_remaining = int(self._rng.integers(2, 6))
            # Either a CO2 slug (feed composition swing) or a flow surge,
            # not both, to keep each upset event physically legible.
            if self._rng.random() < 0.5:
                self._upset_co2_bump = float(self._rng.uniform(2.5, 4.5)) * self._rng.choice([-1, 1])
                self._upset_flow_bump = 0.0
            else:
                self._upset_co2_bump = 0.0
                self._upset_flow_bump = self.base_flow_kmol_h * float(self._rng.uniform(0.12, 0.20))

    def sample(self, timestamp_h: float) -> PlantSnapshot:
        self._maybe_trigger_upset()
        is_upset = self._upset_steps_remaining > 0

        hour_of_day = timestamp_h % 24.0
        load_factor = self._daily_load_factor(hour_of_day)

        flow = self.base_flow_kmol_h * load_factor
        flow += self._rng.normal(0.0, self.flow_noise_std)
        flow += self._upset_flow_bump

        # Slow drift in CO2 concentration tied loosely to load (higher load,
        # slightly leaner combustion mix in this toy model) plus noise.
        co2_drift = -0.4 * (load_factor - 1.0) * 10.0
        co2_pct = self.base_co2_mol_pct + co2_drift + self._rng.normal(0.0, self.co2_noise_std)
        co2_pct += self._upset_co2_bump
        co2_pct = float(np.clip(co2_pct, 6.0, 20.0))

        if self._upset_steps_remaining > 0:
            self._upset_steps_remaining -= 1
            if self._upset_steps_remaining == 0:
                self._upset_co2_bump = 0.0
                self._upset_flow_bump = 0.0

        return PlantSnapshot(
            timestamp_h=timestamp_h,
            flue_gas_flow_kmol_h=max(flow, 0.0),
            co2_mol_pct=co2_pct,
            is_upset=is_upset,
        )

    def generate_series(self, hours: float = 24.0, step_h: float = 0.25) -> list[PlantSnapshot]:
        n_steps = int(hours / step_h)
        return [self.sample(i * step_h) for i in range(n_steps)]
