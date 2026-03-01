"""
Unit tests for rename functionality (snapimport.rename module).

Tests file discovery, EXIF date extraction, and rename logic.

Relies on: tmp_path fixture.
Run just this file: pytest tests/test_rename.py -v
"""

from pathlib import Path

from snapimport.rename import find_files

def test_find_files(tmp_path):
    """Verify find_files discovers supported image files recursively."""
    (tmp_path / "test.JPG").touch()
    (tmp_path / "test.ORF").touch()
    (tmp_path / "not_supported.txt").touch()
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "sub.JPG").touch()

    files = find_files(tmp_path)
    assert len(files) == 3
    assert all(f.suffix in ['.JPG', '.ORF'] for f in files)
