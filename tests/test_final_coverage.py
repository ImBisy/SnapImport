"""Final unit tests to reach 80% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli, core


@pytest.mark.unit
def test_import_photos_multiple_sd_cards(tmp_path, monkeypatch):
    """Test import_photos handles multiple SD cards."""
    from snapimport.config import Config
    
    config = Config(photos_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    
    # Create test file
    test_file = tmp_path / "test.JPG"
    test_file.write_text("test")
    
    with patch("snapimport.core.detect_sds", return_value=["/sd1", "/sd2"]), \
         patch("snapimport.core.find_files", return_value=[test_file]), \
         patch("snapimport.core.confirm_import", return_value=True), \
         patch("snapimport.core.Prompt.ask", return_value="1"), \
         patch("snapimport.core.copy_files_with_progress") as mock_copy:
        
        mock_copy.return_value = {
            "copied": [str(test_file)],
            "failed": [],
            "skipped_seen": 0,
            "skipped_exists": 0,
            "overwritten": 0,
        }
        
        result = core.import_photos(config)
        
        # Should complete successfully
        assert result is not None
        assert result["copied"] == 1


@pytest.mark.unit
def test_import_photos_with_overwrite_warning(tmp_path, monkeypatch):
    """Test import_photos shows overwrite warning when enabled."""
    from snapimport.config import Config
    
    config = Config(photos_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    
    with patch("snapimport.core.detect_sds", return_value=[str(tmp_path)]), \
         patch("snapimport.core.find_files", return_value=[]), \
         patch("snapimport.progress.show_overwrite_warning") as mock_warning:
        
        result = core.import_photos(config, overwrite=True)
        
        # Should show overwrite warning
        mock_warning.assert_called_once()


@pytest.mark.unit
def test_cli_main_callback_no_config(tmp_path, monkeypatch):
    """Test CLI main callback runs wizard when no config exists."""
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    
    with patch("snapimport.cli.config_exists", return_value=False), \
         patch("snapimport.cli.run_wizard") as mock_wizard, \
         patch("snapimport.cli.console.print") as mock_print:
        
        cli.main(ctx)
        
        mock_wizard.assert_called_once()
        mock_print.assert_called()


@pytest.mark.unit
def test_cli_main_callback_with_config(tmp_path, monkeypatch):
    """Test CLI main callback shows help when config exists."""
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    
    with patch("snapimport.cli.config_exists", return_value=True), \
         patch("snapimport.cli.console.print") as mock_print:
        
        cli.main(ctx)
        
        # Should show help messages
        assert mock_print.call_count >= 2


@pytest.mark.unit
def test_rename_cmd_no_path_no_config(tmp_path, monkeypatch):
    """Test rename command handles no path and no config."""
    with patch("snapimport.cli.load_config", return_value=None), \
         patch("snapimport.cli.show_error_panel") as mock_error:
        
        cli.rename(path=None, log=False, force=False)
        
        mock_error.assert_called_once()


@pytest.mark.unit
def test_rename_cmd_invalid_path(tmp_path, monkeypatch):
    """Test rename command handles invalid path."""
    invalid_path = tmp_path / "nonexistent"
    
    with patch("snapimport.cli.show_error_panel") as mock_error:
        
        cli.rename(path=str(invalid_path), log=False, force=False)
        
        mock_error.assert_called_once()


@pytest.mark.unit
def test_wizard_cmd_shows_volumes(tmp_path, monkeypatch):
    """Test wizard command shows detected volumes."""
    with patch("snapimport.cli.run_wizard"), \
         patch("snapimport.cli.list_all_volumes", return_value=[("/vol1", True), ("/vol2", False)]), \
         patch("snapimport.cli.console.print") as mock_print:
        
        cli.wizard_cmd()
        
        # Should print table with volumes
        mock_print.assert_called()


@pytest.mark.unit
def test_setup_cmd_runs_wizard(tmp_path, monkeypatch):
    """Test setup command runs wizard and shows config."""
    with patch("snapimport.cli.run_wizard") as mock_wizard, \
         patch("snapimport.cli.load_config", return_value=MagicMock(photos_dir="/photos", logs_dir="/logs")), \
         patch("snapimport.cli.console.print") as mock_print:
        
        cli.setup_cmd()
        
        mock_wizard.assert_called_once()
        mock_print.assert_called()
