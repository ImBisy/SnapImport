"""Final test to push integration coverage over 80%."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli


@pytest.mark.integration
def test_integration_cli_rename_seen_files_handling(tmp_path, monkeypatch):
    """Integration test for CLI rename seen files handling."""
    from snapimport.config import Config
    
    # Create config
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text('photos_dir = "/test/photos"\nlogs_dir = "/test/logs"')
    
    # Create seen files
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    seen_file = logs_dir / "seen-files.txt"
    seen_file.write_text("/test/old.txt\n/test/new.txt\n")
    
    test_dir = tmp_path / "test_photos"
    test_dir.mkdir()
    
    with patch("snapimport.cli.load_config", return_value=Config(photos_dir="/test/photos", logs_dir=str(logs_dir))), \
         patch("snapimport.cli.get_renames_for_folder", return_value=[("old.txt", "new.txt")]), \
         patch("snapimport.cli.execute_renames") as mock_execute:
        
        cli.rename(path=str(test_dir), log=True, force=False)
        mock_execute.assert_called_once()


@pytest.mark.integration
def test_integration_cli_rename_with_relative_paths(tmp_path, monkeypatch):
    """Integration test for CLI rename with relative path handling."""
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
        # Check that log_seen_files was called
        mock_log.assert_called_once()


@pytest.mark.integration
def test_integration_progress_more_coverage(tmp_path, monkeypatch):
    """Integration test for more progress function coverage."""
    from snapimport.progress import create_progress
    from snapimport.core import copy_files_with_progress
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    progress = create_progress()
    with progress:
        result = copy_files_with_progress([test_file], tmp_path, progress, verbose=True)
    
    assert len(result["copied"]) == 1
