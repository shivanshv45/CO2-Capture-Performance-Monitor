# Methodology and Assumptions

## What this model does and does not do

This is a correlation and mass-balance based approximation of a 30 wt% MEA
post-combustion CO2 capture unit, built to reproduce the right order of
magnitude and the right qualitative trade-offs, not a rigorous rate-based
absorber/stripper design. No licensed process simulator was used. No real
plant data was used anywhere, all flue gas inputs are synthetically
generated.

## Process model (Module A)

**Mass balance.** CO2 captured is set directly from a target capture rate
applied to the incoming CO2 molar flow.

**Vapor-liquid equilibrium.** Rich loading is not assumed, it is solved for.
The model implements a simplified two-parameter Kent-Eisenberg style
relation:

```
ln(P*_CO2 [kPa]) = A - B/T[K] + C * loading + D * loading^2
```

which gives the equilibrium CO2 partial pressure above an aqueous MEA
solution as a function of loading and temperature. This form is a well
known simplification of the real Kent-Eisenberg framework (Kent, R.L. and
Eisenberg, B., "Better Data for Amine Treating", Hydrocarbon Processing,
1976), which itself treats the amine-CO2-H2O system as a set of chemical
equilibria rather than requiring full activity coefficient thermodynamics.
The coefficients here were fitted by hand to reproduce two qualitative
anchors from published 30 wt% MEA VLE behavior: a low equilibrium pressure
at a typical lean loading of 0.20 (so the absorber can pick up CO2 easily),
and a pressure near the flue gas CO2 partial pressure around a loading of
0.42 to 0.45 (the practical rich loading ceiling widely cited for 30 wt%
MEA before corrosion and degradation concerns dominate). The rich loading
in the absorber is then found by locating where the equilibrium pressure at
absorber temperature equals the actual flue gas CO2 partial pressure (the
thermodynamic pinch point at the bottom of the column), then pulling back
from that ideal maximum with an 85% approach factor, since a real column
does not fully reach equilibrium at any single stage.

**Solvent circulation.** Backed out from the absorber CO2 mass balance:
moles of CO2 absorbed equals moles of MEA circulated times the loading
swing (rich minus lean).

**Reboiler duty.** Instead of one lumped correlation, duty is built up from
its three standard physical components, the same breakdown used in
Freeman and Rochelle's published work out of the UT Austin Texas Carbon
Management Program:

1. *Sensible heat* - heating circulating solvent across the unrecovered
   approach temperature left by the lean/rich cross-exchanger (assumed 10 C
   here), scaled by how much solvent must circulate per ton of CO2, which
   depends on the loading swing.
2. *Heat of desorption* - the energy to break the CO2-amine bond, taken as
   a near-fixed 1.86 GJ/ton CO2 for 30 wt% MEA (roughly 82 kJ/mol CO2, a
   commonly cited figure for this system).
3. *Stripping steam* - steam used to strip CO2 out of solution in the
   stripper. This is the dominant term and the one that actually drives the
   classic trade-offs: it rises sharply as lean loading is pushed down
   (deeper regeneration needs proportionally more steam per ton of CO2
   handled) and rises further as target capture rate is pushed up (a
   tighter capture spec needs a leaner solvent to hit the required driving
   force at the top of the absorber).

At the reference case (30 wt% MEA, 90% capture, 0.20 lean loading, 5000
kmol/h flue gas at 13% CO2), this reproduces a total reboiler duty of about
3.5 GJ/ton CO2, inside the commonly cited 2.5 to 4.0 GJ/ton range for
conventional 30 wt% MEA. One side effect of building duty up this way
instead of assuming a fixed number: the model shows a real minimum in duty
around a lean loading of 0.25 to 0.30 rather than a monotonic curve, which
matches the qualitative shape reported in the literature for the same
reason, too lean wastes stripping steam, too rich strains the absorber
approach and needs more solvent circulated.

MEA concentration also carries a small penalty above 35 wt%, representing
the corrosion and degradation-driven derating that is the commonly cited
reason plants do not simply run ever more concentrated amine to cut
circulation costs.

## Techno-economics (Module B)

Capex is broken into five major equipment line items rather than a single
lumped multiplier: absorber column, stripper column, reboiler, lean/rich
cross-exchanger, and circulation pumps/auxiliaries. Each is scaled from a
reference-case cost using a power-law "six-tenths rule" style exponent
against the relevant sizing variable (flue gas flow for the absorber,
solvent circulation rate for the stripper/exchanger/pumps, total reboiler
duty for the reboiler), which is a standard preliminary chemical process
cost estimation technique (see Peters, Timmerhaus and West, "Plant Design
and Economics for Chemical Engineers"). Indirect costs (installation,
piping, instrumentation, engineering, contingency) are added as a Lang
factor multiplier on total direct equipment cost.

Reference-case equipment costs are illustrative anchors, not vendor quotes,
chosen so the baseline scenario's resulting $/ton CO2 avoided lands inside
the range commonly cited in IEAGHG and NETL techno-economic studies for
MEA-based post-combustion capture retrofits (roughly $50-100/ton CO2
avoided for large-scale applications). The baseline case in this project
comes out to about $80-90/ton. Opex is simpler: a fixed O&M fraction of
capex plus a steam cost driven directly by the process model's reboiler
duty.

A tornado-style sensitivity function swings each key process input (target
capture rate, lean loading, MEA concentration, flue gas flow) +/- 15% around
a scenario and reports the resulting cost range, showing which design lever
the plant economics are actually most sensitive to.

This is explicitly not a bankable techno-economic study. No vendor quotes,
no detailed equipment sizing calculations beyond the power-law scaling, no
financing structure beyond a flat 20-year amortization.

## Synthetic data (Module C)

Flue gas flow rate follows a two-peak daily load curve (morning and evening,
loosely mimicking grid demand) with Gaussian noise layered on top. CO2
concentration drifts slightly with load and carries its own independent
noise term. The generator also occasionally injects a short transient
upset, either a CO2 slug or a flow surge lasting a few timesteps, so the
dashboard's anomaly checks have real events to catch rather than only
ordinary noise. All parameters are tunable in the dashboard.

## Monitoring and anomaly detection (Module D)

The Live Monitor tab combines two kinds of checks, both described honestly
as non-predictive:

- Static guardrails: capture rate below 85%, reboiler duty above 4.2
  GJ/ton.
- Rolling z-score checks: each KPI's latest value is compared against the
  mean and standard deviation of its own trailing window, and flagged if it
  sits more than 3 standard deviations away, a standard Shewhart-style
  control-chart rule. This adapts to the current operating window instead
  of firing on every normal load swing, but it is still a statistical
  threshold, not a trained model, and it is described that way throughout
  the app.

## Known limitations

- No rigorous stage-by-stage VLE solve, no packed column hydraulics, no
  heat exchanger network optimization. The Kent-Eisenberg style relation
  used here is simplified and hand-fitted to two qualitative anchors, not
  fitted to a full published dataset.
- Cost correlations are power-law scaled from illustrative reference
  anchors, not bottom-up equipment sizing from vendor data.
- The anomaly checks are rolling statistics and static thresholds. They are
  not machine learning and should not be described as fault detection or a
  digital twin.
- Single amine system (MEA) only, no blended or advanced solvent
  chemistries.

## What I would add with more time

- A rate-based absorber model with real mass transfer correlations (HTU/NTU
  or a proper rigorous stage-by-stage solve) instead of the simplified
  equilibrium pinch approach.
- Weather-linked flue gas variability instead of a synthetic sinusoidal load
  curve.
- A genuinely predictive layer (e.g. a simple regression or anomaly
  detection model trained on the synthetic history) instead of rolling
  statistics and static thresholds.
- Deployment to Streamlit Community Cloud for a live link instead of a
  local-only demo.
