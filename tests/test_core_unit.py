"""Additional unit tests for core functionality (snapimport.core module).

Tests individual functions and edge cases not covered in integration tests.

Relies on: tmp_path, monkeypatch fixtures.
Run just this file: pytest tests/test_core_unit.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import core


@pytest.mark.unit
def test_detect_sds():
    """Test detect_sds function exists and returns list."""
    # This is a basic smoke test since the function relies on system state
    result = core.detect_sds()
    assert isinstance(result, list)


@pytest.mark.unit
def test_copy_file_with_progress_success(tmp_path):
    """Test copy_file_with_progress returns True on successful copy."""
    from snapimport.progress import create_progress
    
    # Create source file
    source = tmp_path / "source.txt"
    source.write_text("test content")
    
    # Create destination path
    dest = tmp_path / "dest.txt"
    
    progress = create_progress()
    with progress:
        # Add a task first
        task_id = progress.add_task("Copying", total=source.stat().st_size)
        result = core.copy_file_with_progress(source, dest, progress, task_id)
    
    assert result is True
    assert dest.exists()
    assert dest.read_text() == "test content"


@pytest.mark.unit
def test_copy_file_with_progress_failure(tmp_path):
    """Test copy_file_with_progress returns False on copy failure."""
    from snapimport.progress import create_progress
    
    # Try to copy non-existent file
    source = tmp_path / "nonexistent.txt"
    dest = tmp_path / "dest.txt"
    
    progress = create_progress()
    with progress:
        result = core.copy_file_with_progress(source, dest, progress, 1)
    
    assert result is False
    assert not dest.exists()


@pytest.mark.unit
def test_copy_files_with_progress_empty_list(tmp_path):
    """Test copy_files_with_progress handles empty file list."""
    from snapimport.progress import create_progress
    
    progress = create_progress()
    with progress:
        result = core.copy_files_with_progress([], tmp_path, progress, verbose=False)
    
    assert len(result["copied"]) == 0
    assert result["skipped_seen"] == 0
    assert result["overwritten"] == 0
    assert len(result["failed"]) == 0


@pytest.mark.unit
def test_copy_files_with_progress_seen_files(tmp_path):
    """Test copy_files_with_progress skips seen files."""
    from snapimport.progress import create_progress
    
    # Create source file
    source = tmp_path / "source.txt"
    source.write_text("test")
    
    seen_set = {str(source)}
    
    progress = create_progress()
    with progress:
        result = core.copy_files_with_progress(
            [source], tmp_path, progress, seen_set=seen_set, verbose=False
        )
    
    # Should skip the file since it's in seen_set
    assert len(result["copied"]) == 0
    assert result["skipped_seen"] == 1




@pytest.mark.unit
def test_log_seen_files(tmp_path):
    """Test log_seen_files writes to seen-files.txt."""
    logs_dir = tmp_path / "logs"
    files = [tmp_path / "file1.txt", tmp_path / "file2.txt"]
    
    core.log_seen_files(logs_dir, files)
    
    seen_file = logs_dir / "seen-files.txt"
    assert seen_file.exists()
    
    content = seen_file.read_text()
    assert "file1.txt" in content
    assert "file2.txt" in content


@pytest.mark.unit
def test_log_seen_files_with_base_folder(tmp_path):
    """Test log_seen_files uses base folder for relative paths."""
    logs_dir = tmp_path / "logs"
    base_folder = tmp_path / "base"
    base_folder.mkdir()
    files = [base_folder / "file1.txt", base_folder / "file2.txt"]
    
    core.log_seen_files(logs_dir, files, base_folder)
    
    seen_file = logs_dir / "seen-files.txt"
    assert seen_file.exists()
    
    content = seen_file.read_text()
    assert "file1.txt" in content
    assert "file2.txt" in content


@pytest.mark.unit
def test_check_permissions_no_root_files(tmp_path):
    """Test check_permissions handles directory with no root files."""
    # Create a test file with current user ownership
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    
    # Should not raise any exceptions
    core.check_permissions(tmp_path)
