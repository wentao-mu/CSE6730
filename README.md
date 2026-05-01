# Pressing, Fatigue, and Chance Creation Simulator

This project is a discrete-event football simulation for studying how pressing
intensity and fatigue affect chance creation, shot quality, and scoring
outcomes. A match is represented as a sequence of possession-level events:
teams retain possession, turn the ball over, create shots, accumulate fatigue,
and score goals through a zone-based expected goals model.

The simulator is designed as a reproducible modeling project rather than a
full professional football analytics system. It focuses on interpretable
mechanisms: pressing changes turnover pressure, fatigue reduces effective
pressing and attacking quality, and chance creation is measured through shots,
xG, possession, goals, and fatigue-related metrics.

## Project Structure

```text
.
├── app.py                         # Streamlit dashboard for experiment results
├── config/default_params.yaml     # Shared model parameters
├── notebooks/                     # Exploratory analysis notebooks
├── output/                        # Generated experiment CSVs and plots
├── scripts/
│   ├── calibrate.py               # Build calibrated transition matrix from data
│   ├── fetch_statsbomb.py         # Fetch StatsBomb open data
│   ├── plot_results.py            # Generate static experiment plots
│   └── run_experiment.py          # Run batch simulation experiments
├── src/
│   ├── chance_model.py            # Zone-based xG and shot-quality adjustment
│   ├── engine.py                  # Main simulation loop
│   ├── fatigue.py                 # Fatigue accumulation and penalty functions
│   ├── match_state.py             # Match state representation
│   ├── pressing.py                # Pressing and recovery modifiers
│   ├── teams.py                   # Team state, fatigue, and effective pressing
│   └── transitions.py             # Default and calibrated transition logic
└── tests/                         # Unit tests
```

## Model Summary

Each simulated match runs for a fixed number of discrete steps, currently 90 by
default. Each step represents a possession event or short possession sequence.
The model tracks:

- Team in possession
- Field zone
- Match clock
- Score
- Team fatigue
- Pressing level
- Event log

Pressing levels are configured as `low`, `medium`, and `high`. Higher pressing
can increase defensive disruption, but it also accumulates fatigue faster.
Fatigue reduces effective pressing and can reduce attacking execution and shot
quality.

Shot quality is estimated through a coarse zone-based xG model:

- Defensive zone shots have low xG
- Midfield/middle-zone shots have moderate xG
- Attacking-zone shots have higher xG

The simulator can run with the default transition model or with a calibrated
transition matrix from local StatsBomb-derived calibration output.

## Installation

Create a virtual environment if desired, then install dependencies:

```bash
pip install -r requirements.txt
```

Required packages include:

- pandas
- matplotlib
- plotly
- PyYAML
- pytest
- requests
- streamlit

## Running Tests

Run the full test suite from the project root:

```bash
python -m pytest
```

Expected current result:

```text
20 passed
```

## Running Experiments

Run 100 simulated matches with the default medium-vs-medium pressing setup:

```bash
python scripts/run_experiment.py --n 100
```

Run 500 matches with a specific pressing matchup:

```bash
python scripts/run_experiment.py --n 500 --home-press high --away-press low -o output/hl.csv
```

Run the main pressing sweep used for current result exploration:

```bash
python scripts/run_experiment.py --n 300 --sweep-press -o output/pressing_sweep.csv
```

This runs 300 matches for each home pressing level:

- Home low press vs away medium press
- Home medium press vs away medium press
- Home high press vs away medium press

The output CSV contains one row per simulated match, including:

- Goals
- Shots
- xG
- Possession share
- Final fatigue
- Average fatigue
- Effective pressing
- Pressing settings
- Run index

## Plotting Results

Generate static plots from an experiment CSV:

```bash
python scripts/plot_results.py -i output/pressing_sweep.csv -o output/plots --no-show
```

Generated plots include:

- xG by pressing intensity
- Shot comparison by pressing intensity
- Possession by pressing intensity
- xG distribution

## Dashboard

Launch the interactive dashboard:

```bash
streamlit run app.py
```

The dashboard automatically scans `output/` for CSV files and lets the user
select available experiment results. It dynamically detects metric columns and
factor columns, so it can still run if a CSV is missing optional fields.

Dashboard sections include:

- Research overview
- Experiment controls
- Results summary
- Comparative visualizations
- Event-level inspection
- Reproducibility notes

The dashboard is intended as an academic companion interface for exploring how
pressing and fatigue affect chance creation.

## Data and Calibration

The current experiment CSVs in `output/` are simulator-generated results. They
are not raw real-match data. The default experiment command uses the simulator's
default transition model unless `--use-calibrated` is explicitly passed.

StatsBomb open data can be fetched and processed locally:

```bash
python scripts/fetch_statsbomb.py
python scripts/calibrate.py
```

Calibrated transitions are expected at:

```text
data/calibration/transitions.json
```

The `data/` directory is intentionally ignored by git because raw and processed
data can be large or machine-specific. If `data/calibration/transitions.json`
is missing, the dashboard can still browse existing CSV outputs, but calibrated
experiment runs should not be used until the calibration file is generated.

To run experiments with calibrated transitions:

```bash
python scripts/run_experiment.py --n 300 --sweep-press --use-calibrated -o output/calibrated_pressing_sweep.csv
```

## Reproducing Current Results

From a clean environment with dependencies installed:

```bash
python -m pytest
python scripts/run_experiment.py --n 300 --sweep-press -o output/pressing_sweep.csv
python scripts/plot_results.py -i output/pressing_sweep.csv -o output/plots --no-show
streamlit run app.py
```

The regenerated `output/pressing_sweep.csv` should contain 900 rows: 300
simulated matches for each home pressing level.

## Notes

- Results are stochastic but reproducible within the current script because each
  run uses the run index as the random seed.
- Goals are reported as match-level counts in each CSV row. Grouped tables in
  plots or reports usually show mean goals per match, which can be fractional.
- The current model is intentionally coarse. It is useful for comparing tactical
  mechanisms, but absolute shot and xG rates should be interpreted as model
  outputs rather than direct estimates from professional match data.
