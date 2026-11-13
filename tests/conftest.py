from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def synthetic_frame(rows: Iterable[dict]) -> pd.DataFrame:
    defaults = {
        "longitude": -120.0,
        "latitude": 40.0,
        "fire_mask": 8.0,
        "confidence": "n",
        "acq_date": "2020-08-01",
        "acq_time": "12:00",
        "acq_datetime": pd.Timestamp("2020-08-01T12:00:00Z"),
        "vza": 20.0,
        "sza": 30.0,
        "daynight": "D",
        "frp": 10.0,
        "frp_old": 9.0,
        "satellite": "SNPP",
        "fireid": "SYNTHETIC-FIRE",
        "name": "SYNTHETIC TEST EVENT",
    }
    materialized = []
    for row in rows:
        merged = defaults.copy()
        merged.update(row)
        materialized.append(merged)
    return pd.DataFrame(materialized)

