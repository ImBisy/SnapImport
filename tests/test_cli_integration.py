"""More integration tests to reach 80% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli


@pytest.mark.integration
def test_integration_cli_import_command(tmp_path, monkeypatch):
    """Integration test for CLI import command."""
    from snapimport.config import Config
    
    # Create config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('photos_dir = "/test/photos"\nlogs_dir = "/test/logs"')
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir="/test/photos", logs_dir="/test/logs")), \
         patch("snapimport.cli.import_photos", return_value={"copied": 5}) as mock_import:
        
        cli.import_cmd(dry_run=False, verbose=False, overwrite=False, reconfigure=False)
        mock_import.assert_called_once()


@pytest.mark.integration
def test_integration_cli_import_command_no_config(tmp_path, monkeypatch):
    """Integration test for CLI import command with no config."""
    with patch("snapimport.cli.load_config", return_value=None), \
         patch("snapimport.cli.show_error_panel") as mock_error:
        
        cli.import_cmd(dry_run=False, verbose=False, overwrite=False, reconfigure=False)
        mock_error.assert_called_once()


@pytest.mark.integration
def test_integration_cli_import_command_reconfigure(tmp_path, monkeypatch):
    """Integration test for CLI import command with reconfigure."""
    from snapimport.config import Config
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir="/test/photos", logs_dir="/test/logs")), \
         patch("snapimport.cli.run_wizard") as mock_wizard, \
         patch("snapimport.cli.import_photos", return_value={"copied": 5}) as mock_import:
        
        cli.import_cmd(dry_run=False, verbose=False, overwrite=False, reconfigure=True)
        mock_wizard.assert_called_once()
        mock_import.assert_called_once()


@pytest.mark.integration
def test_integration_cli_rename_command_with_path(tmp_path, monkeypatch):
    """Integration test for CLI rename command with path."""
    test_dir = tmp_path / "test_photos"
    test_dir.mkdir()
    
    with patch("snapimport.cli.get_renames_for_folder", return_value=[]), \
         patch("snapimport.cli.execute_renames") as mock_execute:
        
        cli.rename(path=str(test_dir), log=False, force=False)
        mock_execute.assert_called_once()


@pytest.mark.integration
def test_integration_cli_rename_command_logging(tmp_path, monkeypatch):
    """Integration test for CLI rename command with logging."""
    from snapimport.config import Config
    
    # Create config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('photos_dir = "/test/photos"\nlogs_dir = "/test/logs"')
    
    test_dir = tmp_path / "test_photos"
    test_dir.mkdir()
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir="/test/photos", logs_dir="/test/logs")), \
         patch("snapimport.cli.get_renames_for_folder", return_value=[("old.txt", "new.txt")]), \
         patch("snapimport.cli.execute_renames") as mock_execute, \
         patch("snapimport.core.log_seen_files") as mock_log:
        
        cli.rename(path=str(test_dir), log=True, force=False)
        mock_execute.assert_called_once()
        mock_log.assert_called_once()


@pytest.mark.integration
def test_integration_cli_redo_logs_command(tmp_path, monkeypatch):
    """Integration test for CLI redo-logs command."""
    from snapimport.config import Config
    
    # Create config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('photos_dir = "/test/photos"\nlogs_dir = "/test/logs"')
    
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir=str(photos_dir), logs_dir=str(logs_dir))), \
         patch("snapimport.cli.find_files", return_value=[]), \
         patch("snapimport.cli.is_already_renamed", return_value=False):
        
        cli.redo_logs_cmd()
        
        # Verify log file was created
        log_file = logs_dir / "seen-files.txt"
        assert log_file.exists()


@pytest.mark.integration
def test_integration_cli_redo_logs_no_config(tmp_path, monkeypatch):
    """Integration test for CLI redo-logs command with no config."""
    with patch("snapimport.cli.load_config", return_value=None), \
         patch("snapimport.cli.show_error_panel") as mock_error:
        
        cli.redo_logs_cmd()
        mock_error.assert_called_once()


@pytest.mark.integration
def test_integration_cli_setup_command(tmp_path, monkeypatch):
    """Integration test for CLI setup command."""
    with patch("snapimport.cli.run_wizard") as mock_wizard, \
         patch("snapimport.cli.load_config", return_value=MagicMock(photos_dir="/photos", logs_dir="/logs")), \
         patch("snapimport.cli.console.print") as mock_print:
        
        cli.setup_cmd()
        mock_wizard.assert_called_once()
        mock_print.assert_called()


@pytest.mark.integration
def test_integration_cli_wizard_command(tmp_path, monkeypatch):
    """Integration test for CLI wizard command."""
    with patch("snapimport.cli.run_wizard") as mock_wizard, \
         patch("snapimport.cli.list_all_volumes", return_value=[("/vol1", True), ("/vol2", False)]), \
         patch("snapimport.cli.console.print") as mock_print:
        
        cli.wizard_cmd()
        mock_wizard.assert_called_once()
        mock_print.assert_called()


@pytest.mark.integration
def test_integration_cli_fake_sd_command_no_demo(tmp_path, monkeypatch):
    """Integration test for CLI fake-sd command with no demo files."""
    # Mock paths with no demo files
    fake_sd = tmp_path / "fake-sd"
    fake_sd.mkdir()
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()
    
    with patch("snapimport.cli.FAKE_SD_PATH", fake_sd), \
         patch("snapimport.cli.DEMO_TEMPLATE_DIR", demo_dir), \
         patch("snapimport.cli.show_fake_sd_ready_panel") as mock_show:
        
        cli.fake_sd_cmd()
        
        # Should create DCIM but no files
        assert (fake_sd / "DCIM").exists()
        mock_show.assert_called_with(fake_sd, 0)
