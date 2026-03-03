"""One more integration test to reach 80% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli


@pytest.mark.integration
def test_integration_cli_main_callback_with_subcommand(tmp_path, monkeypatch):
    """Integration test for CLI main callback with subcommand."""
    ctx = MagicMock()
    ctx.invoked_subcommand = "import"
    
    with patch("snapimport.cli.show_header") as mock_header:
        cli.main(ctx)
        mock_header.assert_called_once()


@pytest.mark.integration
def test_integration_progress_panels_coverage(tmp_path, monkeypatch):
    """Integration test for progress panel functions."""
    from snapimport.progress import (
        show_warnings_panel, 
        show_dry_run_table, 
        show_overwrite_warning
    )
    
    # Test panel functions (should not raise exceptions)
    show_warnings_panel([{"file": "test.txt", "reason": "error", "suggestion": "fix"}])
    show_dry_run_table([("old.txt", "new.txt")])
    show_overwrite_warning()


@pytest.mark.integration
def test_integration_rename_edge_cases(tmp_path, monkeypatch):
    """Integration test for rename edge cases."""
    from snapimport.rename import is_already_renamed, get_renames
    
    # Test edge cases for is_already_renamed
    assert is_already_renamed(Path("24-02-24-001.JPG")) is True
    assert is_already_renamed(Path("24-02-24-001")) is True  # No extension
    assert is_already_renamed(Path("IMG_001.JPG")) is False
    
    # Test get_renames with no EXIF
    test_file = tmp_path / "test.JPG"
    test_file.write_text("test")
    
    with patch("snapimport.rename.get_exif_date", return_value=None):
        renames = get_renames([test_file], tmp_path)
        assert len(renames) == 0
