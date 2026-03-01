"""Unit tests for SD card detection (snapimport.sd module).

Tests macOS-specific volume scanning and camera file detection.

Relies on: tmp_path, monkeypatch fixtures.
Run just this file: pytest tests/test_sd.py -v
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from snapimport import sd


@pytest.mark.unit
def test_has_camera_files_true(tmp_path):
    """Verify has_camera_files detects supported file extensions."""
    # Create fake volume with supported files
    volume = tmp_path / "volume"
    volume.mkdir()
    dcim = volume / "DCIM"
    dcim.mkdir()
    (dcim / "test.JPG").touch()
    (dcim / "test.ORF").touch()
    (dcim / "not_supported.txt").touch()
    
    assert sd.has_camera_files(str(volume)) == True


@pytest.mark.unit
def test_has_camera_files_false(tmp_path):
    """Verify has_camera_files returns False when no supported files."""
    # Test volume with no supported files
    empty_volume = tmp_path / "empty"
    empty_volume.mkdir()
    (empty_volume / "DCIM").mkdir()
    (empty_volume / "DCIM" / "not_supported.txt").touch()
    
    assert sd.has_camera_files(str(empty_volume)) == False


@pytest.mark.unit
def test_has_camera_files_no_dcim(tmp_path):
    """Verify has_camera_files returns False when no DCIM folder."""
    # Test volume without DCIM folder
    volume = tmp_path / "no_dcim"
    volume.mkdir()
    (volume / "other.txt").touch()
    
    assert sd.has_camera_files(str(volume)) == False


@pytest.mark.unit
def test_detect_sds_with_camera_files(tmp_path, monkeypatch):
    """Verify detect_sds finds volumes with camera files."""
    # Mock /Volumes
    volumes_dir = tmp_path / "volumes"
    volumes_dir.mkdir()
    
    # Create fake volumes
    vol1 = volumes_dir / "SDCARD"
    vol1.mkdir()
    dcim1 = vol1 / "DCIM"
    dcim1.mkdir()
    (dcim1 / "photo.JPG").touch()
    
    vol2 = volumes_dir / "HDD"
    vol2.mkdir()  # No camera files
    
    vol3 = volumes_dir / "System"
    vol3.mkdir()  # System volume, should be excluded
    
    # Mock os.path.exists and os.listdir
    def mock_exists(path):
        return path == str(volumes_dir) or Path(path).exists()
    
    def mock_listdir(path):
        if path == str(volumes_dir):
            return ["SDCARD", "HDD", "System"]
        return []
    
    monkeypatch.setattr(os.path, "exists", mock_exists)
    monkeypatch.setattr(os.path, "listdir", mock_listdir)
    monkeypatch.setattr(os.path, "isdir", lambda p: Path(p).is_dir())
    
    volumes = sd.detect_sds()
    assert len(volumes) == 1
    assert str(vol1) in volumes


@pytest.mark.unit
def test_detect_sds_no_volumes_dir(tmp_path, monkeypatch):
    """Verify detect_sds returns empty list when /Volumes doesn't exist."""
    # Mock os.path.exists to return False for /Volumes
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    
    volumes = sd.detect_sds()
    assert volumes == []


@pytest.mark.unit
def test_list_all_volumes(tmp_path, monkeypatch):
    """Verify list_all_volumes returns all volumes with camera file status."""
    # Mock /Volumes
    volumes_dir = tmp_path / "volumes"
    volumes_dir.mkdir()
    
    # Create fake volumes
    vol1 = volumes_dir / "SDCARD"
    vol1.mkdir()
    dcim1 = vol1 / "DCIM"
    dcim1.mkdir()
    (dcim1 / "photo.JPG").touch()
    
    vol2 = volumes_dir / "HDD"
    vol2.mkdir()  # No camera files
    
    vol3 = volumes_dir / "System"
    vol3.mkdir()  # System volume, should be excluded
    
    # Mock os.path.exists and os.listdir
    def mock_exists(path):
        return path == str(volumes_dir) or Path(path).exists()
    
    def mock_listdir(path):
        if path == str(volumes_dir):
            return ["SDCARD", "HDD", "System"]
        return []
    
    monkeypatch.setattr(os.path, "exists", mock_exists)
    monkeypatch.setattr(os.path, "listdir", mock_listdir)
    monkeypatch.setattr(os.path, "isdir", lambda p: Path(p).is_dir())
    
    volumes = sd.list_all_volumes()
    assert len(volumes) == 2  # Excludes System
    # Check that SDCARD has camera files, HDD does not
    sdcard_entry = next(v for v in volumes if v[0] == str(vol1))
    hdd_entry = next(v for v in volumes if v[0] == str(vol2))
    assert sdcard_entry[1] == True
    assert hdd_entry[1] == False


@pytest.mark.unit
def test_list_all_volumes_no_volumes_dir(tmp_path, monkeypatch):
    """Verify list_all_volumes returns empty list when /Volumes doesn't exist."""
    # Mock os.path.exists to return False for /Volumes
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    
    volumes = sd.list_all_volumes()
    assert volumes == []


@pytest.mark.unit
def test_supported_extensions():
    """Verify SUPPORTED_EXTENSIONS contains expected image formats."""
    expected = {'.JPG', '.JPEG', '.TIF', '.TIFF', '.ORF', '.RAF', '.NEF', '.CR2', '.DNG', '.ARW'}
    assert sd.SUPPORTED_EXTENSIONS == expected


@pytest.mark.unit
def test_system_volumes():
    """Verify SYSTEM_VOLUMES contains expected macOS system volume prefixes."""
    expected = {'Macintosh', 'Macintosh HD', 'Macintosh SSD', 'APFS', 'Recovery'}
    assert sd.SYSTEM_VOLUMES == expected
