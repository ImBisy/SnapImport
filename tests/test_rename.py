from pathlib import Path

from snapimport.rename import find_files

def test_find_files(tmp_path):
    # Create some test files
    (tmp_path / "test.JPG").touch()
    (tmp_path / "test.ORF").touch()
    (tmp_path / "not_supported.txt").touch()
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "sub.JPG").touch()

    files = find_files(tmp_path)
    assert len(files) == 3
    assert all(f.suffix in ['.JPG', '.ORF'] for f in files)
