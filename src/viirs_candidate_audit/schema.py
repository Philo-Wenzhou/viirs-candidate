"""Schema normalization and explicit known/candidate classification checks."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


REQUIRED_COLUMNS = {
    "longitude",
    "latitude",
    "fire_mask",
    "confidence",
    "acq_date",
    "acq_time",
    "acq_datetime",
    "vza",
    "sza",
    "daynight",
    "frp",
    "frp_old",
    "satellite",
    "fireid",
}

KNOWN_CONFIDENCE = {"l", "n", "h"}
CANDIDATE_CONFIDENCE = {"x"}
ALLOWED_DAYNIGHT = {"D", "N"}
ALLOWED_SATELLITES = {"SNPP", "NOAA20"}


@dataclass(frozen=True)
class SchemaResult:
    missing_columns: tuple[str, ...]
    extra_columns: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.missing_columns


def inspect_schema(frame: pd.DataFrame) -> SchemaResult:
    columns = set(frame.columns)
    return SchemaResult(
        missing_columns=tuple(sorted(REQUIRED_COLUMNS - columns)),
        extra_columns=tuple(sorted(columns - REQUIRED_COLUMNS)),
    )


def require_schema(frame: pd.DataFrame) -> None:
    result = inspect_schema(frame)
    if not result.valid:
        raise ValueError(f"Missing required columns: {', '.join(result.missing_columns)}")


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    require_schema(frame)
    out = frame.copy()
    out["confidence_normalized"] = out["confidence"].astype("string").str.strip().str.lower()
    out["daynight_normalized"] = out["daynight"].astype("string").str.strip().str.upper()
    out["satellite_normalized"] = out["satellite"].astype("string").str.strip().str.upper()
    out["acq_datetime_utc"] = pd.to_datetime(out["acq_datetime"], utc=True, errors="coerce")
    out["date_time_from_parts_utc"] = pd.to_datetime(
        out["acq_date"].astype("string").str.strip()
        + " "
        + out["acq_time"].astype("string").str.strip(),
        utc=True,
        errors="coerce",
    )

    confidence = out["confidence_normalized"]
    mask = pd.to_numeric(out["fire_mask"], errors="coerce")
    confidence_known = confidence.isin(KNOWN_CONFIDENCE)
    confidence_candidate = confidence.isin(CANDIDATE_CONFIDENCE)
    mask_known = mask.between(7, 9, inclusive="both")
    mask_candidate = mask.between(0, 6, inclusive="both")

    status = pd.Series("unknown", index=out.index, dtype="string")
    status.loc[confidence_known & mask_known] = "known"
    status.loc[confidence_candidate & mask_candidate] = "candidate"
    status.loc[(confidence_known & mask_candidate) | (confidence_candidate & mask_known)] = "conflict"
    out["classification_status"] = status
    return out

