# Data management

## Source and custody

The public empirical source, DOI, declared license and SHA256 are recorded in
`data/manifest.json`. Keep that acquisition record intact when rerunning analyses;
its retrieval timestamp is not the date of a subsequent analysis run.
Raw inputs are immutable and excluded from Git. Retrieve them using the documented
download command; never replace failed downloads with synthetic observations.

## Publication boundary

Publish only this standalone analysis project. Application forms, CVs, transcripts,
account information, commercial satellite imagery and operational power-grid data
are outside its scope. Never include credentials or local machine paths in notebooks.
Code uses MIT; source-data licensing and attribution remain separate.

## Reproducibility

Keep configurations and source changes in Git together with regenerated tables,
figures and a dated validation record. Record the input checksum, environment,
commands and test outcome for each release. Synthetic fixtures belong only in tests.
Review output differences before replacing a published result. Preserve prior
releases through Git history rather than overwriting their provenance.

## Interpretation

The unit of observation is an event/satellite/UTC group, not an independent fire.
Candidate weights are sensitivity scenarios. FRP sample sums are not energy or
emissions; observed detection spans are not continuous burning durations. Without
independent labels, precision and recall cannot be inferred.
