"""Unit tests for CLI module (snapimport.cli module).

Tests CLI commands and utility functions in isolation.

Relies on: tmp_path, monkeypatch fixtures.
Run just this file: pytest tests/test_cli_unit.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli


@pytest.mark.unit
def test_app_exists():
    """Test that Typer app exists."""
    assert cli.app is not None


@pytest.mark.unit
def test_handle_fake_sd_restore_no_source_volume():
    """Test _handle_fake_sd_restore handles missing source_volume."""
    stats = {}
    # Should not raise exception
    cli._handle_fake_sd_restore(stats)


@pytest.mark.unit
def test_handle_fake_sd_restore_non_fake_volume():
    """Test _handle_fake_sd_restore ignores non-fake volumes."""
    stats = {"source_volume": "/some/other/path"}
    # Should not raise exception
    cli._handle_fake_sd_restore(stats)


@pytest.mark.unit
def test_handle_fake_sd_restore_with_fake_volume(tmp_path, monkeypatch):
    """Test _handle_fake_sd_restore handles fake SD volume."""
    # Mock FAKE_SD_PATH to use our tmp_path
    fake_sd = tmp_path / "fake-sd"
    fake_sd.mkdir()
    dcim = fake_sd / "DCIM"
    dcim.mkdir()
    
    # Create a test file
    test_file = dcim / "test.txt"
    test_file.write_text("test")
    
    monkeypatch.setattr(cli, "FAKE_SD_PATH", fake_sd)
    
    stats = {"source_volume": str(fake_sd)}
    
    # Mock Confirm.ask to return False (don't restore)
    with patch("snapimport.cli.Confirm.ask", return_value=False):
        cli._handle_fake_sd_restore(stats)
    
    # File should still exist since we didn't restore
    assert test_file.exists()


@pytest.mark.unit
def test_handle_fake_sd_restore_with_restore(tmp_path, monkeypatch):
    """Test _handle_fake_sd_restore actually restores when confirmed."""
    # Mock FAKE_SD_PATH and DEMO_TEMPLATE_DIR
    fake_sd = tmp_path / "fake-sd"
    fake_sd.mkdir()
    dcim = fake_sd / "DCIM"
    dcim.mkdir()
    
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()
    template_orf = demo_dir / "IMG_001.ORF"
    template_orf.write_bytes(b"template data")
    
    # Create a test file that will be replaced
    test_file = dcim / "test.txt"
    test_file.write_text("test")
    
    monkeypatch.setattr(cli, "FAKE_SD_PATH", fake_sd)
    monkeypatch.setattr(cli, "DEMO_TEMPLATE_DIR", demo_dir)
    
    stats = {"source_volume": str(fake_sd)}
    
    # Mock Confirm.ask to return True (do restore)
    with patch("snapimport.cli.Confirm.ask", return_value=True), \
         patch("snapimport.cli.console.print"):
        cli._handle_fake_sd_restore(stats)
    
    # Test file should be gone, template file should exist
    assert not test_file.exists()
    assert (dcim / "IMG_001.ORF").exists()


@pytest.mark.unit
def test_run_wizard_basic_flow(tmp_path, monkeypatch):
    """Test run_wizard basic flow with mocked prompts."""
    # Mock all the prompt functions
    photos_path = tmp_path / "photos"
    photos_path.mkdir()
    logs_path = tmp_path / "logs"
    logs_path.mkdir()
    
    with patch("snapimport.cli.show_welcome_panel"), \
         patch("snapimport.cli.prompt_photos_dir", return_value=str(photos_path)), \
         patch("snapimport.cli.prompt_logs_dir", return_value=str(logs_path)), \
         patch("snapimport.cli.find_files", return_value=[]), \
         patch("snapimport.cli.save_config") as mock_save, \
         patch("snapimport.cli.Config") as mock_config:
        
        mock_config_instance = MagicMock()
        mock_config_instance.photos_dir = str(photos_path)
        mock_config_instance.logs_dir = str(logs_path)
        mock_config.return_value = mock_config_instance
        
        cli.run_wizard()
        
        # Verify config was saved
        mock_save.assert_called_once_with(mock_config_instance)


@pytest.mark.unit
def test_run_wizard_creates_logs_dir(tmp_path, monkeypatch):
    """Test run_wizard creates logs directory if it doesn't exist."""
    photos_path = tmp_path / "photos"
    photos_path.mkdir()
    logs_path = tmp_path / "logs"  # Don't create this - wizard should create it
    
    with patch("snapimport.cli.show_welcome_panel"), \
         patch("snapimport.cli.prompt_photos_dir", return_value=str(photos_path)), \
         patch("snapimport.cli.prompt_logs_dir", return_value=str(logs_path)), \
         patch("snapimport.cli.find_files", return_value=[]), \
         patch("snapimport.cli.save_config"), \
         patch("snapimport.cli.Config") as mock_config:
        
        mock_config_instance = MagicMock()
        mock_config_instance.photos_dir = str(photos_path)
        mock_config_instance.logs_dir = str(logs_path)
        mock_config.return_value = mock_config_instance
        
        cli.run_wizard()
        
        # Verify logs directory was created
        assert logs_path.exists()


@pytest.mark.unit
def test_run_wizard_handles_existing_renamed_files(tmp_path, monkeypatch):
    """Test run_wizard handles already renamed files."""
    photos_path = tmp_path / "photos"
    photos_path.mkdir()
    logs_path = tmp_path / "logs"
    logs_path.mkdir()
    
    # Mock existing renamed files
    renamed_files = [photos_path / "24-02-24-001.jpg"]
    
    with patch("snapimport.cli.show_welcome_panel"), \
         patch("snapimport.cli.prompt_photos_dir", return_value=str(photos_path)), \
         patch("snapimport.cli.prompt_logs_dir", return_value=str(logs_path)), \
         patch("snapimport.cli.find_files", return_value=renamed_files), \
         patch("snapimport.cli.is_already_renamed", return_value=True), \
         patch("snapimport.cli.save_config"), \
         patch("snapimport.cli.Config") as mock_config, \
         patch("snapimport.cli.Confirm.ask", return_value=True), \
         patch("snapimport.core.log_seen_files") as mock_log:
        
        mock_config_instance = MagicMock()
        mock_config_instance.photos_dir = str(photos_path)
        mock_config_instance.logs_dir = str(logs_path)
        mock_config.return_value = mock_config_instance
        
        cli.run_wizard()
        
        # Verify logging was called
        mock_log.assert_called_once()


@pytest.mark.unit
def test_run_wizard_creates_first_run_marker(tmp_path, monkeypatch):
    """Test run_wizard creates first-run marker."""
    photos_path = tmp_path / "photos"
    photos_path.mkdir()
    logs_path = tmp_path / "logs"
    logs_path.mkdir()
    
    # Mock config path
    config_dir = tmp_path / "config"
    config_path = config_dir / "config.toml"
    
    with patch("snapimport.cli.show_welcome_panel"), \
         patch("snapimport.cli.prompt_photos_dir", return_value=str(photos_path)), \
         patch("snapimport.cli.prompt_logs_dir", return_value=str(logs_path)), \
         patch("snapimport.cli.find_files", return_value=[]), \
         patch("snapimport.cli.save_config"), \
         patch("snapimport.cli.Config") as mock_config, \
         patch("snapimport.cli.get_config_path", return_value=config_path), \
         patch("snapimport.cli.show_success_panel"):
        
        mock_config_instance = MagicMock()
        mock_config_instance.photos_dir = str(photos_path)
        mock_config_instance.logs_dir = str(logs_path)
        mock_config.return_value = mock_config_instance
        
        cli.run_wizard()
        
        # Verify marker was created
        marker = config_dir / ".first_run_done"
        assert marker.exists()


@pytest.mark.unit
def test_fake_sd_cmd(tmp_path, monkeypatch):
    """Test fake_sd_cmd creates fake SD structure."""
    # Mock paths
    fake_sd = tmp_path / "fake-sd"
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()
    
    # Create template files
    template_orf = demo_dir / "IMG_001.ORF"
    template_orf.write_bytes(b"fake orf data")
    template_xmp = demo_dir / "IMG_001.XMP"
    template_xmp.write_text("fake xmp data")
    
    monkeypatch.setattr(cli, "FAKE_SD_PATH", fake_sd)
    monkeypatch.setattr(cli, "DEMO_TEMPLATE_DIR", demo_dir)
    
    with patch("snapimport.cli.show_fake_sd_ready_panel") as mock_show:
        cli.fake_sd_cmd()
        
        # Verify fake SD was created
        assert fake_sd.exists()
        assert (fake_sd / "DCIM").exists()
        assert (fake_sd / "DCIM" / "IMG_001.ORF").exists()
        assert (fake_sd / "DCIM" / "IMG_001.XMP").exists()
        
        # Verify panel was shown
        mock_show.assert_called_once_with(fake_sd, 1)


@pytest.mark.unit
def test_reset_demo_cmd_no_files(tmp_path, monkeypatch):
    """Test reset_demo_cmd when no state files exist."""
    # Mock config path to non-existent location
    config_path = tmp_path / "config" / "config.toml"
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    
    with patch("snapimport.cli.console.print") as mock_print:
        cli.reset_demo_cmd(force=True)
        
        # Should print "No state files found"
        mock_print.assert_called_with("No state files found. Nothing to reset.")


@pytest.mark.unit
def test_reset_demo_cmd_with_files(tmp_path, monkeypatch):
    """Test reset_demo_cmd deletes existing state files."""
    # Create config and log files
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text("test config")
    
    first_run_marker = config_dir / ".first_run_done"
    first_run_marker.write_text("done")
    
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    seen_files = logs_dir / "seen-files.txt"
    seen_files.write_text("test.txt")
    import_errors = logs_dir / "import-errors.log"
    import_errors.write_text("error log")
    
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    
    with patch("snapimport.cli.load_config") as mock_load, \
         patch("snapimport.cli.console.print") as mock_print, \
         patch("snapimport.cli.Panel") as mock_panel:
        
        mock_config = MagicMock()
        mock_config.logs_dir = str(logs_dir)
        mock_load.return_value = mock_config
        
        cli.reset_demo_cmd(force=True)
        
        # Verify files were deleted
        assert not config_path.exists()
        assert not first_run_marker.exists()
        assert not seen_files.exists()
        assert not import_errors.exists()
        
        # Verify success message
        mock_print.assert_called_with("✓ Reset Complete - run `snapimport` to start fresh")


@pytest.mark.unit
def test_reset_demo_cmd_with_confirmation(tmp_path, monkeypatch):
    """Test reset_demo_cmd respects confirmation prompt."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    config_path.write_text("test config")
    
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    
    with patch("snapimport.cli.load_config") as mock_load, \
         patch("snapimport.cli.console.print") as mock_print, \
         patch("snapimport.cli.Panel") as mock_panel, \
         patch("snapimport.cli.Confirm.ask", return_value=False):
        
        mock_config = MagicMock()
        mock_config.logs_dir = str(tmp_path / "logs")  # Provide valid path
        mock_load.return_value = mock_config
        
        cli.reset_demo_cmd(force=False)
        
        # Should print "Aborted."
        mock_print.assert_any_call("Aborted.")
        
        # File should still exist
        assert config_path.exists()
