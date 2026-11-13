from __future__ import annotations

import numpy as np
import pandas as pd

from conftest import synthetic_frame
from viirs_candidate_audit.metrics import observation_metrics
from viirs_candidate_audit.quality import prepare_analysis_frame


def _synthetic_edge_cases() -> pd.DataFrame:
    return synthetic_frame(
        [
            {"frp": 10.0, "frp_old": 8.0},
            {
                "confidence": "x",
                "fire_mask": 5.0,
                "frp": 4.0,
                "frp_old": None,
                "longitude": -120.1,
            },
            {
                "acq_time": "12:05",
                "acq_datetime": pd.Timestamp("2020-08-01T12:05:00Z"),
                "confidence": "x",
                "fire_mask": 5.0,
                "frp": 2.0,
                "frp_old": None,
            },
            {
                "acq_time": "12:10",
                "acq_datetime": pd.Timestamp("2020-08-01T12:10:00Z"),
                "frp": 0.0,
                "frp_old": 0.0,
            },
            {
                "acq_time": "12:10",
                "acq_datetime": pd.Timestamp("2020-08-01T12:10:00Z"),
                "confidence": "x",
                "fire_mask": 5.0,
                "frp": 3.0,
                "frp_old": None,
                "longitude": -120.1,
            },
            {
                "acq_time": "12:15",
                "acq_datetime": pd.Timestamp("2020-08-01T12:15:00Z"),
                "frp": None,
                "frp_old": None,
            },
            {
                "acq_time": "12:15",
                "acq_datetime": pd.Timestamp("2020-08-01T12:15:00Z"),
                "confidence": "x",
                "fire_mask": 5.0,
                "frp": None,
                "frp_old": None,
                "longitude": -120.1,
            },
            {
                "acq_time": "12:20",
                "acq_datetime": pd.Timestamp("2020-08-01T12:20:00Z"),
                "frp": 5.0,
                "frp_old": 4.0,
            },
            {
                "acq_time": "12:20",
                "acq_datetime": pd.Timestamp("2020-08-01T12:20:00Z"),
                "frp": 6.0,
                "frp_old": None,
                "longitude": -120.1,
            },
        ]
    )


def test_synthetic_weight_baseline_monotonicity_and_edge_groups() -> None:
    observations = observation_metrics(
        prepare_analysis_frame(_synthetic_edge_cases()), [0, 0.25, 0.5, 1]
    ).set_index("observation_time_utc")
    first = observations.loc[pd.Timestamp("2020-08-01T12:00:00Z")]
    assert first["p_w_0"] == 10.0
    assert first["p_w_0_25"] == 11.0
    assert first["p_w_1"] == 14.0
    assert first["gain_w_1"] == 0.4

    candidate_only = observations.loc[pd.Timestamp("2020-08-01T12:05:00Z")]
    assert candidate_only["candidate_only"]
    assert candidate_only["p_w_0"] == 0.0
    assert candidate_only["p_w_1"] == 2.0
    assert np.isnan(candidate_only["gain_w_1"])

    zero_baseline = observations.loc[pd.Timestamp("2020-08-01T12:10:00Z")]
    assert zero_baseline["zero_known_baseline"]
    assert np.isnan(zero_baseline["gain_w_1"])

    all_missing = observations.loc[pd.Timestamp("2020-08-01T12:15:00Z")]
    assert np.isnan(all_missing["p_w_0"])
    assert np.isnan(all_missing["p_w_1"])

    comparable = observations[observations["known_baseline_frp"].notna()]
    assert (comparable["p_w_0"] == comparable["known_baseline_frp"]).all()
    ordered = comparable[["p_w_0", "p_w_0_25", "p_w_0_5", "p_w_1"]]
    assert (ordered.diff(axis=1).iloc[:, 1:] >= 0).all().all()


def test_synthetic_retrieval_uses_matched_known_pixels_only() -> None:
    observations = observation_metrics(
        prepare_analysis_frame(_synthetic_edge_cases()), [0, 0.25, 0.5, 1]
    ).set_index("observation_time_utc")
    first = observations.loc[pd.Timestamp("2020-08-01T12:00:00Z")]
    assert first["retrieval_delta_sum"] == 2.0
    assert first["retrieval_coverage"] == 1.0

    partial = observations.loc[pd.Timestamp("2020-08-01T12:20:00Z")]
    assert partial["retrieval_known_count"] == 2
    assert partial["retrieval_matched_count"] == 1
    assert partial["retrieval_delta_sum"] == 1.0
    assert partial["retrieval_coverage"] == 0.5

