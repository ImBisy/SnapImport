"""Additional integration tests to reach 80% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from snapimport import cli, core


@pytest.mark.integration
def test_integration_sd_detection(tmp_path, monkeypatch):
    """Integration test for SD card detection functionality."""
    # Mock /Volumes directory
    volumes_dir = tmp_path / "volumes"
    volumes_dir.mkdir()
    
    # Create a fake SD card
    sd_card = volumes_dir / "SDCARD"
    sd_card.mkdir()
    dcim = sd_card / "DCIM"
    dcim.mkdir()
    (dcim / "test.JPG").touch()
    
    with patch("snapimport.sd.os.path.exists", return_value=True), \
         patch("snapimport.sd.os.listdir", return_value=["SDCARD"]), \
         patch("snapimport.sd.os.path.isdir", return_value=True), \
         patch("snapimport.sd.has_camera_files", return_value=True):
        
        from snapimport.sd import detect_sds
        volumes = detect_sds()
        assert len(volumes) >= 1


@pytest.mark.integration
def test_integration_config_lifecycle(tmp_path, monkeypatch):
    """Integration test for config creation, loading, and saving."""
    from snapimport.config import Config, save_config, load_config, config_exists
    
    # Mock user config dir
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    
    with patch("snapimport.config.user_config_dir", return_value=str(config_dir)):
        # Initially no config
        assert not config_exists()
        assert load_config() is None
        
        # Create config
        test_config = Config(photos_dir="/test/photos", logs_dir="/test/logs")
        save_config(test_config)
        
        # Now config exists and loads
        assert config_exists()
        loaded_config = load_config()
        assert loaded_config is not None
        assert loaded_config.photos_dir == "/test/photos"
        assert loaded_config.logs_dir == "/test/logs"


@pytest.mark.integration
def test_integration_rename_workflow(tmp_path, monkeypatch):
    """Integration test for complete rename workflow."""
    from snapimport.rename import rename_files_in_folder, find_files, get_renames_for_folder
    
    # Create test files
    test_file = tmp_path / "test.JPG"
    test_file.write_text("test")
    
    # Mock EXIF date extraction
    with patch("snapimport.rename.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Date/Time Original              : 24-02-24")
        
        # Test the workflow
        files = find_files(tmp_path)
        assert len(files) == 1
        
        renames = get_renames_for_folder(tmp_path)
        assert len(renames) == 1
        assert "24-02-24-001" in renames[0][1]


@pytest.mark.integration
def test_integration_progress_display(tmp_path, monkeypatch):
    """Integration test for progress display functionality."""
    from snapimport.progress import create_progress, show_error_panel, show_success_panel
    
    # Test progress creation
    progress = create_progress()
    assert progress is not None
    
    # Test panel displays (should not raise exceptions)
    show_error_panel("Test error")
    show_success_panel("Test success")


@pytest.mark.integration
def test_integration_import_with_errors(tmp_path, monkeypatch):
    """Integration test for import with error handling."""
    from snapimport.config import Config
    from snapimport.progress import write_import_errors
    
    # Create config
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    config = Config(photos_dir=str(tmp_path), logs_dir=str(logs_dir))
    
    # Test error logging
    failures = [
        {"file": "test1.txt", "reason": "Permission denied", "suggestion": "Check permissions"},
        {"file": "test2.txt", "reason": "Disk full", "suggestion": "Free up space"}
    ]
    
    write_import_errors(logs_dir, failures)
    
    # Verify error log was created
    error_log = logs_dir / "import-errors.log"
    assert error_log.exists()
    content = error_log.read_text()
    assert "test1.txt" in content
    assert "test2.txt" in content


@pytest.mark.integration
def test_integration_seen_files_tracking(tmp_path, monkeypatch):
    """Integration test for seen files tracking."""
    from snapimport.core import log_seen_files
    
    # Create test files
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    files = [tmp_path / "file1.txt", tmp_path / "file2.txt"]
    
    # Test logging
    log_seen_files(logs_dir, files)
    
    # Verify seen files log
    seen_file = logs_dir / "seen-files.txt"
    assert seen_file.exists()
    content = seen_file.read_text()
    assert "file1.txt" in content
    assert "file2.txt" in content


@pytest.mark.integration
def test_integration_volume_listing(tmp_path, monkeypatch):
    """Integration test for volume listing functionality."""
    from snapimport.sd import list_all_volumes, SYSTEM_VOLUMES
    
    # Mock /Volumes directory
    volumes_dir = tmp_path / "volumes"
    volumes_dir.mkdir()
    
    # Create test volumes
    system_vol = volumes_dir / "Macintosh HD"
    system_vol.mkdir()
    camera_vol = volumes_dir / "CAMERA"
    camera_vol.mkdir()
    (camera_vol / "DCIM").mkdir()
    (camera_vol / "DCIM" / "test.JPG").touch()
    
    with patch("snapimport.sd.os.path.exists", return_value=True), \
         patch("snapimport.sd.os.listdir", return_value=["Macintosh HD", "CAMERA"]), \
         patch("snapimport.sd.os.path.isdir", return_value=True), \
         patch("snapimport.sd.has_camera_files") as mock_has_files:
        
        mock_has_files.side_effect = lambda path: "CAMERA" in path
        
        volumes = list_all_volumes()
        assert len(volumes) >= 2
        
        # Check that volumes were processed
        volume_names = [v[0] for v in volumes]
        assert len(volume_names) >= 2


@pytest.mark.integration
def test_integration_file_operations(tmp_path, monkeypatch):
    """Integration test for file operations and error handling."""
    from snapimport.core import copy_file_with_progress
    from snapimport.progress import create_progress
    
    # Create test file
    source = tmp_path / "source.txt"
    source.write_text("test content")
    dest = tmp_path / "dest.txt"
    
    progress = create_progress()
    with progress:
        # Add a task first
        task_id = progress.add_task("Copying", total=source.stat().st_size)
        result = copy_file_with_progress(source, dest, progress, task_id)
    
    assert result is True
    assert dest.exists()
    assert dest.read_text() == "test content"


@pytest.mark.integration
def test_integration_exif_extraction(tmp_path, monkeypatch):
    """Integration test for EXIF date extraction."""
    from snapimport.rename import get_exif_date
    
    # Create test file
    test_file = tmp_path / "test.JPG"
    test_file.write_text("fake image")
    
    # Mock subprocess.run to simulate exiftool output
    with patch("snapimport.rename.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="Date/Time Original              : 24-02-24"
        )
        
        date = get_exif_date(test_file)
        assert date == "24-02-24"


@pytest.mark.integration
def test_integration_file_filtering(tmp_path, monkeypatch):
    """Integration test for file filtering and extension handling."""
    from snapimport.rename import find_files
    from snapimport.sd import EXTENSIONS
    
    # Create test files with different extensions
    (tmp_path / "test.JPG").touch()
    (tmp_path / "test.ORF").touch()
    (tmp_path / "test.txt").touch()
    (tmp_path / "test.XMP").touch()
    
    files = find_files(tmp_path)
    
    # Should only find supported camera files
    assert len(files) >= 3  # JPG, ORF, XMP
    file_names = [f.name for f in files]
    assert "test.JPG" in file_names
    assert "test.ORF" in file_names
    assert "test.txt" not in file_names
