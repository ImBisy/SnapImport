"""Unit tests for progress module (snapimport.progress module).

Tests progress display, panels, and utility functions.

Relies on: tmp_path, monkeypatch fixtures.
Run just this file: pytest tests/test_progress_unit.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import progress


@pytest.mark.unit
def test_create_progress():
    """Test create_progress returns a progress instance."""
    result = progress.create_progress()
    assert result is not None


@pytest.mark.unit
def test_console_exists():
    """Test console object exists."""
    assert progress.console is not None


@pytest.mark.unit
def test_show_error_panel():
    """Test show_error_panel function exists and is callable."""
    assert callable(progress.show_error_panel)
    # Should not raise exception
    progress.show_error_panel("Test error message")


@pytest.mark.unit
def test_show_success_panel():
    """Test show_success_panel function exists and is callable."""
    assert callable(progress.show_success_panel)
    # Should not raise exception
    progress.show_success_panel("Test success message")


@pytest.mark.unit
def test_show_no_sd_card_panel():
    """Test show_no_sd_card_panel function exists and is callable."""
    assert callable(progress.show_no_sd_card_panel)
    # Should not raise exception
    progress.show_no_sd_card_panel()


@pytest.mark.unit
def test_show_import_complete_panel():
    """Test show_import_complete_panel function exists and is callable."""
    assert callable(progress.show_import_complete_panel)
    # Should not raise exception
    progress.show_import_complete_panel(
        files_copied=10,
        total_size_bytes=1024,
        files_skipped_seen=2,
        renamed_count=8,
        no_exif_count=2,
        destination="/test/path",
        is_dry_run=False,
        overwritten=1,
        skipped_exists=1
    )


@pytest.mark.unit
def test_write_import_errors(tmp_path):
    """Test write_import_errors writes to import-errors.log."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    failures = [
        {"file": "test1.txt", "reason": "Test error 1", "suggestion": "Suggestion 1"},
        {"file": "test2.txt", "reason": "Test error 2", "suggestion": "Suggestion 2"}
    ]
    
    progress.write_import_errors(logs_dir, failures)
    
    error_log = logs_dir / "import-errors.log"
    assert error_log.exists()
    
    content = error_log.read_text()
    assert "test1.txt | Test error 1 | Suggestion 1" in content
    assert "test2.txt | Test error 2 | Suggestion 2" in content


@pytest.mark.unit
def test_write_import_errors_no_failures(tmp_path):
    """Test write_import_errors handles empty failures list."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    progress.write_import_errors(logs_dir, [])
    
    error_log = logs_dir / "import-errors.log"
    # Should not create file for empty failures
    assert not error_log.exists()


@pytest.mark.unit
def test_write_import_errors_no_logs_dir(tmp_path):
    """Test write_import_errors handles missing logs directory."""
    failures = [{"file": "test.txt", "reason": "Test error", "suggestion": "Test suggestion"}]
    
    # Use a path that doesn't exist but is within tmp_path to avoid permission issues
    nonexistent_path = tmp_path / "nonexistent"
    
    # Should not raise exception even if logs_dir doesn't exist
    progress.write_import_errors(nonexistent_path, failures)
    
    # Should create the directory and file
    error_log = nonexistent_path / "import-errors.log"
    assert error_log.exists()


@pytest.mark.unit
def test_show_warnings_panel():
    """Test show_warnings_panel function exists and is callable."""
    assert callable(progress.show_warnings_panel)
    # Should not raise exception
    failures = [{"file": "test.txt", "reason": "Test error", "suggestion": "Test suggestion"}]
    progress.show_warnings_panel(failures)


@pytest.mark.unit
def test_show_dry_run_table():
    """Test show_dry_run_table function exists and is callable."""
    assert callable(progress.show_dry_run_table)
    # Should not raise exception
    renames = [("old.txt", "new.txt")]
    progress.show_dry_run_table(renames)


@pytest.mark.unit
def test_show_overwrite_warning():
    """Test show_overwrite_warning function exists and is callable."""
    assert callable(progress.show_overwrite_warning)
    # Should not raise exception
    progress.show_overwrite_warning()


@pytest.mark.unit
def test_confirm_import():
    """Test confirm_import function exists and is callable."""
    assert callable(progress.confirm_import)
