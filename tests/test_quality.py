from __future__ import annotations

import pandas as pd
import pytest

from conftest import synthetic_frame
from viirs_candidate_audit.quality import build_quality_report, prepare_analysis_frame
from viirs_candidate_audit.schema import normalize


@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
def test_synthetic_datetime_resolution_contract(unit: str) -> None:
    frame = synthetic_frame([{}, {}])
    values = pd.Series(pd.to_datetime(["2020-08-01T12:00:00Z", None], utc=True))
    frame["acq_datetime"] = values.astype(f"datetime64[{unit}, UTC]")
    normalized = normalize(frame)
    assert str(normalized["acq_datetime_utc"].dtype) == "datetime64[ns, UTC]"
    assert str(normalized["date_time_from_parts_utc"].dtype) == "datetime64[ns, UTC]"
    assert normalized.loc[0, "acq_datetime_utc"] == values.iloc[0]
    assert pd.isna(normalized.loc[1, "acq_datetime_utc"])


def test_synthetic_utc_and_classification_checks() -> None:
    frame = synthetic_frame(
        [
            {},
            {"confidence": "x", "fire_mask": 5.0, "frp_old": None},
            {"confidence": "z", "fire_mask": 8.0},
            {"confidence": "x", "fire_mask": 8.0, "frp_old": None},
        ]
    )
    normalized = normalize(frame)
    assert str(normalized["acq_datetime_utc"].dtype) == "datetime64[ns, UTC]"
    assert normalized["classification_status"].tolist() == [
        "known",
        "candidate",
        "unknown",
        "conflict",
    ]
    prepared = prepare_analysis_frame(frame)
    assert len(prepared) == 2


def test_synthetic_quality_reports_duplicates_missingness_and_time_mismatch() -> None:
    frame = synthetic_frame(
        [
            {"frp": None},
            {"frp": None},
            {
                "acq_datetime": pd.Timestamp("2020-08-01T12:01:00Z"),
                "longitude": -121.0,
            },
        ]
    )
    report = build_quality_report(frame)
    assert report["completeness"]["all_missing_frp_rows"] == 2
    assert report["uniqueness"]["exact_duplicate_rows_involved"] == 2
    assert report["uniqueness"]["exact_duplicate_excess_rows"] == 1
    assert report["validity"]["datetime_parts_mismatch_rows"] == 1

