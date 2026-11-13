# Data provenance

The empirical input is `joined_dets_2020.parquet` from the University of
Maryland Digital Repository (DRUM), dataset DOI
[`10.13016/evnn-j0zz`](https://doi.org/10.13016/evnn-j0zz). The landing page
declares the data as **CC0 1.0 Universal** and links the related paper DOI
[`10.1016/j.rse.2025.115156`](https://doi.org/10.1016/j.rse.2025.115156).

The raw file is intentionally excluded from version control. Run:

```bash
viirs-candidate-audit --root . download
```

The command downloads only the declared source file, validates its SHA256,
and writes `data/manifest.json` with the URL, access time, byte size, checksum,
license, DOIs, and software versions. A network, license, or checksum failure
stops the empirical workflow. There is no synthetic fallback.

The checksum recorded on 2026-09-15 is:

```text
c0695f44f8aa49e3db40bfc4517368d4b638dc9d1b1251874d9e632a81961416
```

Synthetic fixtures exist only inside `tests/`; their names and test purpose
are explicit.

