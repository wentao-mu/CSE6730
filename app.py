"""Academic Streamlit dashboard for soccer simulation experiment outputs."""

from __future__ import annotations

import copy
import math
import random
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CALIBRATED_TRANSITIONS_PATH = PROJECT_ROOT / "data" / "calibration" / "transitions.json"
ACADEMIC_COLORS = ["#334155", "#64748b", "#0f766e", "#b45309", "#7f1d1d", "#4338ca"]
PRESSING_ORDER = ["low", "medium", "high"]
PRESSING_COLORS = {
    "low": "#64748b",
    "medium": "#0f766e",
    "high": "#b45309",
}

METRIC_KEYWORDS = {
    "goals": ("goal", "goals"),
    "xg": ("xg", "expected_goal"),
    "shots": ("shot", "shots"),
    "possession": ("possession", "poss"),
    "turnovers": ("turnover",),
    "recoveries": ("recovery", "recoveries"),
    "fatigue": ("fatigue",),
    "shot_quality": ("shot_quality", "quality"),
    "effective_pressing": ("effective_press", "pressing_effect"),
}

FACTOR_HINTS = (
    "press",
    "pressing",
    "fatigue",
    "scenario",
    "setting",
    "model",
    "team",
    "zone",
)

EVENT_HINTS = ("event", "event_type", "type", "minute", "team", "zone")


def find_output_csvs(output_dir: Path | str = OUTPUT_DIR) -> list[Path]:
    """Return sorted CSV files available under output/."""
    path = Path(output_dir)
    if not path.exists():
        return []
    return sorted(item for item in path.rglob("*.csv") if item.is_file())


def load_results_csv(path: Path | str) -> pd.DataFrame:
    """Load a result CSV and return an empty DataFrame for empty files."""
    csv_path = Path(path)
    try:
        return pd.read_csv(csv_path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def load_selected_results(csv_paths: Iterable[Path], selected_label: str) -> tuple[pd.DataFrame, list[Path]]:
    """Load either one CSV or a combined view of all output CSVs."""
    paths = list(csv_paths)
    if selected_label == "All output CSVs":
        frames = []
        for path in paths:
            frame = load_results_csv(path)
            if not frame.empty:
                frame = frame.copy()
                frame["source_file"] = path.name
            frames.append(frame)
        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return combined, paths

    selected_path = next(path for path in paths if display_path(path) == selected_label)
    frame = load_results_csv(selected_path)
    if not frame.empty:
        frame = frame.copy()
        frame["source_file"] = selected_path.name
    return frame, [selected_path]


def display_path(path: Path) -> str:
    """Display a path relative to the project root when possible."""
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return numeric columns in source order."""
    return list(df.select_dtypes(include="number").columns)


def detect_metric_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    """Detect known metric families from actual numeric column names."""
    numeric = numeric_columns(df)
    detected: dict[str, list[str]] = {}
    for family, keywords in METRIC_KEYWORDS.items():
        matches = [
            column
            for column in numeric
            if any(keyword in column.lower() for keyword in keywords)
        ]
        if matches:
            detected[family] = matches
    return detected


def metric_options(df: pd.DataFrame) -> list[str]:
    """Return numeric metric options with recognized metrics first."""
    detected = detect_metric_columns(df)
    ordered: list[str] = []
    for family in ("xg", "shots", "goals", "possession", "turnovers", "recoveries", "fatigue"):
        ordered.extend(detected.get(family, []))
    ordered.extend(column for column in numeric_columns(df) if column not in ordered)
    return ordered


def detect_factor_columns(df: pd.DataFrame, max_unique: int = 30) -> list[str]:
    """Detect columns suitable for grouping or filtering."""
    if df.empty:
        return []

    factors: list[str] = []
    for column in df.columns:
        unique_count = df[column].dropna().nunique()
        lower = column.lower()
        hinted = any(hint in lower for hint in FACTOR_HINTS)
        categorical = not pd.api.types.is_numeric_dtype(df[column])
        low_cardinality = 1 < unique_count <= max_unique
        if low_cardinality and (categorical or hinted):
            factors.append(column)

    return sorted(
        factors,
        key=lambda name: (not any(hint in name.lower() for hint in FACTOR_HINTS), name.lower()),
    )


def summarize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Build mean/std/min/max summary for numeric columns."""
    cols = numeric_columns(df)
    if not cols:
        return pd.DataFrame(columns=["metric", "mean", "std", "min", "max"])

    summary = df[cols].agg(["mean", "std", "min", "max"]).T.reset_index()
    summary = summary.rename(columns={"index": "metric"})
    return summary


def available_experimental_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Return detected factors with observed levels."""
    rows = []
    for column in detect_factor_columns(df):
        values = sorted(str(value) for value in df[column].dropna().unique())
        rows.append(
            {
                "factor": column,
                "levels": ", ".join(values[:12]),
                "n_levels": len(values),
            }
        )
    return pd.DataFrame(rows)


def grouped_metric_summary(df: pd.DataFrame, metric: str, factor: str) -> pd.DataFrame:
    """Summarize a metric by a factor with standard error."""
    grouped = (
        df.dropna(subset=[metric])
        .groupby(factor, dropna=False)[metric]
        .agg(["count", "mean", "std", "min", "max"])
        .reset_index()
    )
    grouped["sem"] = grouped.apply(
        lambda row: 0.0 if row["count"] <= 1 or pd.isna(row["std"]) else row["std"] / math.sqrt(row["count"]),
        axis=1,
    )
    grouped["ci95"] = grouped["sem"] * 1.96
    grouped = sort_grouped_summary(grouped, factor)
    return grouped


def sort_grouped_summary(summary: pd.DataFrame, factor: str) -> pd.DataFrame:
    """Sort common factor levels in a consistent research-friendly order."""
    values = summary[factor].astype(str).str.lower()
    if set(values).issubset(set(PRESSING_ORDER)):
        order = {name: index for index, name in enumerate(PRESSING_ORDER)}
        return summary.assign(_order=values.map(order)).sort_values("_order").drop(columns="_order")
    return summary.sort_values(factor, key=lambda series: series.astype(str))


def detect_event_level_columns(df: pd.DataFrame) -> list[str]:
    """Return columns that suggest event-level records."""
    return [column for column in df.columns if any(hint == column.lower() or hint in column.lower() for hint in EVENT_HINTS)]


def apply_filters(df: pd.DataFrame, selected_filters: dict[str, list]) -> pd.DataFrame:
    """Apply sidebar filters without assuming particular column names."""
    filtered = df.copy()
    for column, values in selected_filters.items():
        if values:
            filtered = filtered[filtered[column].isin(values)]
    return filtered


def plot_metric_by_factor(df: pd.DataFrame, metric: str, factor: str | None, chart_type: str):
    """Create a Plotly chart for a metric using the selected grouping."""
    import plotly.express as px
    import plotly.graph_objects as go

    clean = df.dropna(subset=[metric]).copy()
    if clean.empty:
        return None

    axis_title = labelize(metric)
    if not factor:
        clean = clean.reset_index(names="row_index")
        if chart_type == "scatter plot":
            return px.scatter(clean, x="row_index", y=metric, title=f"{axis_title} by row", color_discrete_sequence=ACADEMIC_COLORS)
        if chart_type == "line chart":
            return px.line(clean, x="row_index", y=metric, title=f"{axis_title} by row", color_discrete_sequence=ACADEMIC_COLORS)
        return px.histogram(clean, x=metric, title=f"Distribution of {axis_title}", marginal="box", color_discrete_sequence=ACADEMIC_COLORS)

    if chart_type == "box plot":
        return px.box(
            clean,
            x=factor,
            y=metric,
            points="outliers",
            title=f"{axis_title} by {labelize(factor)}",
            color=factor,
            category_orders={factor: PRESSING_ORDER},
            color_discrete_map=PRESSING_COLORS,
            color_discrete_sequence=ACADEMIC_COLORS,
        )

    if chart_type == "scatter plot":
        x_axis = "run" if "run" in clean.columns else factor
        return px.scatter(
            clean,
            x=x_axis,
            y=metric,
            color=factor,
            title=f"{axis_title} by {labelize(factor)}",
            category_orders={factor: PRESSING_ORDER},
            color_discrete_map=PRESSING_COLORS,
            color_discrete_sequence=ACADEMIC_COLORS,
            opacity=0.68,
        )

    summary = grouped_metric_summary(clean, metric, factor)
    if chart_type == "line chart":
        return px.line(
            summary,
            x=factor,
            y="mean",
            markers=True,
            error_y="sem",
            title=f"Mean {axis_title} by {labelize(factor)}",
            color_discrete_sequence=ACADEMIC_COLORS,
        )

    figure = go.Figure()
    colors = [PRESSING_COLORS.get(str(value).lower(), ACADEMIC_COLORS[index % len(ACADEMIC_COLORS)]) for index, value in enumerate(summary[factor])]
    figure.add_bar(
        x=summary[factor].astype(str),
        y=summary["mean"],
        error_y={"type": "data", "array": summary["sem"], "visible": True},
        marker_color=colors,
        marker_line={"color": "#1f2937", "width": 0.6},
        hovertemplate=(
            f"{labelize(factor)}=%{{x}}<br>"
            f"Mean {axis_title}=%{{y:.3f}}<br>"
            "SEM=%{customdata[0]:.3f}<br>"
            "n=%{customdata[1]}<extra></extra>"
        ),
        customdata=summary[["sem", "count"]],
    )
    figure.update_layout(title=f"Mean {axis_title} by {labelize(factor)}", xaxis_title=labelize(factor), yaxis_title=axis_title)
    return figure


def plot_distribution(df: pd.DataFrame, metric: str, factor: str | None = None):
    """Plot a distribution for a metric, optionally grouped by factor."""
    import plotly.express as px

    clean = df.dropna(subset=[metric]).copy()
    if clean.empty:
        return None
    return px.histogram(
        clean,
        x=metric,
        color=factor if factor in clean.columns else None,
        marginal="box",
        barmode="overlay",
        opacity=0.62,
        title=f"Distribution of {labelize(metric)}",
        category_orders={factor: PRESSING_ORDER} if factor else None,
        color_discrete_map=PRESSING_COLORS,
        color_discrete_sequence=ACADEMIC_COLORS,
    )


def plot_metric_pair(df: pd.DataFrame, left_metric: str, right_metric: str, factor: str | None):
    """Plot two related aggregate metrics by factor."""
    import plotly.graph_objects as go

    if not factor:
        factor = "source_file" if "source_file" in df.columns else None
    if not factor:
        return None

    clean = df.dropna(subset=[left_metric, right_metric]).copy()
    if clean.empty:
        return None

    left = grouped_metric_summary(clean, left_metric, factor)
    right = grouped_metric_summary(clean, right_metric, factor)

    figure = go.Figure()
    figure.add_bar(name=labelize(left_metric), x=left[factor].astype(str), y=left["mean"], marker_color="#334155")
    figure.add_bar(name=labelize(right_metric), x=right[factor].astype(str), y=right["mean"], marker_color="#94a3b8")
    figure.update_layout(
        barmode="group",
        title=f"{labelize(left_metric)} and {labelize(right_metric)} by {labelize(factor)}",
        xaxis_title=labelize(factor),
        yaxis_title="Mean per simulated match",
    )
    return figure


def plot_fatigue_effect(df: pd.DataFrame, fatigue_column: str, outcome_column: str, factor: str | None):
    """Plot fatigue against an outcome when enough columns are present."""
    import plotly.express as px

    clean = df.dropna(subset=[fatigue_column, outcome_column]).copy()
    if clean.empty:
        return None

    if pd.api.types.is_numeric_dtype(clean[fatigue_column]):
        return px.scatter(
            clean,
            x=fatigue_column,
            y=outcome_column,
            color=factor if factor in clean.columns else None,
            title=f"{labelize(outcome_column)} versus {labelize(fatigue_column)}",
        )

    return plot_metric_by_factor(clean, outcome_column, fatigue_column, "bar chart with error bars")


def labelize(column: str) -> str:
    """Readable label for snake_case columns."""
    return column.replace("_", " ").strip().title()


def metric_family_columns(metrics: dict[str, list[str]], family: str) -> list[str]:
    return metrics.get(family, [])


def first_existing_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def get_git_commit() -> str:
    """Return current commit hash when git is available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
            text=True,
        )
    except Exception:
        return "unavailable"
    return result.stdout.strip()


def summarize_match_state(state, config=None) -> dict:
    """Convert MatchState output into one aggregate result row."""
    home_shots = 0
    away_shots = 0
    home_xg = 0.0
    away_xg = 0.0
    possession_samples = 0
    home_possession_samples = 0
    fatigue_samples = []

    for event in state.event_log:
        possession = event.get("possession")
        if possession in (0, 1):
            possession_samples += 1
            if possession == 0:
                home_possession_samples += 1

        fatigue = event.get("fatigue")
        if isinstance(fatigue, list) and len(fatigue) >= 2:
            fatigue_samples.append(fatigue)

        if event.get("type") != "shot":
            continue

        team_index = event.get("team", possession)
        if team_index == 0:
            home_shots += 1
            home_xg += float(event.get("xg", 0.0) or 0.0)
        elif team_index == 1:
            away_shots += 1
            away_xg += float(event.get("xg", 0.0) or 0.0)

    home_possession = home_possession_samples / possession_samples if possession_samples else 0.5
    home_avg_fatigue = (
        sum(sample[0] for sample in fatigue_samples) / len(fatigue_samples)
        if fatigue_samples
        else state.teams[0].fatigue
    )
    away_avg_fatigue = (
        sum(sample[1] for sample in fatigue_samples) / len(fatigue_samples)
        if fatigue_samples
        else state.teams[1].fatigue
    )
    summary = {
        "home_goals": state.score[0],
        "away_goals": state.score[1],
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_xg": home_xg,
        "away_xg": away_xg,
        "home_possession": home_possession,
        "home_final_fatigue": state.teams[0].fatigue,
        "away_final_fatigue": state.teams[1].fatigue,
        "home_avg_fatigue": home_avg_fatigue,
        "away_avg_fatigue": away_avg_fatigue,
    }

    if config is not None:
        summary.update(
            {
                "home_effective_pressing": state.teams[0].effective_pressing(config),
                "away_effective_pressing": state.teams[1].effective_pressing(config),
            }
        )

    return summary


def run_small_experiment(
    n_matches: int,
    home_pressing: str,
    away_pressing: str,
    fatigue_model: str,
    seed: int,
    output_path: Path,
    use_calibrated: bool = False,
) -> pd.DataFrame:
    """Run a small experiment on demand without overwriting existing outputs."""
    if use_calibrated and not CALIBRATED_TRANSITIONS_PATH.exists():
        raise FileNotFoundError(
            f"Calibrated transition matrix not found at {display_path(CALIBRATED_TRANSITIONS_PATH)}"
        )

    from src.engine import load_config, run_match

    transition_callback = None
    if use_calibrated:
        from src.transitions import build_transition_function, load_transition_matrix

        transition_callback = build_transition_function(load_transition_matrix(CALIBRATED_TRANSITIONS_PATH))

    base_config = load_config()
    rows = []
    for index in range(n_matches):
        config = copy.deepcopy(base_config)
        config.setdefault("teams", {}).setdefault("team1", {})["pressing_level"] = home_pressing
        config.setdefault("teams", {}).setdefault("team2", {})["pressing_level"] = away_pressing
        config.setdefault("fatigue", {})["model"] = fatigue_model
        state = run_match(
            config=config,
            rng=random.Random(seed + index),
            transition_callback=transition_callback,
        )
        summary = summarize_match_state(state, config=config)
        summary.update(
            {
                "run": index,
                "seed": seed + index,
                "home_pressing": home_pressing,
                "away_pressing": away_pressing,
                "fatigue_model": fatigue_model,
            }
        )
        rows.append(summary)

    frame = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return frame


def configure_plotly_figure(figure):
    """Apply a restrained academic chart style."""
    if figure is None:
        return None
    figure.update_layout(
        template="simple_white",
        font={"family": "Arial, sans-serif", "size": 13, "color": "#1f2933"},
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 52, "r": 28, "t": 70, "b": 54},
        legend_title_text="",
        title={"font": {"size": 18}, "x": 0.02, "xanchor": "left"},
        hovermode="closest",
    )
    figure.update_xaxes(showgrid=False, zeroline=False, linecolor="#d1d5db", ticks="outside", tickfont={"size": 12})
    figure.update_yaxes(showgrid=True, gridcolor="#edf0f2", zeroline=False, linecolor="#d1d5db", ticks="outside", tickfont={"size": 12})
    return figure


def render_static_table(st, frame: pd.DataFrame, max_rows: int = 100) -> None:
    """Render a small table without Streamlit's Arrow dataframe path."""
    if frame.empty:
        st.caption("No rows available.")
        return

    display_frame = frame.head(max_rows).copy()
    st.markdown(
        display_frame.to_html(index=False, border=0, classes="academic-table"),
        unsafe_allow_html=True,
    )
    if len(frame) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(frame):,} rows.")


def render_app() -> None:
    """Render the Streamlit dashboard."""
    import streamlit as st

    st.set_page_config(
        page_title="Pressing, Fatigue, and Chance Creation",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
        h1, h2, h3 { color: #111827; }
        div[data-testid="stMetric"] { background: #ffffff; border: 1px solid #e5e7eb; padding: 0.75rem 1rem; }
        section[data-testid="stSidebar"] { background: #fafafa; border-right: 1px solid #e5e7eb; }
        table.academic-table { width: 100%; border-collapse: collapse; font-size: 0.92rem; }
        table.academic-table th, table.academic-table td { border-bottom: 1px solid #e5e7eb; padding: 0.48rem 0.55rem; text-align: left; }
        table.academic-table th { color: #4b5563; font-weight: 700; background: #fafafa; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Pressing, Fatigue, and Chance Creation in a Discrete-Event Football Simulator")

    st.header("Research Overview")
    st.info(
        "Research question: How do pressing intensity and fatigue jointly affect chance creation, "
        "shot quality, and scoring outcomes in a discrete-event football simulation?"
    )

    notes_left, notes_right = st.columns([1.2, 1])
    with notes_left:
        st.markdown(
            """
            **Model notes**

            - Discrete-event match simulation, where each step approximates a possession or match event.
            - Zone-based transitions model progression, turnovers, shots, and retained possession.
            - Pressing affects turnover and recovery likelihood through fatigue-adjusted modifiers.
            - Fatigue attenuates effective pressing and shot quality over time.
            - Zone-based xG estimates goal probability for generated shots.
            """
        )
    with notes_right:
        calibrated_status = "available" if CALIBRATED_TRANSITIONS_PATH.exists() else "not found"
        st.markdown(
            f"""
            **Current data status**

            - Output directory: `{display_path(OUTPUT_DIR)}`
            - Calibrated transition matrix: `{calibrated_status}`
            - Git commit: `{get_git_commit()}`
            """
        )

    csv_paths = find_output_csvs()
    if not csv_paths:
        st.warning(
            "No CSV files were found under output/. Run `python scripts/run_experiment.py` "
            "and reload this dashboard."
        )
        render_reproducibility_notes(st, pd.DataFrame(), [], [])
        return

    st.sidebar.header("Experiment Controls")
    labels = ["All output CSVs"] + [display_path(path) for path in csv_paths]
    default_label = next((label for label in labels if "pressing_sweep" in label), labels[0])
    selected_label = st.sidebar.selectbox("CSV file", labels, index=labels.index(default_label))
    raw_df, selected_paths = load_selected_results(csv_paths, selected_label)

    if raw_df.empty:
        st.warning("The selected CSV is empty. Choose another file or rerun the experiment.")
        render_reproducibility_notes(st, raw_df, selected_paths, [])
        return

    factor_columns = detect_factor_columns(raw_df)
    metric_columns = metric_options(raw_df)
    detected_metrics = detect_metric_columns(raw_df)

    filter_columns = [column for column in factor_columns if raw_df[column].dropna().nunique() <= 20]
    filters: dict[str, list] = {}
    with st.sidebar.expander("Optional filters", expanded=False):
        if not filter_columns:
            st.caption("No low-cardinality factor columns were detected for filtering.")
        for column in filter_columns:
            values = sorted(raw_df[column].dropna().unique(), key=str)
            filters[column] = st.multiselect(labelize(column), values)

    df = apply_filters(raw_df, filters)
    if df.empty:
        st.warning("The current filters removed all rows. Clear one or more filters to continue.")
        render_reproducibility_notes(st, df, selected_paths, list(raw_df.columns))
        return

    default_factor_index = 0
    if "home_pressing" in factor_columns:
        default_factor_index = factor_columns.index("home_pressing") + 1
    selected_factor = st.sidebar.selectbox("Grouping variable", ["None"] + factor_columns, index=default_factor_index)
    selected_factor = None if selected_factor == "None" else selected_factor

    if metric_columns:
        default_metric = first_existing_column(df, ["home_xg", "away_xg", "home_shots", "home_goals"]) or metric_columns[0]
        metric_index = metric_columns.index(default_metric) if default_metric in metric_columns else 0
        selected_metric = st.sidebar.selectbox("Metric", metric_columns, index=metric_index, format_func=labelize)
    else:
        selected_metric = None
        st.sidebar.caption("No numeric metric columns detected.")

    chart_type = st.sidebar.selectbox(
        "Chart type",
        ["bar chart with error bars", "box plot", "line chart", "scatter plot"],
    )

    st.sidebar.divider()
    render_small_experiment_controls(st)

    st.header("Results Summary")
    render_results_summary(st, df, detected_metrics, factor_columns)

    st.header("Comparative Visualizations")
    st.caption(
        "Bars report group means with standard error. Box plots show match-to-match dispersion. "
        "Scatter plots preserve individual simulated matches."
    )
    if selected_metric:
        figure = plot_metric_by_factor(df, selected_metric, selected_factor, chart_type)
        if figure is not None:
            st.plotly_chart(configure_plotly_figure(figure), use_container_width=True)
        else:
            st.caption("The selected metric has no valid numeric rows after filtering.")
    else:
        st.caption("No numeric metrics are available for comparative visualization.")

    render_core_metric_sections(st, df, detected_metrics, selected_factor)

    st.header("Event-Level Inspection")
    render_event_level_inspection(st, df)

    st.header("Reproducibility Notes")
    render_reproducibility_notes(st, df, selected_paths, list(raw_df.columns))


def render_results_summary(st, df: pd.DataFrame, detected_metrics: dict[str, list[str]], factor_columns: list[str]) -> None:
    """Render high-level metrics and summary tables."""
    metric_cols = detect_metric_columns(df)
    xg_col = first_existing_column(df, metric_cols.get("xg", []))
    shots_col = first_existing_column(df, metric_cols.get("shots", []))
    goals_col = first_existing_column(df, metric_cols.get("goals", []))
    possession_col = first_existing_column(df, metric_cols.get("possession", []))

    columns = st.columns(4)
    columns[0].metric("Rows / simulated matches", f"{len(df):,}")
    columns[1].metric("Mean xG", f"{df[xg_col].mean():.3f}" if xg_col else "N/A")
    columns[2].metric("Mean shots", f"{df[shots_col].mean():.2f}" if shots_col else "N/A")
    columns[3].metric("Mean possession", f"{df[possession_col].mean() * 100:.1f}%" if possession_col else "N/A")

    available = {key: ", ".join(value) for key, value in detected_metrics.items()}
    if available:
        st.markdown("**Available metric families:** " + "; ".join(f"`{key}`: {value}" for key, value in available.items()))
    else:
        st.caption("No recognized metric families were detected, but numeric columns may still be available.")

    table_left, table_right = st.columns([1.3, 1])
    with table_left:
        st.subheader("Numeric metrics")
        render_static_table(st, summarize_numeric_columns(df))
    with table_right:
        st.subheader("Experimental factors")
        factors = available_experimental_factors(df)
        if factors.empty:
            st.caption("No experimental factor columns were detected.")
        else:
            render_static_table(st, factors)


def render_core_metric_sections(st, df: pd.DataFrame, metrics: dict[str, list[str]], factor: str | None) -> None:
    """Render domain-specific chart sections with graceful degradation."""
    st.subheader("xG distribution")
    xg_cols = metric_family_columns(metrics, "xg")
    if xg_cols:
        xg_choice = st.selectbox("xG metric", xg_cols, key="xg_metric", format_func=labelize)
        st.plotly_chart(configure_plotly_figure(plot_distribution(df, xg_choice, factor)), use_container_width=True)
        if factor:
            render_static_table(st, grouped_metric_summary(df, xg_choice, factor))
    else:
        st.caption("No xG-related numeric column was detected, so xG distribution is skipped.")

    st.subheader("Shots and goals comparison")
    shot_cols = metric_family_columns(metrics, "shots")
    goal_cols = metric_family_columns(metrics, "goals")
    if shot_cols or goal_cols:
        chart_cols = st.columns(2)
        with chart_cols[0]:
            if shot_cols:
                shot_col = st.selectbox("Shots metric", shot_cols, key="shots_metric", format_func=labelize)
                st.plotly_chart(configure_plotly_figure(plot_metric_by_factor(df, shot_col, factor, "bar chart with error bars")), use_container_width=True)
            else:
                st.caption("No shots column was detected.")
        with chart_cols[1]:
            if goal_cols:
                goal_col = st.selectbox("Goals metric", goal_cols, key="goals_metric", format_func=labelize)
                st.plotly_chart(configure_plotly_figure(plot_metric_by_factor(df, goal_col, factor, "bar chart with error bars")), use_container_width=True)
            else:
                st.caption("No goals column was detected.")

        conversion = build_conversion_proxy(df, goal_cols, shot_cols)
        if conversion is not None:
            st.plotly_chart(configure_plotly_figure(plot_metric_by_factor(conversion, "conversion_proxy", factor, "bar chart with error bars")), use_container_width=True)
    else:
        st.caption("No shots or goals columns were detected, so this section is skipped.")

    st.subheader("Possession / territory / event outcomes")
    possession_cols = metric_family_columns(metrics, "possession")
    turnover_cols = metric_family_columns(metrics, "turnovers")
    recovery_cols = metric_family_columns(metrics, "recoveries")
    zone_cols = [column for column in df.columns if "zone" in column.lower()]
    if possession_cols:
        st.plotly_chart(configure_plotly_figure(plot_metric_by_factor(df, possession_cols[0], factor, "bar chart with error bars")), use_container_width=True)
    elif turnover_cols or recovery_cols:
        left = turnover_cols[0] if turnover_cols else None
        right = recovery_cols[0] if recovery_cols else None
        if left and right:
            st.plotly_chart(configure_plotly_figure(plot_metric_pair(df, left, right, factor)), use_container_width=True)
        else:
            metric = left or right
            st.plotly_chart(configure_plotly_figure(plot_metric_by_factor(df, metric, factor, "bar chart with error bars")), use_container_width=True)
    elif zone_cols and factor:
        render_static_table(st, pd.crosstab(df[factor], df[zone_cols[0]], normalize="index"))
    else:
        st.caption("No possession, turnover, recovery, or zone columns were detected in the selected CSV.")

    st.subheader("Fatigue effect")
    fatigue_cols = metric_family_columns(metrics, "fatigue") + [column for column in df.columns if "fatigue" in column.lower()]
    fatigue_cols = list(dict.fromkeys(fatigue_cols))
    xg_or_quality = metric_family_columns(metrics, "xg") + metric_family_columns(metrics, "shot_quality")
    if fatigue_cols and xg_or_quality:
        fatigue_col = st.selectbox("Fatigue variable", fatigue_cols, key="fatigue_col", format_func=labelize)
        outcome_col = st.selectbox("Fatigue outcome", xg_or_quality, key="fatigue_outcome", format_func=labelize)
        figure = plot_fatigue_effect(df, fatigue_col, outcome_col, factor)
        if figure is not None:
            st.plotly_chart(configure_plotly_figure(figure), use_container_width=True)
        else:
            st.caption("No valid fatigue/outcome rows were available after filtering.")
    else:
        st.caption("Fatigue-specific analysis is skipped because fatigue and outcome columns are not both present.")


def build_conversion_proxy(df: pd.DataFrame, goal_cols: list[str], shot_cols: list[str]) -> pd.DataFrame | None:
    """Create a goals-per-shot proxy when compatible columns are present."""
    if not goal_cols or not shot_cols:
        return None
    goal_col = first_existing_column(df, ["home_goals", "away_goals"]) or goal_cols[0]
    shot_col = first_existing_column(df, ["home_shots", "away_shots"]) or shot_cols[0]
    if shot_col not in df.columns or goal_col not in df.columns:
        return None
    conversion = df.copy()
    conversion["conversion_proxy"] = conversion.apply(
        lambda row: 0.0 if float(row.get(shot_col, 0.0) or 0.0) == 0 else float(row.get(goal_col, 0.0) or 0.0) / float(row.get(shot_col, 0.0)),
        axis=1,
    )
    return conversion


def render_event_level_inspection(st, df: pd.DataFrame) -> None:
    """Render event rows when the CSV appears event-level."""
    event_cols = detect_event_level_columns(df)
    event_type_col = first_existing_column(df, ["event_type", "type", "event"])
    minute_col = first_existing_column(df, ["minute", "time"])
    if event_type_col or minute_col:
        run_col = first_existing_column(df, ["run", "match_id", "match"])
        inspect_df = df
        if run_col:
            run_values = sorted(df[run_col].dropna().unique(), key=str)
            selected_run = st.selectbox("Select match/run", run_values, key="event_run")
            inspect_df = df[df[run_col] == selected_run]
        preferred = [column for column in ["minute", "time", "team", "event_type", "type", "zone", "xg", "goal", "possession"] if column in inspect_df.columns]
        remaining = [column for column in event_cols if column not in preferred]
        render_static_table(st, inspect_df[preferred + remaining], max_rows=100)
    else:
        st.caption(
            "Current CSV appears to contain aggregate experiment results only. "
            "Event-level inspection requires saving event logs from the engine."
        )


def render_reproducibility_notes(st, df: pd.DataFrame, selected_paths: list[Path], detected_columns: list[str]) -> None:
    """Render reproducibility information for the selected result set."""
    path_text = ", ".join(display_path(path) for path in selected_paths) if selected_paths else "none"
    columns_text = ", ".join(detected_columns) if detected_columns else "none"
    calibrated_note = (
        "available"
        if CALIBRATED_TRANSITIONS_PATH.exists()
        else "not found; run calibration before using calibrated transitions"
    )
    st.markdown(
        f"""
        - Selected CSV path(s): `{path_text}`
        - Number of rows after filtering: `{len(df):,}`
        - Detected columns: `{columns_text}`
        - Current git commit: `{get_git_commit()}`
        - Calibrated transition file: `{display_path(CALIBRATED_TRANSITIONS_PATH)}` ({calibrated_note})
        - Rerun experiments: `python scripts/run_experiment.py --n 100 -o output/experiment_results.csv`
        - Calibrated mode requires: `data/calibration/transitions.json`
        """
    )


def render_small_experiment_controls(st) -> None:
    """Render optional small-run controls in the sidebar."""
    with st.sidebar.expander("Run small experiment", expanded=False):
        st.caption("Runs are optional and intentionally small by default.")
        n_matches = st.number_input("Matches", min_value=1, max_value=50, value=10, step=1)
        home_pressing = st.selectbox("Home pressing", ["low", "medium", "high"], index=1, key="run_home_press")
        away_pressing = st.selectbox("Away pressing", ["low", "medium", "high"], index=1, key="run_away_press")
        fatigue_model = st.selectbox("Fatigue model", ["linear", "threshold"], key="run_fatigue")
        seed = st.number_input("Random seed", min_value=0, max_value=1000000, value=2026, step=1)
        calibrated_available = CALIBRATED_TRANSITIONS_PATH.exists()
        use_calibrated = st.checkbox(
            "Use calibrated transitions",
            value=False,
            disabled=not calibrated_available,
            help="Requires data/calibration/transitions.json.",
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / "dashboard_runs" / f"small_experiment_{timestamp}.csv"
        st.code(f"Output: {display_path(output_path)}")
        if not calibrated_available:
            st.caption("Calibrated transition file not found. Default transition model will be used.")

        if st.button("Run small experiment"):
            try:
                with st.spinner("Running small experiment..."):
                    result = run_small_experiment(
                        int(n_matches),
                        home_pressing,
                        away_pressing,
                        fatigue_model,
                        int(seed),
                        output_path,
                        use_calibrated=use_calibrated,
                )
                st.success(f"Saved {len(result)} rows to {display_path(output_path)}")
                render_static_table(st, result)
            except Exception as exc:
                st.error(f"Experiment failed: {exc}")


if __name__ == "__main__":
    render_app()
