# Candidate inclusion and retrieval effects in VIIRS fire records

## Question

How do author-selected candidate detections change recorded fire activity, and
how much of the change instead reflects recalculation of FRP on known pixels?

## Evidence and method

The public dataset contains 873,862 records from 95 events. Grouping by event,
satellite and exact UTC yields 9,518 observation groups. We compare known-pixel
FRP with candidate-weight scenarios and separately compare old and recalculated
FRP on matched known pixels. Configuration and exclusions are documented in
`methods.md`; acquisition provenance is in `../data/manifest.json`.

## Results recorded in the analysis

Including candidates at full weight increases the recalculated FRP sample sum
by approximately 16.01%. Recalculation on matched known pixels decreases their
sample sum by 8.18% relative to the original values. The combined change is
approximately +6.52% relative to original known-pixel FRP. These percentages
have different denominators and must not simply be added.

The median comparable observation-level inclusion effect is only +0.68%,
indicating that the aggregate ratio does not describe a typical observation.
There are 661 candidate-only observation groups. These describe extra recorded
observations, not independently confirmed burning or reconstructed overpasses.

## Limitations and conclusion

This is a descriptive sensitivity audit, not a detector validation or paper
replication. Candidate status is not ground truth. Neither sample-sum FRP nor
observed detection span estimates emissions or true fire duration. Results
apply to this selected sample; they should not be generalized to all fires.
Separating candidate inclusion from retrieval changes makes the source of an
aggregate difference inspectable without assuming candidate detections are true.

## Reproduction and data stewardship

See the repository README for commands and generated evidence, and
[data management](data-management.md) for provenance and publication boundaries.
