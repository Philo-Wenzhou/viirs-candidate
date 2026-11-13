"""Observation grouping that preserves fire, satellite, and UTC acquisition identity."""

from __future__ import annotations

import pandas as pd


GROUP_KEYS = ["fireid", "satellite_normalized", "observation_time_utc"]


def assign_observation_groups(
    frame: pd.DataFrame, tolerance_minutes: int = 0
) -> pd.DataFrame:
    out = frame.copy()
    timestamp = out["acq_datetime_utc"]
    if tolerance_minutes < 0:
        raise ValueError("overpass_tolerance_minutes must be non-negative")
    if tolerance_minutes:
        timestamp = timestamp.dt.floor(f"{tolerance_minutes}min")
    out["observation_time_utc"] = timestamp
    out["observation_id"] = (
        out["fireid"].astype("string")
        + "|"
        + out["satellite_normalized"].astype("string")
        + "|"
        + out["observation_time_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    return out


def _single_or_mixed(values: pd.Series) -> str:
    unique = values.dropna().astype(str).unique()
    if len(unique) == 0:
        return "missing"
    if len(unique) == 1:
        return unique[0]
    return "mixed"


def aggregate_observations(frame: pd.DataFrame, tolerance_minutes: int = 0) -> pd.DataFrame:
    grouped_frame = assign_observation_groups(frame, tolerance_minutes)
    grouped_frame["known_frp"] = grouped_frame["frp_analysis"].where(
        grouped_frame["classification_status"] == "known"
    )
    grouped_frame["candidate_frp"] = grouped_frame["frp_analysis"].where(
        grouped_frame["classification_status"] == "candidate"
    )
    grouped_frame["is_known"] = grouped_frame["classification_status"].eq("known")
    grouped_frame["is_candidate"] = grouped_frame["classification_status"].eq("candidate")
    grouped_frame["known_frp_valid"] = grouped_frame["is_known"] & grouped_frame["frp_analysis"].notna()
    grouped_frame["candidate_frp_valid"] = grouped_frame["is_candidate"] & grouped_frame["frp_analysis"].notna()

    grouped = grouped_frame.groupby(GROUP_KEYS, dropna=False, sort=True)
    observations = grouped.agg(
        observation_id=("observation_id", "first"),
        observed_rows=("classification_status", "size"),
        known_count=("is_known", "sum"),
        candidate_count=("is_candidate", "sum"),
        known_frp_valid_count=("known_frp_valid", "sum"),
        candidate_frp_valid_count=("candidate_frp_valid", "sum"),
        known_frp_sum=("known_frp", lambda values: values.sum(min_count=1)),
        candidate_frp_sum=("candidate_frp", lambda values: values.sum(min_count=1)),
        daynight=("daynight_normalized", _single_or_mixed),
        mean_vza=("vza_analysis", "mean"),
        max_abs_vza=("vza_analysis", lambda values: values.abs().max()),
        source_acquisition_times=("acq_datetime_utc", "nunique"),
    ).reset_index()
    observations["known_count"] = observations["known_count"].astype(int)
    observations["candidate_count"] = observations["candidate_count"].astype(int)
    observations["known_frp_missing_fraction"] = 1 - (
        observations["known_frp_valid_count"] / observations["known_count"].replace(0, pd.NA)
    )
    observations["candidate_frp_missing_fraction"] = 1 - (
        observations["candidate_frp_valid_count"]
        / observations["candidate_count"].replace(0, pd.NA)
    )
    return observations
