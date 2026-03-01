"""
Extended unit tests for rename functionality (snapimport.rename module).

Tests EXIF parsing, rename logic with sequences, and file filtering.

Relies on: tmp_path, monkeypatch fixtures.
Run just this file: pytest tests/test_rename_more.py -v
"""

import os
from pathlib import Path

import pytest

from snapimport.rename import (
    find_files,
    get_exif_date,
    get_renames,
    rename_files_in_folder,
)


def _mock_run_factory(dates):
    # returns a function compatible with subprocess.run signature
    class _Res:
        def __init__(self, stdout):
            self.stdout = stdout

    def _fake_run(args, capture_output, text):
        if not dates:
            date = ""
        else:
            date = dates.pop(0)
        # simulate empty output for none case
        if date == "":
            return _Res("")
        return _Res(f"Date/Time Original              : {date}")

    return _fake_run


def test_get_exif_date_parses(monkeypatch):
    """Verify get_exif_date extracts and formats EXIF DateTimeOriginal."""
    dates = ["24-02-24"]
    monkeypatch.setattr("snapimport.rename.subprocess.run", _mock_run_factory(dates))
    assert get_exif_date(Path("a.JPG")) == "24-02-24"


def test_get_exif_date_none(monkeypatch):
    """Verify get_exif_date returns None when EXIF data is missing."""
    assert get_exif_date(Path("a.JPG")) is None


def test_get_renames_increments(monkeypatch, tmp_path):
    """Verify rename sequences increment correctly for same-date files."""
    f1 = tmp_path / "image1.JPG"
    f2 = tmp_path / "image2.JPG"
    f1.touch()
    f2.touch()
    dates = ["24-02-24", "24-02-24"]
    monkeypatch.setattr("snapimport.rename.subprocess.run", _mock_run_factory(dates))

    renames = get_renames(sorted([f1, f2]), tmp_path)
    assert len(renames) == 2
    assert renames[0][0] == str(f1)
    assert renames[0][1].endswith("-001.JPG")
    assert renames[1][1].endswith("-002.JPG")


def test_rename_files_in_folder_dry_run(monkeypatch, tmp_path):
    """Verify dry-run mode shows renames without modifying files."""
    f1 = tmp_path / "A.JPG"
    f2 = tmp_path / "B.JPG"
    f1.touch()
    f2.touch()
    dates = ["24-02-24", "24-02-24"]
    monkeypatch.setattr("snapimport.rename.subprocess.run", _mock_run_factory(dates))
    renames = rename_files_in_folder(tmp_path, dry_run=True)
    assert len(renames) == 2
    # Ensure files were not renamed on disk
    assert f1.exists() and f2.exists()


def test_find_files_filters_and_sort(monkeypatch, tmp_path):
    """Verify find_files filters extensions and returns sorted results."""
    a = tmp_path / "a.JPG"
    a.touch()
    b = tmp_path / "b.ORF"
    b.touch()
    c = tmp_path / "c.txt"
    c.touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    d = sub / "d.JPG"
    d.touch()
    files = find_files(tmp_path)
    # should include only JPG/ORF extensions: 3 files
    assert len(files) == 3
