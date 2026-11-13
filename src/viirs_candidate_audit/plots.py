"""Static, question-focused figures for the empirical audit."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .metrics import weight_label


def _finish(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_sensitivity(
    observations: pd.DataFrame,
    events: pd.DataFrame,
    weights: Iterable[float],
    path: str | Path,
) -> None:
    weights = list(map(float, weights))
    event_medians = []
    pooled = []
    for weight in weights:
        label = weight_label(weight)
        event_medians.append(events[f"sample_sum_ratio_gain_w_{label}"].median())
        baseline = observations["known_baseline_frp"].sum(min_count=1)
        power = observations[f"p_w_{label}"].sum(min_count=1)
        pooled.append((power - baseline) / baseline if baseline > 0 else np.nan)

    fig, axis = plt.subplots(figsize=(7.2, 4.6))
    axis.plot(weights, np.array(event_medians) * 100, marker="o", label="Median event")
    axis.plot(weights, np.array(pooled) * 100, marker="s", label="Sample-sum ratio")
    axis.axhline(0, color="#888888", linewidth=0.8)
    axis.set(
        xlabel="Candidate-pixel sensitivity weight (w)",
        ylabel="Relative change from known-pixel baseline (%)",
        title="Candidate inclusion sensitivity",
    )
    axis.legend(frameon=False)
    axis.grid(axis="y", alpha=0.25)
    _finish(fig, Path(path))


def plot_strata(strata: pd.DataFrame, path: str | Path) -> None:
    dimensions = ["daynight", "satellite_normalized", "vza_bin"]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2))
    for axis, dimension in zip(axes, dimensions, strict=True):
        part = strata[strata["dimension"].eq(dimension)].copy()
        axis.bar(
            part["stratum"],
            part["sample_sum_ratio_gain_w_1"] * 100,
            color="#D55E00",
            alpha=0.85,
        )
        axis.set_title({"daynight": "Day/night", "satellite_normalized": "Satellite", "vza_bin": "|VZA| bin"}[dimension])
        axis.set_ylabel("Relative change (%)")
        axis.tick_params(axis="x", rotation=35)
        axis.grid(axis="y", alpha=0.2)
        for index, row in part.reset_index(drop=True).iterrows():
            axis.text(index, 0, f"n={int(row['observation_groups']):,}", rotation=90, va="bottom", ha="center", fontsize=7)
    fig.suptitle("Candidate inclusion at w=1 by observation condition")
    fig.tight_layout()
    _finish(fig, Path(path))


def plot_retrieval_effect(events: pd.DataFrame, path: str | Path) -> None:
    part = events.loc[
        events["retrieval_relative_change"].notna()
        & events["sample_sum_ratio_gain_w_1"].notna(),
        [
            "fireid",
            "sample_sum_ratio_gain_w_1",
            "retrieval_relative_change",
            "retrieval_coverage",
        ],
    ]
    fig, axis = plt.subplots(figsize=(7.2, 4.6))
    axis.scatter(
        part["sample_sum_ratio_gain_w_1"] * 100,
        part["retrieval_relative_change"] * 100,
        s=28,
        alpha=0.65,
        color="#0072B2",
    )
    axis.axvline(0, color="#777777", linewidth=0.8)
    axis.axhline(0, color="#777777", linewidth=0.8)
    coverage_min = part["retrieval_coverage"].min()
    coverage_max = part["retrieval_coverage"].max()
    axis.text(
        0.98,
        0.04,
        f"Matched known-pixel coverage: {coverage_min:.0%}–{coverage_max:.0%}",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
    )
    axis.set(
        xlabel="Candidate inclusion effect at w=1 (%)",
        ylabel="Recalculated vs original known-pixel FRP (%)",
        title="Event-level separation of inclusion and retrieval effects",
    )
    axis.grid(alpha=0.2)
    _finish(fig, Path(path))


def select_map_cases(
    frame: pd.DataFrame,
    events: pd.DataFrame,
    count: int = 3,
    min_pixels: int = 100,
    min_frp_completeness: float = 0.95,
) -> pd.DataFrame:
    profile = frame.groupby("fireid").agg(
        rows=("fireid", "size"),
        frp_completeness=("frp_analysis", lambda values: values.notna().mean()),
        candidate_share=("classification_status", lambda values: values.eq("candidate").mean()),
    )
    profile = profile.join(
        events.set_index("fireid")[["sample_sum_ratio_gain_w_1", "name"]], how="left"
    )
    eligible = profile[
        profile["rows"].ge(min_pixels)
        & profile["frp_completeness"].ge(min_frp_completeness)
        & profile["candidate_share"].between(0, 1, inclusive="neither")
    ].copy()
    if eligible.empty:
        return pd.DataFrame(
            columns=["fireid", "selection_rule", "rows", "frp_completeness", "candidate_share"]
        )

    selections: list[tuple[str, str]] = []
    ordered_rules = [
        ("largest_complete_event", eligible.sort_values(["rows", "fireid"], ascending=[False, True])),
        (
            "highest_candidate_share_among_complete",
            eligible.sort_values(["candidate_share", "fireid"], ascending=[False, True]),
        ),
        (
            "smallest_candidate_frp_effect_among_complete",
            eligible.sort_values(["sample_sum_ratio_gain_w_1", "fireid"], ascending=[True, True]),
        ),
    ]
    for rule, ordered in ordered_rules:
        for fireid in ordered.index:
            if fireid not in {selected for selected, _ in selections}:
                selections.append((fireid, rule))
                break
        if len(selections) >= count:
            break
    selected = profile.loc[[fireid for fireid, _ in selections]].reset_index()
    selected["selection_rule"] = [rule for _, rule in selections]
    return selected


def plot_map_cases(frame: pd.DataFrame, cases: pd.DataFrame, path: str | Path) -> None:
    if cases.empty:
        return
    fig, axes = plt.subplots(1, len(cases), figsize=(5 * len(cases), 4.5), squeeze=False)
    for axis, (_, case) in zip(axes[0], cases.iterrows(), strict=True):
        part = frame[frame["fireid"].eq(case["fireid"])]
        known = part[part["classification_status"].eq("known")]
        candidate = part[part["classification_status"].eq("candidate")]
        axis.scatter(known["longitude"], known["latitude"], s=4, alpha=0.35, label="Known", color="#0072B2")
        axis.scatter(candidate["longitude"], candidate["latitude"], s=5, alpha=0.35, label="Candidate", color="#D55E00")
        display_name = case["name"] if pd.notna(case.get("name")) else case["fireid"]
        axis.set_title(f"{display_name}\n{case['selection_rule'].replace('_', ' ')}", fontsize=9)
        axis.set_xlabel("Longitude")
        axis.set_ylabel("Latitude")
        axis.set_aspect("equal", adjustable="datalim")
    axes[0][0].legend(frameon=False, markerscale=2)
    fig.suptitle("Pre-specified complete-event map cases")
    fig.tight_layout()
    _finish(fig, Path(path))
