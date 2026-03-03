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


@pytest.mark.unit
def test_is_already_renamed_true():
    """Verify is_already_renamed detects correctly formatted filenames."""
    from snapimport.rename import is_already_renamed
    
    assert is_already_renamed(Path("24-02-24-001.JPG")) is True
    assert is_already_renamed(Path("23-12-31-123.ORF")) is True
    assert is_already_renamed(Path("22-01-01-001.XMP")) is True


@pytest.mark.unit
def test_is_already_renamed_false():
    """Verify is_already_renamed rejects incorrectly formatted filenames."""
    from snapimport.rename import is_already_renamed
    
    assert is_already_renamed(Path("IMG_001.JPG")) is False
    assert is_already_renamed(Path("photo.jpg")) is False
    assert is_already_renamed(Path("24-02-24-001")) is True  # No extension but matches pattern
    assert is_already_renamed(Path("24-02-24-1.JPG")) is False  # Not 3 digits
    assert is_already_renamed(Path("2024-02-24-001.JPG")) is False  # 4-digit year


@pytest.mark.unit
def test_get_exif_date_subprocess_failure(monkeypatch):
    """Verify get_exif_date handles subprocess failures gracefully."""
    from snapimport.rename import get_exif_date
    import subprocess
    
    # Mock subprocess.run to raise an exception
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "exiftool")
    
    monkeypatch.setattr("snapimport.rename.subprocess.run", mock_run)
    assert get_exif_date(Path("test.JPG")) is None


@pytest.mark.unit
def test_get_exif_date_malformed_output(monkeypatch):
    """Verify get_exif_date handles malformed exiftool output."""
    from snapimport.rename import get_exif_date
    
    class MockResult:
        def __init__(self, stdout):
            self.stdout = stdout
    
    def mock_run(*args, **kwargs):
        return MockResult("malformed output without colon")
    
    monkeypatch.setattr("snapimport.rename.subprocess.run", mock_run)
    assert get_exif_date(Path("test.JPG")) is None


@pytest.mark.unit
def test_get_renames_skips_xmp_files(monkeypatch, tmp_path):
    """Verify get_renames skips XMP files but includes associated XMPs."""
    from snapimport.rename import get_renames
    
    # Create test files
    jpg_file = tmp_path / "test.JPG"
    xmp_file = tmp_path / "test.XMP"
    jpg_file.touch()
    xmp_file.touch()
    
    dates = ["24-02-24"]
    monkeypatch.setattr("snapimport.rename.subprocess.run", _mock_run_factory(dates))
    
    renames = get_renames([jpg_file, xmp_file], tmp_path)
    
    # Should only rename the JPG, but include the associated XMP
    assert len(renames) == 2
    assert any("JPG" in rename[1] for rename in renames)
    assert any("XMP" in rename[1] for rename in renames)


@pytest.mark.unit
def test_get_renames_no_exif_date(monkeypatch, tmp_path):
    """Verify get_renames skips files without EXIF dates."""
    from snapimport.rename import get_renames
    
    jpg_file = tmp_path / "test.JPG"
    jpg_file.touch()
    
    # Mock get_exif_date to return None
    def mock_get_exif_date(file):
        return None
    
    monkeypatch.setattr("snapimport.rename.get_exif_date", mock_get_exif_date)
    
    renames = get_renames([jpg_file], tmp_path)
    assert len(renames) == 0


@pytest.mark.unit
def test_get_renames_for_folder(monkeypatch, tmp_path):
    """Verify get_renames_for_folder returns mappings without executing."""
    from snapimport.rename import get_renames_for_folder
    
    jpg_file = tmp_path / "test.JPG"
    jpg_file.touch()
    
    dates = ["24-02-24"]
    monkeypatch.setattr("snapimport.rename.subprocess.run", _mock_run_factory(dates))
    
    renames = get_renames_for_folder(tmp_path)
    assert len(renames) == 1
    assert renames[0][0] == str(jpg_file)


@pytest.mark.unit
def test_execute_renames_dry_run(tmp_path):
    """Verify execute_renames doesn't rename files in dry_run mode."""
    from snapimport.rename import execute_renames
    
    old_file = tmp_path / "old.JPG"
    new_file = tmp_path / "new.JPG"
    old_file.touch()
    
    renames = [(str(old_file), str(new_file))]
    result = execute_renames(renames, dry_run=True)
    
    assert result == renames
    assert old_file.exists()  # File should still exist
    assert not new_file.exists()  # New file should not exist


@pytest.mark.unit
def test_execute_renames_actual_rename(tmp_path):
    """Verify execute_renames actually renames files when not dry_run."""
    from snapimport.rename import execute_renames
    
    old_file = tmp_path / "old.JPG"
    new_file = tmp_path / "new.JPG"
    old_file.touch()
    
    renames = [(str(old_file), str(new_file))]
    result = execute_renames(renames, dry_run=False)
    
    assert result == renames
    assert not old_file.exists()  # Old file should be gone
    assert new_file.exists()  # New file should exist
