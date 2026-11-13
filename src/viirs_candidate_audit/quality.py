"""High-signal data-quality checks for the public VIIRS detection table."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .schema import ALLOWED_DAYNIGHT, ALLOWED_SATELLITES, inspect_schema, normalize


IDENTITY_COLUMNS = [
    "fireid",
    "satellite",
    "acq_datetime",
    "longitude",
    "latitude",
    "confidence",
    "fire_mask",
]


def _iso_or_none(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat()


def build_quality_report(frame: pd.DataFrame) -> dict[str, Any]:
    normalized = normalize(frame)
    schema = inspect_schema(frame)
    rows = len(normalized)
    exact_duplicate = normalized[frame.columns].duplicated(keep=False)
    identity_cols = [column for column in IDENTITY_COLUMNS if column in normalized.columns]
    identity_duplicate = normalized.duplicated(identity_cols, keep=False)
    time_delta = (
        normalized["acq_datetime_utc"] - normalized["date_time_from_parts_utc"]
    ).abs()
    valid_class = normalized["classification_status"].isin(["known", "candidate"])
    valid_keys = normalized[["fireid", "satellite_normalized", "acq_datetime_utc"]].notna().all(axis=1)
    valid_coords = normalized["longitude"].between(-180, 180) & normalized["latitude"].between(-90, 90)

    null_rates = {column: float(rate) for column, rate in normalized[frame.columns].isna().mean().items()}
    report: dict[str, Any] = {
        "schema_version": 1,
        "dataset": {
            "rows": rows,
            "columns": len(frame.columns),
            "column_names": list(frame.columns),
            "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
            "grain_assumption": "one author-selected VIIRS pixel record within a FEDS fire event",
            "time_min_utc": _iso_or_none(normalized["acq_datetime_utc"].min()),
            "time_max_utc": _iso_or_none(normalized["acq_datetime_utc"].max()),
            "distinct_fire_events": int(normalized["fireid"].nunique(dropna=True)),
        },
        "schema": {
            "valid": schema.valid,
            "missing_required_columns": list(schema.missing_columns),
            "extra_columns": list(schema.extra_columns),
        },
        "completeness": {
            "null_rates": null_rates,
            "all_missing_frp_rows": int(normalized["frp"].isna().sum()),
            "all_missing_frp_old_rows": int(normalized["frp_old"].isna().sum()),
        },
        "classification": {
            "status_counts": {
                str(key): int(value)
                for key, value in normalized["classification_status"].value_counts(dropna=False).items()
            },
            "confidence_counts": {
                str(key): int(value)
                for key, value in normalized["confidence_normalized"].value_counts(dropna=False).items()
            },
            "fire_mask_counts": {
                str(key): int(value)
                for key, value in normalized["fire_mask"].value_counts(dropna=False).sort_index().items()
            },
            "unknown_daynight_rows": int(
                (~normalized["daynight_normalized"].isin(ALLOWED_DAYNIGHT)).sum()
            ),
            "unknown_satellite_rows": int(
                (~normalized["satellite_normalized"].isin(ALLOWED_SATELLITES)).sum()
            ),
        },
        "validity": {
            "invalid_coordinate_rows": int((~valid_coords.fillna(False)).sum()),
            "acq_datetime_parse_failures": int(normalized["acq_datetime_utc"].isna().sum()),
            "date_time_parts_parse_failures": int(normalized["date_time_from_parts_utc"].isna().sum()),
            "datetime_parts_mismatch_rows": int((time_delta > pd.Timedelta(0)).fillna(False).sum()),
            "negative_frp_rows": int((normalized["frp"] < 0).fillna(False).sum()),
            "negative_frp_old_rows": int((normalized["frp_old"] < 0).fillna(False).sum()),
            "candidate_rows_with_frp_old": int(
                ((normalized["classification_status"] == "candidate") & normalized["frp_old"].notna()).sum()
            ),
            "known_rows_missing_frp_old": int(
                ((normalized["classification_status"] == "known") & normalized["frp_old"].isna()).sum()
            ),
        },
        "uniqueness": {
            "exact_duplicate_rows_involved": int(exact_duplicate.sum()),
            "exact_duplicate_excess_rows": int(normalized[frame.columns].duplicated().sum()),
            "identity_columns": identity_cols,
            "identity_duplicate_rows_involved": int(identity_duplicate.sum()),
        },
        "analysis_eligibility": {
            "valid_class_and_required_keys_rows": int((valid_class & valid_keys).sum()),
            "excluded_invalid_classification_rows": int((~valid_class).sum()),
            "excluded_missing_group_key_rows": int((valid_class & ~valid_keys).sum()),
            "policy": (
                "Exact duplicate rows are removed after being reported. Classification conflicts and rows "
                "without event/satellite/UTC keys are excluded. Negative FRP values are logged and treated "
                "as missing for quantitative aggregation."
            ),
        },
    }
    return report


def prepare_analysis_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = normalize(frame)
    source_columns = list(frame.columns)
    out = out.loc[~out[source_columns].duplicated()].copy()
    valid_class = out["classification_status"].isin(["known", "candidate"])
    valid_keys = out[["fireid", "satellite_normalized", "acq_datetime_utc"]].notna().all(axis=1)
    out = out.loc[valid_class & valid_keys].copy()
    out["frp_analysis"] = pd.to_numeric(out["frp"], errors="coerce").mask(lambda value: value < 0)
    out["frp_old_analysis"] = pd.to_numeric(out["frp_old"], errors="coerce").mask(
        lambda value: value < 0
    )
    out["vza_analysis"] = pd.to_numeric(out["vza"], errors="coerce")
    return out


def write_quality_report(report: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")

