# Methodology and Assumptions

## What this model does and does not do

This is a correlation-based approximation of a 30 wt% MEA post-combustion CO2
capture unit, built to reproduce the right order of magnitude and the right
qualitative trade-offs, not a rigorous rate-based absorber/stripper design. No
licensed process simulator was used. No real plant data was used anywhere,
all flue gas inputs are synthetically generated.

## Process model (Module A)

- CO2 captured is set directly from a target capture rate applied to the
  incoming CO2 molar flow (a straightforward mass balance).
- Rich loading (mol CO2 / mol MEA in the rich solvent leaving the absorber)
  is estimated from a simplified monotonic function of lean loading and CO2
  partial pressure, shaped to follow the qualitative curvature of published
  CO2-MEA equilibrium data (Kent-Eisenberg type behavior: loading capacity
  rises with CO2 partial pressure and saturates near 0.5 mol/mol for 30 wt%
  MEA, which is roughly where industrial operators stop pushing loading due
  to corrosion and degradation concerns).
- Solvent circulation rate is backed out from the absorber CO2 mass balance:
  moles of CO2 absorbed equals moles of MEA circulated times the loading
  swing (rich minus lean).
- Reboiler duty is estimated from a baseline of 3.3 GJ/ton CO2 captured at a
  reference point (30 wt% MEA, 90% capture, 0.20 lean loading), which sits
  inside the commonly cited 2.5-4.0 GJ/ton range for conventional 30 wt% MEA
  reported in Rochelle group (UT Austin) pilot plant work. Duty increases as
  lean loading is driven down (deeper regeneration) and as target capture
  rate increases (more absorption driving force required), consistent with
  the direction reported in that literature.

## Techno-economics (Module B)

Capex is scaled from nameplate CO2 capture capacity (ton/day) using a rough
per-ton-capacity multiplier, amortized over 20 years. Opex is split into a
fixed O&M fraction of capex and a steam cost driven directly by reboiler
duty. None of the unit cost figures are vendor quotes, they were chosen so
the resulting $/ton CO2 avoided lands inside the range commonly cited in
IEAGHG and NETL techno-economic studies for MEA-based post-combustion
capture retrofits (roughly $50-100/ton CO2 avoided for large-scale
applications). This is explicitly an illustrative figure for showing the
shape of the cost curve, not a bankable estimate.

## Synthetic data (Module C)

Flue gas flow rate follows a two-peak daily load curve (morning and evening,
loosely mimicking grid demand) with Gaussian noise layered on top. CO2
concentration drifts slightly with load and carries its own independent
noise term. All parameters are tunable in the dashboard.

## Known limitations

- No rigorous vapor-liquid equilibrium model, no packed column hydraulics,
  no heat exchanger network optimization.
- Cost correlations are single-point illustrative multipliers, not bottom-up
  equipment sizing.
- The anomaly flag on the dashboard is a simple threshold check on capture
  rate and reboiler duty. It is not predictive and should not be described as
  fault detection or a digital twin.
- Single amine system (MEA) only, no blended or advanced solvent chemistries.

## What I would add with more time

- A rate-based absorber model with real mass transfer correlations (HTU/NTU
  or a proper rigorous stage-by-stage solve).
- Weather-linked flue gas variability instead of a synthetic sinusoidal load
  curve.
- A genuinely predictive layer (e.g. a simple regression or anomaly
  detection model trained on the synthetic history) instead of static
  thresholds.
