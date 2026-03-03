"""Final integration tests to reach 80% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli, core


@pytest.mark.integration
def test_integration_cli_rename_command_no_renames(tmp_path, monkeypatch):
    """Integration test for CLI rename command with no files to rename."""
    from snapimport.config import Config
    
    # Create config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('photos_dir = "/test/photos"\nlogs_dir = "/test/logs"')
    
    test_dir = tmp_path / "test_photos"
    test_dir.mkdir()
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir="/test/photos", logs_dir="/test/logs")), \
         patch("snapimport.cli.get_renames_for_folder", return_value=[]), \
         patch("snapimport.cli.execute_renames") as mock_execute, \
         patch("snapimport.cli.show_success_panel") as mock_success:
        
        cli.rename(path=str(test_dir), log=False, force=False)
        mock_execute.assert_called_once()
        # Check that success panel was called with correct message pattern
        mock_success.assert_called_once()
        call_args = mock_success.call_args[0][0]
        assert "No files to rename" in call_args


@pytest.mark.integration
def test_integration_cli_rename_command_force_logging(tmp_path, monkeypatch):
    """Integration test for CLI rename command with force flag."""
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
         patch("snapimport.core.log_seen_files") as mock_log, \
         patch("snapimport.cli.show_success_panel") as mock_success:
        
        cli.rename(path=str(test_dir), log=True, force=True)
        mock_execute.assert_called_once()
        mock_log.assert_called_once()
        mock_success.assert_called()


@pytest.mark.integration
def test_integration_cli_import_with_stats(tmp_path, monkeypatch):
    """Integration test for CLI import command with stats handling."""
    from snapimport.config import Config
    
    # Create config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('photos_dir = "/test/photos"\nlogs_dir = "/test/logs"')
    
    # Mock import stats
    stats = {
        "copied": 5,
        "skipped_seen": 2,
        "failed": 1,
        "overwritten": 1,
        "skipped_exists": 1,
        "source_volume": "/fake/sd"
    }
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir="/test/photos", logs_dir="/test/logs")), \
         patch("snapimport.cli.import_photos", return_value=stats), \
         patch("snapimport.cli._handle_fake_sd_restore") as mock_handle:
        
        cli.import_cmd(dry_run=False, verbose=False, overwrite=False, reconfigure=False)
        mock_handle.assert_called_once_with(stats)


@pytest.mark.integration
def test_integration_cli_import_no_stats(tmp_path, monkeypatch):
    """Integration test for CLI import command with no stats."""
    from snapimport.config import Config
    
    # Create config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('photos_dir = "/test/photos"\nlogs_dir = "/test/logs"')
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir="/test/photos", logs_dir="/test/logs")), \
         patch("snapimport.cli.import_photos", return_value=None), \
         patch("snapimport.cli._handle_fake_sd_restore") as mock_handle:
        
        cli.import_cmd(dry_run=False, verbose=False, overwrite=False, reconfigure=False)
        mock_handle.assert_not_called()


@pytest.mark.integration
def test_integration_core_copy_files_verbose(tmp_path, monkeypatch):
    """Integration test for core copy files with verbose output."""
    from snapimport.core import copy_files_with_progress
    from snapimport.progress import create_progress
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    
    progress = create_progress()
    with progress:
        result = copy_files_with_progress([test_file], tmp_path, progress, verbose=True)
    
    assert "copied" in result
    assert len(result["copied"]) == 1


@pytest.mark.integration
def test_integration_core_log_seen_files_with_base(tmp_path, monkeypatch):
    """Integration test for core log_seen_files with base folder."""
    from snapimport.core import log_seen_files
    
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    base_folder = tmp_path / "base"
    base_folder.mkdir()
    files = [base_folder / "file1.txt", base_folder / "file2.txt"]
    
    log_seen_files(logs_dir, files, base_folder)
    
    seen_file = logs_dir / "seen-files.txt"
    assert seen_file.exists()
    content = seen_file.read_text()
    assert "file1.txt" in content
    assert "file2.txt" in content
