# CO2 Capture Process Model + Monitoring Dashboard

A Python project that models a simplified amine (MEA) CO2 capture unit and
shows the results on a live monitoring dashboard, like a stripped down
version of what a plant monitoring screen might actually look like.

I built this to dig into the process engineering side of carbon capture for
a CCUS-related internship application, without needing access to Aspen Plus
or any real plant data. Everything here is open source Python, and every
number on the dashboard comes from a synthetic data generator, not a real
plant.

## What's in it

**Process model**
- Solves for rich loading with a Kent-Eisenberg style vapor-liquid
  equilibrium relation instead of assuming a fixed number.
- Backs out solvent circulation rate from an absorber mass balance.
- Builds reboiler duty from its three real physical components: sensible
  heat, heat of desorption, and stripping steam.

**Techno-economics**
- Breaks capex into equipment line items (absorber, stripper, reboiler,
  cross exchanger, pumps), each scaled with power-law cost exponents.
- Rolls everything up into a $/ton CO2 avoided figure.
- Runs a tornado-style sensitivity to show which input the cost actually
  moves the most with.

**Synthetic plant feed**
- Generates a 24 hour flue gas load curve with drift and noise.
- Injects occasional upset events (a CO2 slug, a flow surge) so the
  dashboard has real events to react to, not just a flat line.

**Dashboard** (Streamlit, three tabs)

| Tab | What's on it |
|---|---|
| Live Monitor | Gauges, a process schematic, rolling KPI trends, and anomaly flags from a rolling z-score check plus static guardrails |
| Scenario Explorer | Sliders for amine concentration, capture rate, and flue gas composition, with the duty breakdown, capex breakdown, trade-off curves, and tornado chart updating live |
| Assumptions | A short summary of the approach behind the model |

## Screenshots

**Live Monitor**, gauges and the process schematic updating as the synthetic
feed advances:

![Live monitor tab](docs/screenshots/live_monitor.png)

**Scenario Explorer**, reboiler duty and capex broken into their real
components:

![Scenario explorer top](docs/screenshots/scenario_explorer_top.png)

Same tab scrolled down, the capture-rate trade-off curves and the tornado
sensitivity chart:

![Scenario explorer sensitivity](docs/screenshots/scenario_explorer_sensitivity.png)

## Why correlations instead of a full simulator

A rate-based packed column model needs proprietary correlations most
simulator vendors don't publish. So instead of black-boxing that with a
licensed tool, I used published relationships from open MEA literature and
built physically grounded versions of them myself:

- The Kent-Eisenberg equilibrium framework for CO2 partial pressure over
  loaded amine solution.
- Freeman and Rochelle's (UT Austin) breakdown of reboiler duty into
  sensible heat, heat of reaction, and stripping steam.
- Standard power-law ("six-tenths rule") equipment cost scaling for the
  capex side.

The result gets the mechanisms and trends right and lands in the ranges
published literature reports for 30 wt% MEA systems.

## Running it

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

That opens the dashboard in your browser. To poke at the model directly:

```python
from co2_capture.process_model import ProcessInputs, run_process_model
from co2_capture.techno_economics import run_techno_economics

inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
process_result = run_process_model(inputs)
cost_result = run_techno_economics(process_result)

print(process_result)
print(cost_result)
```

## Tests

```bash
pip install pytest
pytest tests/
```

17 tests, covering:

- The equilibrium relation's shape (pressure rises with loading and
  temperature).
- The reboiler duty component breakdown.
- Mass balance consistency.
- The capex line items summing correctly.
- The tornado sensitivity output.
- The anomaly detection logic.

A GitHub Actions workflow runs the suite on every push.

## Project layout

```
co2_capture/
  process_model.py     Kent-Eisenberg equilibrium + reboiler duty breakdown
  techno_economics.py  equipment-level capex, cost per ton, tornado sensitivity
  synthetic_plant.py   flue gas stream with load curve and upset events
  anomaly.py           rolling z-score and static guardrail checks
dashboard.py           Streamlit app, live monitor + scenario explorer
tests/                 sanity checks against published ranges and internal consistency
```
