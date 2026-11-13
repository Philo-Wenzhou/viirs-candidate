# Limitations

- The public table contains author-selected known and candidate detections, not
  a complete set of fire and non-fire pixels. Missing records therefore do not
  mean a valid overpass observed no fire.
- No independent airborne truth labels are joined here. This audit does not
  estimate precision, recall, commission error, or omission error.
- Candidate weights are sensitivity scenarios, not calibrated fire
  probabilities.
- FRP is an instantaneous power quantity. Sums across recorded overpasses are
  descriptive sample aggregates, not fire radiative energy (FRE), daily energy,
  fuel consumption, or emissions.
- Recorded first/last detections define an observed detection span, not the
  physical ignition time, continuous burning duration, or extinction time.
- The 2020 large-fire sample is not a probability sample of all fires, regions,
  years, or fire sizes. Event-resampling intervals describe only this sample.
- Exact-time grouping follows the supplied UTC timestamp. A different
  overpass-clustering tolerance may alter observation-level results and should
  be declared before use.
- Map cases are descriptive and do not validate individual pixels. The
  selection rules are recorded in `outputs/map_case_selection.csv`.
- This repository is an independent analysis. It does not imply collaboration
  with, review by, or endorsement from EMBRS, the paper authors, NASA, UBC, or
  the University of Maryland.

