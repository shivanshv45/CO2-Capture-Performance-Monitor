# PRD — CO2 Capture Process Model & Digital Monitoring Dashboard
**Type:** Personal/academic software project (chemical engineering + software)
**Target use:** Technip Energies internship application (CCUS domain)
**Status:** Draft v1

---

## 1. Overview
A pure-software project that models a simplified amine-based (MEA) post-combustion CO2 capture unit using open literature correlations, generates a synthetic fluctuating flue-gas feed to mimic real plant variability, and displays the results on a live monitoring dashboard tracking key performance indicators (CO2 capture rate, reboiler energy penalty, solvent loading, rough cost per ton CO2 avoided).

No licensed process simulator and no physical equipment are used — the process model, the synthetic data stream, and the dashboard are all built in open-source Python.

## 2. Why this is relevant
CCUS is one of Technip Energies' explicitly stated growth areas — carbon capture is built into several of its current major awards (e.g. large Middle East LNG projects with integrated carbon capture, standalone CCS project awards, and low-carbon hydrogen projects). The company also repeatedly emphasizes digital/asset-performance offerings. This project directly touches both: a real CO2 capture process and a live-monitoring software layer.

## 3. Goals
- Model the core process trade-off in amine CO2 capture: capture rate vs. reboiler energy penalty vs. solvent circulation rate.
- Translate that into a rough techno-economic figure (cost per ton CO2 avoided) so the project isn't purely technical — it also shows commercial awareness.
- Present it as a live "plant monitoring" dashboard rather than a static report, to show the digitalization angle.

## 4. Non-goals / Out of scope
- No licensed simulators (Aspen Plus, ProMax, etc.) — Python only, using published correlations/simplified models instead of rigorous rate-based mass transfer.
- No physical pilot unit, no proprietary/confidential plant data.
- Not attempting a full rate-based packed-column design (that's a multi-month industrial engineering exercise) — an equilibrium-stage or correlation-based approximation is the right scope for this timeframe.
- Cost figures are illustrative/order-of-magnitude, not a bankable techno-economic study — this should be stated explicitly, not implied otherwise.

## 5. Users
- **Primary:** You (portfolio piece / interview talking point).
- **Secondary:** Interviewer/recruiter viewing a live or recorded dashboard demo.

## 6. Tech stack
| Layer | Tool | Why |
|---|---|---|
| VLE / thermo (CO2-MEA-H2O) | `thermo`/`chemicals`, or published correlations (e.g. from open literature on MEA loading vs. partial pressure) | Avoids needing a licensed simulator; well-documented open correlations exist for this system |
| Process math | `NumPy` / `SciPy` | Mass/energy balances across absorber & stripper |
| Techno-economics | Custom module using published cost correlations (e.g. $/ton CO2 avoided vs. capture rate) | Adds a commercial dimension |
| Synthetic "plant" data | Custom time-series generator | Simulates flue gas flow rate/composition drifting over time |
| Dashboard | `Streamlit` or `Plotly Dash` | Live KPI visualization, updates as synthetic stream advances |
| Version control | GitHub repo, README, write-up | What you link on your resume |

## 7. Functional modules

**Module A — Absorber/stripper process model**
- Inputs: flue gas flow rate & CO2 mole %, MEA concentration (wt%), lean solvent loading, target capture rate.
- Logic: equilibrium/correlation-based estimate of required solvent circulation rate and stripper reboiler duty to hit the target capture rate, using published CO2-MEA equilibrium and energy-of-regeneration data.
- Output: CO2 captured (%), reboiler duty (GJ/ton CO2 captured), lean/rich loading, solvent circulation rate.

**Module B — Techno-economics**
- Applies simple published cost correlations to Module A's outputs.
- Output: rough capex/opex proxy and $/ton CO2 avoided, plus a sensitivity view (e.g. cost vs. capture rate, energy penalty vs. amine concentration).

**Module C — Synthetic plant data stream**
- Generates a time series of flue gas flow rate and CO2 concentration with realistic drift/noise (e.g. simulating load variation over a day).
- Feeds each timestep through Module A to produce a continuous KPI stream — the "live plant" data.

**Module D — Monitoring dashboard**
- Displays live-updating charts: CO2 capture rate, reboiler duty, lean/rich loading, $/ton CO2 avoided, as the synthetic stream advances.
- Basic threshold-based flag (e.g. "capture rate below target" or "energy penalty above X") to demonstrate an anomaly-alert concept, without claiming true fault-detection ML (keep this simple and honestly scoped).

**Module E — Sensitivity/scenario explorer**
- Sliders/inputs to change amine concentration, target capture rate, or flue gas composition, and see the recalculated KPIs and cost — this is the "process design" story for interview purposes.

## 8. Data strategy
All flue-gas and process data is synthetically generated (Module C) using realistic ranges informed by public literature — never presented as real plant or confidential data. State this explicitly in the README.

## 9. Suggested timeline
| Week | Milestone |
|---|---|
| 1 | Build Module A (process model), sanity-check against published MEA capture benchmarks (~2.5–4 GJ/ton CO2 typical reboiler duty range) |
| 2 | Build Module B (techno-economics) + Module E (scenario explorer) |
| 3 | Build Module C (synthetic data stream) + Module D (dashboard) |
| 4 | Polish README, write a 1-page methodology & assumptions summary, record a short demo |

## 10. Success metrics
- Process model outputs land in a physically reasonable range vs. published MEA capture literature values.
- Dashboard updates live and clearly shows KPI trends as synthetic conditions change.
- Scenario explorer visibly demonstrates the classic trade-off: higher capture rate → higher energy penalty/cost.
- README clearly states all assumptions and the synthetic nature of the data (this matters for credibility in interviews).

## 11. Assumptions & risks
- **Assumption:** Correlation-based (not rigorous rate-based) modeling is an acceptable, clearly-labeled simplification for this scope.
- **Risk:** Published correlations for MEA systems vary by source — pick one credible reference and cite it consistently rather than mixing sources.
- **Risk:** Over-claiming "digital twin" or "fault detection" language without real ML behind it can backfire if probed in interview — keep the anomaly flag simple and describe it accurately as threshold-based, not predictive, unless you actually build a predictive layer.

## 12. Deliverables
1. Public GitHub repo (README, install instructions, sample plots).
2. One-page methodology write-up (PDF) — process assumptions, correlations used, and limitations.
3. Dashboard (Streamlit Community Cloud link if deployed).
4. Resume bullet + a short verbal explanation for interview.

## 13. Interview talking points (for later)
- Why amine-based capture has an inherent energy penalty and how that trade-off is managed.
- Why you chose correlation-based modeling over full rate-based simulation given time constraints — shows scoping judgment.
- What you'd add with more time (e.g. rigorous rate-based absorber model, real weather-linked flue gas variability, an actual predictive maintenance layer).