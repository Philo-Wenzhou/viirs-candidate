"""Sensitivity, retrieval, event, stratum, and uncertainty metrics."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .groupings import GROUP_KEYS, aggregate_observations, assign_observation_groups


def weight_label(weight: float) -> str:
    return str(float(weight)).rstrip("0").rstrip(".").replace(".", "_") or "0"


def add_candidate_sensitivity(
    observations: pd.DataFrame, weights: Iterable[float]
) -> pd.DataFrame:
    out = observations.copy()
    weights = tuple(float(weight) for weight in weights)
    if not weights or 0.0 not in weights:
        raise ValueError("candidate_weights must include 0")
    if any(weight < 0 or weight > 1 for weight in weights):
        raise ValueError("candidate_weights must be between 0 and 1")

    known = out["known_frp_sum"].where(out["known_count"] > 0, 0.0)
    candidate = out["candidate_frp_sum"].where(out["candidate_count"] > 0, 0.0)
    out["known_baseline_frp"] = known
    for weight in weights:
        label = weight_label(weight)
        if weight == 0:
            power = known
        else:
            power = known + weight * candidate
        out[f"p_w_{label}"] = power
        comparable = known.notna() & power.notna() & known.gt(0)
        out[f"gain_w_{label}"] = ((power - known) / known).where(comparable)

    out["candidate_only"] = out["known_count"].eq(0) & out["candidate_count"].gt(0)
    out["zero_known_baseline"] = known.eq(0)
    full_label = weight_label(1.0)
    if f"p_w_{full_label}" in out:
        denominator = out[f"p_w_{full_label}"]
        out["candidate_frp_share_w1"] = (candidate / denominator).where(denominator.gt(0))
    return out


def add_retrieval_effects(
    frame: pd.DataFrame, observations: pd.DataFrame, tolerance_minutes: int = 0
) -> pd.DataFrame:
    grouped_frame = assign_observation_groups(frame, tolerance_minutes)
    known = grouped_frame[grouped_frame["classification_status"].eq("known")].copy()
    known["matched"] = known["frp_analysis"].notna() & known["frp_old_analysis"].notna()
    matched = known[known["matched"]].copy()
    matched["retrieval_delta"] = matched["frp_analysis"] - matched["frp_old_analysis"]

    known_counts = known.groupby(GROUP_KEYS, dropna=False).size().rename("retrieval_known_count")
    if matched.empty:
        retrieval = known_counts.to_frame()
        retrieval["retrieval_matched_count"] = 0
        retrieval["retrieval_new_sum"] = np.nan
        retrieval["retrieval_old_sum"] = np.nan
        retrieval["retrieval_delta_sum"] = np.nan
    else:
        retrieval = matched.groupby(GROUP_KEYS, dropna=False).agg(
            retrieval_matched_count=("matched", "size"),
            retrieval_new_sum=("frp_analysis", lambda values: values.sum(min_count=1)),
            retrieval_old_sum=("frp_old_analysis", lambda values: values.sum(min_count=1)),
            retrieval_delta_sum=("retrieval_delta", lambda values: values.sum(min_count=1)),
        )
        retrieval = known_counts.to_frame().join(retrieval, how="left")
        retrieval["retrieval_matched_count"] = retrieval["retrieval_matched_count"].fillna(0).astype(int)
    retrieval["retrieval_coverage"] = (
        retrieval["retrieval_matched_count"] / retrieval["retrieval_known_count"].replace(0, np.nan)
    )
    retrieval["retrieval_relative_change"] = (
        retrieval["retrieval_delta_sum"] / retrieval["retrieval_old_sum"]
    ).where(retrieval["retrieval_old_sum"].gt(0))
    return observations.merge(retrieval.reset_index(), on=GROUP_KEYS, how="left")


def observation_metrics(
    frame: pd.DataFrame, weights: Iterable[float], tolerance_minutes: int = 0
) -> pd.DataFrame:
    observations = aggregate_observations(frame, tolerance_minutes)
    observations = add_candidate_sensitivity(observations, weights)
    return add_retrieval_effects(frame, observations, tolerance_minutes)


def event_metrics(
    frame: pd.DataFrame, observations: pd.DataFrame, weights: Iterable[float]
) -> pd.DataFrame:
    weights = tuple(float(weight) for weight in weights)
    names = (
        frame.groupby("fireid")["name"]
        .agg(lambda values: next((str(value) for value in values if pd.notna(value)), None))
        if "name" in frame
        else pd.Series(dtype="object")
    )
    grouped = observations.groupby("fireid", sort=True)
    events = grouped.agg(
        first_detection_utc=("observation_time_utc", "min"),
        last_detection_utc=("observation_time_utc", "max"),
        observation_groups=("observation_id", "nunique"),
        observed_pixel_rows=("observed_rows", "sum"),
        known_pixels=("known_count", "sum"),
        candidate_pixels=("candidate_count", "sum"),
        candidate_only_groups=("candidate_only", "sum"),
        mean_vza=("mean_vza", "mean"),
        retrieval_known_pixels=("retrieval_known_count", "sum"),
        retrieval_matched_pixels=("retrieval_matched_count", "sum"),
        retrieval_new_frp_sum=("retrieval_new_sum", "sum"),
        retrieval_old_frp_sum=("retrieval_old_sum", "sum"),
        retrieval_delta_frp_sum=("retrieval_delta_sum", "sum"),
        retrieval_delta_mean_by_observation=("retrieval_delta_sum", "mean"),
    )
    known_observations = observations[observations["known_count"].gt(0)].groupby("fireid")
    events["known_first_detection_utc"] = known_observations["observation_time_utc"].min()
    events["known_last_detection_utc"] = known_observations["observation_time_utc"].max()
    events["known_observation_groups"] = known_observations["observation_id"].nunique()
    events["observed_detection_span_hours"] = (
        events["last_detection_utc"] - events["first_detection_utc"]
    ).dt.total_seconds() / 3600
    events["known_detection_span_hours"] = (
        events["known_last_detection_utc"] - events["known_first_detection_utc"]
    ).dt.total_seconds() / 3600
    events["observed_span_extension_hours"] = (
        events["observed_detection_span_hours"] - events["known_detection_span_hours"]
    )
    events["first_detection_extension_hours"] = (
        events["known_first_detection_utc"] - events["first_detection_utc"]
    ).dt.total_seconds() / 3600
    events["last_detection_extension_hours"] = (
        events["last_detection_utc"] - events["known_last_detection_utc"]
    ).dt.total_seconds() / 3600
    events["candidate_pixel_share"] = events["candidate_pixels"] / (
        events["known_pixels"] + events["candidate_pixels"]
    ).replace(0, np.nan)
    events["retrieval_coverage"] = events["retrieval_matched_pixels"] / events[
        "retrieval_known_pixels"
    ].replace(0, np.nan)
    events["retrieval_relative_change"] = (
        events["retrieval_delta_frp_sum"] / events["retrieval_old_frp_sum"]
    ).where(events["retrieval_old_frp_sum"].gt(0))

    for weight in weights:
        label = weight_label(weight)
        power_col = f"p_w_{label}"
        gain_col = f"gain_w_{label}"
        events[f"mean_observation_frp_w_{label}"] = grouped[power_col].mean()
        events[f"median_relative_gain_w_{label}"] = grouped[gain_col].median()
        numerator = grouped[power_col].sum(min_count=1)
        denominator = grouped["known_baseline_frp"].sum(min_count=1)
        events[f"sample_sum_ratio_gain_w_{label}"] = ((numerator - denominator) / denominator).where(
            denominator.gt(0)
        )

    events.insert(0, "name", names.reindex(events.index))
    return events.reset_index()


def _summarize_stratum(part: pd.DataFrame, dimension: str) -> pd.DataFrame:
    rows = []
    for value, group in part.groupby(dimension, dropna=False, observed=True):
        baseline = group["known_baseline_frp"]
        full = group["p_w_1"]
        denominator = baseline.sum(min_count=1)
        rows.append(
            {
                "dimension": dimension,
                "stratum": str(value),
                "observation_groups": len(group),
                "fire_events": group["fireid"].nunique(),
                "observed_pixel_rows": int(group["observed_rows"].sum()),
                "comparable_gain_groups": int(group["gain_w_1"].notna().sum()),
                "median_relative_gain_w_1": group["gain_w_1"].median(),
                "mean_relative_gain_w_1": group["gain_w_1"].mean(),
                "sample_sum_ratio_gain_w_1": (
                    (full.sum(min_count=1) - denominator) / denominator
                    if pd.notna(denominator) and denominator > 0
                    else np.nan
                ),
                "retrieval_coverage": group["retrieval_matched_count"].sum()
                / group["retrieval_known_count"].sum()
                if group["retrieval_known_count"].sum() > 0
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def strata_metrics(observations: pd.DataFrame, vza_bins: Iterable[float]) -> pd.DataFrame:
    out = observations.copy()
    bins = list(vza_bins)
    out["vza_bin"] = pd.cut(
        out["mean_vza"].abs(), bins=bins, include_lowest=True, right=False
    ).astype("string")
    return pd.concat(
        [
            _summarize_stratum(out, "daynight"),
            _summarize_stratum(out, "satellite_normalized"),
            _summarize_stratum(out, "vza_bin"),
        ],
        ignore_index=True,
    )


def bootstrap_event_mean(
    event_values: pd.Series, replicates: int = 2000, seed: int = 20260915
) -> dict[str, float | int | None]:
    values = event_values.dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return {"events": 0, "mean": None, "lower_95": None, "upper_95": None}
    generator = np.random.default_rng(seed)
    samples = generator.choice(values, size=(replicates, len(values)), replace=True).mean(axis=1)
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return {
        "events": int(len(values)),
        "mean": float(values.mean()),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "replicates": int(replicates),
        "seed": int(seed),
        "interpretation": (
            "Event-resampling interval for variation within this public 2020 sample; "
            "not a confidence interval for candidate-pixel truth."
        ),
    }
