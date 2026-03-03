"""Additional unit tests to reach 80% coverage.

Tests specific edge cases and error paths not covered elsewhere.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli, core


@pytest.mark.unit
def test_run_wizard_invalid_photos_path(tmp_path, monkeypatch):
    """Test run_wizard handles invalid photos path."""
    # Mock photos path that doesn't exist
    invalid_path = tmp_path / "nonexistent"
    valid_path = tmp_path / "valid_photos"
    valid_path.mkdir()
    logs_path = tmp_path / "logs"
    logs_path.mkdir()
    
    with patch("snapimport.cli.show_welcome_panel"), \
         patch("snapimport.cli.prompt_photos_dir", side_effect=[str(invalid_path), str(valid_path)]), \
         patch("snapimport.cli.prompt_logs_dir", return_value=str(logs_path)), \
         patch("snapimport.cli.show_error_panel") as mock_error, \
         patch("snapimport.cli.save_config"), \
         patch("snapimport.cli.Config") as mock_config, \
         patch("snapimport.cli.find_files", return_value=[]):
        
        mock_config_instance = MagicMock()
        mock_config_instance.photos_dir = str(valid_path)
        mock_config_instance.logs_dir = str(logs_path)
        mock_config.return_value = mock_config_instance
        
        cli.run_wizard()
        
        # Should show error panel for invalid path
        mock_error.assert_called()


@pytest.mark.unit
def test_check_permissions_root_files(tmp_path, monkeypatch):
    """Test check_permissions detects root-owned files."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    
    # Mock stat to simulate root ownership
    mock_stat = MagicMock()
    mock_stat.st_uid = 0  # root user ID
    
    with patch("os.stat", return_value=mock_stat), \
         patch("snapimport.cli.Confirm.ask", return_value=False), \
         patch("subprocess.run") as mock_run:
        
        core.check_permissions(tmp_path)
        
        # Should not run subprocess since user declined
        mock_run.assert_not_called()


@pytest.mark.unit
def test_check_permissions_root_files_with_chown(tmp_path, monkeypatch):
    """Test check_permissions runs chown when user confirms."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    
    # Mock stat to simulate root ownership
    mock_stat = MagicMock()
    mock_stat.st_uid = 0  # root user ID
    
    with patch("os.stat", return_value=mock_stat), \
         patch("snapimport.cli.Confirm.ask", return_value=True), \
         patch("subprocess.run") as mock_run, \
         patch("os.getlogin", return_value="testuser"):
        
        core.check_permissions(tmp_path)
        
        # Should run subprocess to fix permissions
        mock_run.assert_called_once()


@pytest.mark.unit
def test_import_photos_no_files_found(tmp_path, monkeypatch):
    """Test import_photos handles no files found case."""
    from snapimport.config import Config
    
    config = Config(photos_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    
    with patch("snapimport.core.detect_sds", return_value=[str(tmp_path)]), \
         patch("snapimport.core.find_files", return_value=[]), \
         patch("snapimport.core.show_error_panel") as mock_error:
        
        result = core.import_photos(config)
        
        # Should return None when no files found
        assert result is None
        mock_error.assert_called_once()


@pytest.mark.unit
def test_import_photos_dry_run(tmp_path, monkeypatch):
    """Test import_photos dry run mode."""
    from snapimport.config import Config
    from snapimport.rename import get_renames
    
    config = Config(photos_dir=str(tmp_path), logs_dir=str(tmp_path / "logs"))
    
    # Create test file
    test_file = tmp_path / "test.JPG"
    test_file.write_text("test")
    
    with patch("snapimport.core.detect_sds", return_value=[str(tmp_path)]), \
         patch("snapimport.core.find_files", return_value=[test_file]), \
         patch("snapimport.progress.show_dry_run_table") as mock_dry_run, \
         patch("snapimport.progress.show_import_complete_panel") as mock_complete:
        
        result = core.import_photos(config, dry_run=True)
        
        # Should return None for dry run
        assert result is None
        mock_dry_run.assert_called_once()
        mock_complete.assert_called_once()


@pytest.mark.unit
def test_fake_sd_cmd_clears_existing_files(tmp_path, monkeypatch):
    """Test fake_sd_cmd clears existing files before creating new ones."""
    # Mock paths
    fake_sd = tmp_path / "fake-sd"
    fake_sd.mkdir()
    dcim = fake_sd / "DCIM"
    dcim.mkdir()
    
    # Create existing files that should be deleted
    existing_file = dcim / "existing.txt"
    existing_file.write_text("existing")
    
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()
    template_orf = demo_dir / "IMG_001.ORF"
    template_orf.write_bytes(b"template data")
    
    monkeypatch.setattr(cli, "FAKE_SD_PATH", fake_sd)
    monkeypatch.setattr(cli, "DEMO_TEMPLATE_DIR", demo_dir)
    
    with patch("snapimport.cli.show_fake_sd_ready_panel"):
        cli.fake_sd_cmd()
        
        # Existing file should be deleted
        assert not existing_file.exists()
        # Template file should exist
        assert (dcim / "IMG_001.ORF").exists()


@pytest.mark.unit
def test_reset_demo_cmd_handles_deletion_errors(tmp_path, monkeypatch):
    """Test reset_demo_cmd handles file deletion errors gracefully."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text("test config")
    
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    
    with patch("snapimport.cli.load_config") as mock_load, \
         patch("snapimport.cli.console.print") as mock_print, \
         patch("snapimport.cli.Panel"):
        
        mock_config = MagicMock()
        mock_config.logs_dir = str(tmp_path / "logs")  # Provide valid path
        mock_load.return_value = mock_config
        
        # Mock Path.unlink to raise exception for the config file
        original_unlink = Path.unlink
        def mock_unlink(self):
            if self.name == "config.toml":
                raise Exception("Permission denied")
            return original_unlink(self)
        
        with patch.object(Path, 'unlink', mock_unlink):
            cli.reset_demo_cmd(force=True)
        
        # Should print warning about deletion failure
        mock_print.assert_any_call("Warning: Could not delete")
