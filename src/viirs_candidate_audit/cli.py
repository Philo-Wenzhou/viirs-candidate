"""Command-line entry points for download, quality audit, and analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .io import download_data, load_config, read_source, write_manifest
from .metrics import (
    bootstrap_event_mean,
    event_metrics,
    observation_metrics,
    strata_metrics,
)
from .plots import (
    plot_map_cases,
    plot_retrieval_effect,
    plot_sensitivity,
    plot_strata,
    select_map_cases,
)
from .quality import build_quality_report, prepare_analysis_frame, write_quality_report


def _paths(root: Path, config: dict[str, Any]) -> dict[str, Path]:
    filename = config["data"]["filename"]
    return {
        "data": root / "data" / "raw" / filename,
        "manifest": root / "data" / "manifest.json",
        "outputs": root / "outputs",
    }


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")


def run_download(root: Path, config: dict[str, Any], overwrite: bool = False) -> None:
    paths = _paths(root, config)
    manifest = download_data(config["data"], paths["data"], paths["manifest"], overwrite)
    print(f"Verified source file: {paths['data']}")
    print(f"SHA256: {manifest['sha256']}")


def run_audit(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    paths = _paths(root, config)
    frame = read_source(paths["data"])
    report = build_quality_report(frame)
    write_quality_report(report, paths["outputs"] / "quality_report.json")
    write_manifest(paths["data"], paths["manifest"], config["data"])
    print(f"Wrote quality report: {paths['outputs'] / 'quality_report.json'}")
    return report


def run_analysis(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    paths = _paths(root, config)
    outputs = paths["outputs"]
    figures = outputs / "figures"
    outputs.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    raw = read_source(paths["data"])
    frame = prepare_analysis_frame(raw)
    settings = config["analysis"]
    weights = settings["candidate_weights"]
    tolerance = int(settings["overpass_tolerance_minutes"])
    observations = observation_metrics(frame, weights, tolerance)
    events = event_metrics(frame, observations, weights)
    strata = strata_metrics(observations, settings["vza_bins"])
    cases = select_map_cases(
        frame,
        events,
        count=int(settings["map_case_count"]),
        min_pixels=int(settings["map_min_pixels"]),
        min_frp_completeness=float(settings["map_min_frp_completeness"]),
    )

    observations.to_parquet(outputs / "observation_metrics.parquet", index=False)
    events.to_csv(outputs / "event_metrics.csv", index=False)
    strata.to_csv(outputs / "strata_metrics.csv", index=False)
    cases.to_csv(outputs / "map_case_selection.csv", index=False)

    uncertainty = bootstrap_event_mean(
        events["sample_sum_ratio_gain_w_1"],
        replicates=int(settings["bootstrap_replicates"]),
        seed=int(settings["random_seed"]),
    )
    matched_known = frame[
        frame["classification_status"].eq("known")
        & frame["frp_analysis"].notna()
        & frame["frp_old_analysis"].notna()
    ]
    retrieval_new_sum = matched_known["frp_analysis"].sum(min_count=1)
    retrieval_old_sum = matched_known["frp_old_analysis"].sum(min_count=1)
    candidate_new_sum = frame.loc[
        frame["classification_status"].eq("candidate"), "frp_analysis"
    ].sum(min_count=1)
    daynight_detection_ratios = {}
    for daynight, part in frame.groupby("daynight_normalized"):
        known_count = int(part["classification_status"].eq("known").sum())
        candidate_count = int(part["classification_status"].eq("candidate").sum())
        daynight_detection_ratios[str(daynight)] = {
            "known_pixels": known_count,
            "candidate_pixels": candidate_count,
            "candidate_to_known_ratio": candidate_count / known_count if known_count else None,
        }
    summary = {
        "schema_version": 1,
        "source_rows_after_declared_exclusions": int(len(frame)),
        "fire_events": int(frame["fireid"].nunique()),
        "observation_groups": int(len(observations)),
        "known_pixels": int(observations["known_count"].sum()),
        "candidate_pixels": int(observations["candidate_count"].sum()),
        "candidate_only_observation_groups": int(observations["candidate_only"].sum()),
        "comparable_w1_gain_groups": int(observations["gain_w_1"].notna().sum()),
        "median_observation_relative_gain_w1": float(observations["gain_w_1"].median()),
        "sample_sum_ratio_gain_w1": float(
            (
                observations["p_w_1"].sum(min_count=1)
                - observations["known_baseline_frp"].sum(min_count=1)
            )
            / observations["known_baseline_frp"].sum(min_count=1)
        ),
        "daynight_detection_counts": daynight_detection_ratios,
        "retrieval_matched_known_pixels": int(observations["retrieval_matched_count"].sum()),
        "retrieval_known_pixels": int(observations["retrieval_known_count"].sum()),
        "matched_known_new_frp_sum": float(retrieval_new_sum),
        "matched_known_old_frp_sum": float(retrieval_old_sum),
        "retrieval_sample_sum_relative_change": float(
            (retrieval_new_sum - retrieval_old_sum) / retrieval_old_sum
        ),
        "combined_new_known_plus_candidates_vs_old_known_relative_change": float(
            (retrieval_new_sum + candidate_new_sum - retrieval_old_sum) / retrieval_old_sum
        ),
        "event_resampling_w1_sample_sum_ratio_gain": uncertainty,
        "interpretation_limits": [
            "Candidate weights are sensitivity scenarios, not calibrated probabilities.",
            "Sample-sum ratios aggregate instantaneous FRP values descriptively and are not FRE or emissions.",
            "Detection spans describe recorded detections, not continuous physical burning duration.",
            "No independent truth labels are used, so this analysis does not estimate precision or recall.",
        ],
    }
    _write_json(summary, outputs / "analysis_summary.json")

    plot_sensitivity(observations, events, weights, figures / "candidate_sensitivity.png")
    plot_strata(strata, figures / "candidate_strata.png")
    plot_retrieval_effect(events, figures / "retrieval_effect.png")
    plot_map_cases(frame, cases, figures / "map_cases.png")
    print(f"Wrote empirical outputs under: {outputs}")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    download = subparsers.add_parser("download", help="Download and verify the public source file")
    download.add_argument("--overwrite", action="store_true")
    subparsers.add_parser("audit", help="Run schema and data-quality checks")
    subparsers.add_parser("analyze", help="Generate empirical tables and static figures")
    run = subparsers.add_parser("run", help="Download, audit, and analyze")
    run.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_config(config_path)
    if args.command == "download":
        run_download(root, config, args.overwrite)
    elif args.command == "audit":
        run_audit(root, config)
    elif args.command == "analyze":
        run_analysis(root, config)
    elif args.command == "run":
        run_download(root, config, args.overwrite)
        run_audit(root, config)
        run_analysis(root, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
