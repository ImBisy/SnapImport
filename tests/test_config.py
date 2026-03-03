"""Unit tests for configuration management (snapimport.config module).

Tests Config class, config file operations, and path utilities.

Relies on: tmp_path, monkeypatch fixtures.
Run just this file: pytest tests/test_config.py -v
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from snapimport import 


@pytest.mark.unit
def test_get_config_path():
    """Test get_config_path returns correct path."""
    result = config.get_config_path()
    assert isinstance(result, Path)
    assert str(result).endswith("config.toml")
    assert "snapimport" in str(result)


@pytest.mark.unit
def test_config_exists_true(tmp_path, monkeypatch):
    """Test config_exists returns True when file exists."""
    # Mock user_config_dir to return our tmp_path
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    config_file = fake_config_dir / "config.toml"
    config_file.write_text("photos_dir = '/test'\nlogs_dir = '/test/logs'")
    
    with patch("snapimport.config.user_config_dir", return_value=str(fake_config_dir)):
        assert config.config_exists() is True


@pytest.mark.unit
def test_config_exists_false(tmp_path, monkeypatch):
    """Test config_exists returns False when file doesn't exist."""
    # Mock user_config_dir to return our tmp_path
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    
    with patch("snapimport.config.user_config_dir", return_value=str(fake_config_dir)):
        assert config.config_exists() is False


@pytest.mark.unit
def test_load_config_success(tmp_path, monkeypatch):
    """Test load_config returns Config instance when file exists and is valid."""
    # Mock user_config_dir to return our tmp_path
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    config_file = fake_config_dir / "config.toml"
    config_file.write_text("photos_dir = '/test'\nlogs_dir = '/test/logs'")
    
    with patch("snapimport.config.user_config_dir", return_value=str(fake_config_dir)):
        result = config.load_config()
        assert result is not None
        assert isinstance(result, config.Config)
        assert result.photos_dir == "/test"
        assert result.logs_dir == "/test/logs"


@pytest.mark.unit
def test_load_config_no_file(tmp_path, monkeypatch):
    """Test load_config returns None when config file doesn't exist."""
    # Mock user_config_dir to return our tmp_path
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    
    with patch("snapimport.config.user_config_dir", return_value=str(fake_config_dir)):
        result = config.load_config()
        assert result is None


@pytest.mark.unit
def test_load_config_invalid_file(tmp_path, monkeypatch):
    """Test load_config returns None when config file is invalid."""
    # Mock user_config_dir to return our tmp_path
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    config_file = fake_config_dir / "config.toml"
    config_file.write_text("invalid toml content [[[")
    
    with patch("snapimport.config.user_config_dir", return_value=str(fake_config_dir)):
        result = config.load_config()
        assert result is None


@pytest.mark.unit
def test_save_config_new_file(tmp_path, monkeypatch):
    """Test save_config creates new config file."""
    # Mock user_config_dir to return our tmp_path
    fake_config_dir = tmp_path / "config"
    
    with patch("snapimport.config.user_config_dir", return_value=str(fake_config_dir)):
        test_config = config.Config(photos_dir="/test/photos", logs_dir="/test/logs")
        config.save_config(test_config)
        
        config_file = fake_config_dir / "config.toml"
        assert config_file.exists()
        
        content = config_file.read_text()
        assert "photos_dir = \"/test/photos\"" in content
        assert "logs_dir = \"/test/logs\"" in content
        assert "SnapImport Configuration" in content


@pytest.mark.unit
def test_save_config_overwrite_existing(tmp_path, monkeypatch):
    """Test save_config overwrites existing config file."""
    # Mock user_config_dir to return our tmp_path
    fake_config_dir = tmp_path / "config"
    fake_config_dir.mkdir()
    config_file = fake_config_dir / "config.toml"
    config_file.write_text("old content")
    
    with patch("snapimport.config.user_config_dir", return_value=str(fake_config_dir)):
        # Create config with init_settings to avoid loading from file
        test_config = config.Config.model_construct(
            photos_dir="/new/photos", 
            logs_dir="/new/logs"
        )
        config.save_config(test_config)
        
        content = config_file.read_text()
        assert "old content" not in content
        assert "photos_dir = \"/new/photos\"" in content
        assert "logs_dir = \"/new/logs\"" in content


@pytest.mark.unit
def test_config_class_init():
    """Test Config class initialization."""
    cfg = config.Config(photos_dir="/test", logs_dir="/logs")
    assert cfg.photos_dir == "/test"
    assert cfg.logs_dir == "/logs"


@pytest.mark.unit
def test_config_settings_customise_sources():
    """Test Config.settings_customise_sources returns correct sources."""
    sources = config.Config.settings_customise_sources(
        config.Config,
        None,  # init_settings
        None,  # env_settings
        None,  # dotenv_settings
        None,  # file_secret_settings
    )
    assert len(sources) == 2
    # First source should be init_settings
    # Second source should be TomlConfigSettingsSource
