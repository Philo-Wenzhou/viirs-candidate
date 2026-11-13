from __future__ import annotations

from pathlib import Path

import pytest

from viirs_candidate_audit.io import read_source, sha256_file


def test_synthetic_file_is_rejected_by_empirical_reader(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_empirical_input.csv"
    path.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Synthetic files are not accepted"):
        read_source(path)


def test_sha256_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "checksum_fixture.txt"
    path.write_bytes(b"viirs-audit")
    assert sha256_file(path) == "b289737f43c1ec02b21f50437844ba7ba8b9f2e2b78bbc95ffaa451f41b59076"
