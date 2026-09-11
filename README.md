# CO2 Capture Process Model + Monitoring Dashboard

A small Python project that models a simplified amine (MEA) CO2 capture unit
and shows the results on a live dashboard, like a very stripped down version
of what a plant monitoring screen might look like.

I built this to dig into the process engineering side of carbon capture
(mostly for a CCUS-related internship application) without needing access to
Aspen Plus or any real plant data. Everything here is open source Python and
everything on the dashboard is synthetic data, there is no real plant or
proprietary information involved anywhere.

## What it actually does

There's a process model for a 30 wt% MEA absorber/stripper loop. You give it
a flue gas flow rate, CO2 percentage, amine concentration, lean loading, and
a target capture rate, and it spits out the solvent circulation rate,
reboiler duty, and rich loading. Then there's a rough cost module that turns
that into a $/ton CO2 avoided number, and a synthetic data generator that
fakes a fluctuating flue gas feed over a 24 hour period so the dashboard has
something to show live instead of a single static number.

The dashboard is Streamlit, it has two tabs:

- **Live Monitor**: advances the synthetic feed step by step and shows the
  KPIs trending over time, plus a couple of threshold flags (like "capture
  rate dropped below target").
- **Scenario Explorer**: sliders for amine concentration, capture rate target,
  and flue gas composition so you can see the classic trade-off play out,
  push capture rate up and reboiler duty (and cost) go up with it.

## Why correlations instead of a real simulator

Building an actual rate-based packed column model is a multi month exercise
and needs proprietary correlations most of the time anyway. Instead I used
published numbers from open MEA literature (mainly the Rochelle group's work
out of UT Austin on reboiler duty ranges, roughly 2.5 to 4 GJ per ton CO2
captured for conventional 30 wt% MEA) and built simplified but physically
reasonable relationships around those benchmarks. The full breakdown of what
correlations were used and where the numbers came from is in
[methodology.md](methodology.md).

This is not a bankable techno-economic study and it's not a rigorous process
simulation. It's scoped to be a believable, defensible approximation that
gets the trends right, not the fourth decimal place.

## Running it

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

That opens the dashboard in your browser. If you just want to poke at the
model directly:

```python
from co2_capture.process_model import ProcessInputs, run_process_model
from co2_capture.techno_economics import run_techno_economics

inputs = ProcessInputs(flue_gas_flow_kmol_h=5000, co2_mol_pct=13.0)
process_result = run_process_model(inputs)
cost_result = run_techno_economics(process_result)

print(process_result)
print(cost_result)
```

## Running the tests

```bash
pip install pytest
pytest tests/
```

The tests mostly check that the numbers stay in a physically sane range
(reboiler duty landing in the published 2.5-4.5 GJ/ton band, cost per ton
staying positive and in a reasonable ballpark, capture rate trade-offs going
the right direction) rather than checking exact values, since this is an
approximation, not a validated simulator.

## Project layout

```
co2_capture/
  process_model.py     absorber/stripper model (Module A)
  techno_economics.py  cost per ton CO2 avoided (Module B)
  synthetic_plant.py   fake flue gas data stream (Module C)
dashboard.py           Streamlit app (Modules D and E)
tests/                 sanity checks against published ranges
methodology.md         assumptions, sources, and limitations
```

## Limitations, said plainly

- No real rate-based mass transfer model, this is correlation based.
- No physical pilot unit and no real plant data anywhere.
- Cost numbers are order of magnitude illustrations, not vendor quotes.
- The dashboard's "flag" logic is a plain threshold check. It is not machine
  learning and I'm not going to pretend it's fault detection or a digital
  twin.

More detail on assumptions and what I'd build next with more time is in
[methodology.md](methodology.md).
