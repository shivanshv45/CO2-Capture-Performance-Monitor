"""
Rolling-statistics anomaly check for the monitoring dashboard.

This is deliberately NOT machine learning and NOT predictive. It is a
rolling mean/standard deviation z-score check plus a couple of static
guardrails, described accurately here and in the README as a threshold and
control-chart style anomaly flag, not fault detection or a digital twin.

The z-score approach is a step up from a single fixed threshold because it
adapts to the current operating window instead of firing on every normal
load swing, which is closer to how a real basic plant alarm/control chart
would behave (e.g. a Shewhart-style 3-sigma rule), while still being fully
transparent and explainable.
"""

from dataclasses import dataclass

import numpy as np

Z_SCORE_ALARM_THRESHOLD = 3.0
MIN_WINDOW_FOR_ZSCORE = 8


@dataclass
class AnomalyFlag:
    message: str
    severity: str  # "warning" or "alarm"


def rolling_zscore_flags(values: list[float], label: str, window: int = 20) -> list[AnomalyFlag]:
    """
    Computes a z-score for the latest value against the trailing window
    (excluding the latest point itself) and flags it if it sits outside a
    3-sigma band, the standard control-chart rule of thumb for "this point
    is not just normal process noise."
    """
    if len(values) < MIN_WINDOW_FOR_ZSCORE + 1:
        return []

    history = values[-(window + 1):-1] if len(values) > window else values[:-1]
    if len(history) < MIN_WINDOW_FOR_ZSCORE:
        return []

    mean = float(np.mean(history))
    std = float(np.std(history))
    latest = values[-1]

    if std < 1e-9:
        # A perfectly flat history has no basis for a statistical z-score;
        # fall back to flagging any nonzero deviation as an outright break
        # from a previously constant signal.
        if abs(latest - mean) > 1e-9:
            return [AnomalyFlag(message=f"{label} deviated from a previously flat baseline", severity="alarm")]
        return []

    z = (latest - mean) / std

    if abs(z) >= Z_SCORE_ALARM_THRESHOLD:
        direction = "above" if z > 0 else "below"
        return [
            AnomalyFlag(
                message=f"{label} is {abs(z):.1f} sigma {direction} its recent rolling average",
                severity="alarm",
            )
        ]
    return []


def static_guardrail_flags(
    capture_rate: float,
    reboiler_duty_gj_per_ton: float,
    capture_rate_min: float = 0.85,
    reboiler_duty_max: float = 4.2,
) -> list[AnomalyFlag]:
    flags = []
    if capture_rate < capture_rate_min:
        flags.append(
            AnomalyFlag(
                message=f"Capture rate {capture_rate*100:.1f}% is below the {capture_rate_min*100:.0f}% target floor",
                severity="warning",
            )
        )
    if reboiler_duty_gj_per_ton > reboiler_duty_max:
        flags.append(
            AnomalyFlag(
                message=f"Reboiler duty {reboiler_duty_gj_per_ton:.2f} GJ/ton is above the normal operating ceiling",
                severity="warning",
            )
        )
    return flags
