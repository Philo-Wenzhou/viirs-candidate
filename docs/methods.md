# Methods

## Research question and grain

This independent reanalysis asks how author-selected candidate VIIRS fire
pixels change observed fire-activity summaries, and separates that inclusion
effect from the change between the study's recalculated FRP and the original
VIIRS-product FRP. The raw grain is one author-selected pixel record within a
FEDS fire event. The primary aggregation grain is fire event × satellite ×
exact UTC acquisition time. The default configuration does not merge nearby
times; alternative minute tolerances must be declared as sensitivity analyses.

## Quality and exclusion policy

The audit checks required fields, UTC parsing, agreement between the combined
timestamp and date/time parts, coordinate ranges, allowed categories,
candidate/known agreement between `confidence` and `fire_mask`, non-negative
FRP, missingness, exact duplicates, and composite identity duplicates.

Exact duplicate rows are removed only after their count is recorded.
Classification conflicts and records without event, satellite, or UTC grouping
keys are excluded. Negative FRP values are logged and treated as missing.
Missing FRP is never replaced by zero. If every relevant FRP value in a group
is missing, the group sum remains missing.

## Candidate inclusion sensitivity

Within observation group \(g\), known pixels are \(K_g\), author-selected
candidate pixels are \(C_g\), and both use the recalculated `frp` column:

\[
P_g^{(w)}=\sum_{i\in K_g}P_i^{new}
+w\sum_{i\in C_g}P_i^{new},\qquad w\in\{0,0.25,0.5,1\}.
\]

For a positive known-pixel baseline:

\[
G_g^{(w)}=\frac{P_g^{(w)}-P_g^{(0)}}{P_g^{(0)}}.
\]

The weights are deliberately uncalibrated scenarios, not probabilities that a
candidate pixel is truly burning. Candidate-only groups and zero baselines are
flagged; they do not receive infinite relative gains.

## FRP retrieval effect

Only known pixels for which both new and old FRP are present are compared:

\[
D_{g,retrieval}=\sum_{i\in K_g^*}P_i^{new}
-\sum_{i\in K_g^*}P_i^{old}.
\]

Every aggregation reports matched-pixel coverage. This prevents a difference
in missingness from being mislabeled as a retrieval difference.

## Summaries and uncertainty

Event-level tables report recorded first/last detection times, the known-only
and candidate-inclusive detection spans, candidate-only observation groups,
pixel counts, candidate sensitivity, and retrieval comparison coverage. These
are stratified by the source `daynight` flag, satellite, and absolute view
zenith angle bins.

The reported 95% interval resamples fire events, not pixels, with a fixed seed.
It describes variation among the 95 events in this public 2020 sample. It is
not a confidence interval for candidate-pixel truth and does not establish
population representativeness.

Map cases are selected mechanically from events with at least 100 pixels and
95% FRP completeness: the largest event, the largest candidate share, and the
smallest candidate FRP effect, avoiding duplicate selections.

