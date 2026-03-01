"""Configuration management for SnapImport.

Provides Config class and utilities for loading/saving configuration
from ~/.config/snapimport/config.toml.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource
from platformdirs import user_config_dir
import tomlkit

class Config(BaseSettings):
    """Configuration model for SnapImport.
    
    Attributes:
        photos_dir: Path to the destination photos directory.
        logs_dir: Path to the logs directory for seen-files.txt and import-errors.log.
    """
    photos_dir: str
    logs_dir: str

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls, toml_file=str(Path(user_config_dir("snapimport")) / "config.toml")),
        )

def get_config_path() -> Path:
    """Get the path to the config.toml file.
    
    Returns:
        Path to ~/.config/snapimport/config.toml
    """
    return Path(user_config_dir("snapimport")) / "config.toml"

def config_exists() -> bool:
    """Check if the config file exists.
    
    Returns:
        True if config.toml exists, False otherwise.
    """
    return get_config_path().exists()

def load_config() -> Config | None:
    """Load configuration from file.
    
    Returns:
        Config instance if file exists and is valid, None otherwise.
    """
    if not config_exists():
        return None
    try:
        return Config()
    except Exception:
        return None

def save_config(config: Config) -> None:
    """Save configuration to file.
    
    Args:
        config: Config instance to save.
        
    Note:
        Creates the config directory if it doesn't exist.
        Overwrites existing config file.
    """
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = tomlkit.document()
    doc.add(tomlkit.comment("SnapImport Configuration"))
    doc.add(tomlkit.comment("Edit these paths anytime. Nothing else needed for v1."))
    doc.add(tomlkit.nl())
    doc["photos_dir"] = config.photos_dir
    doc["logs_dir"] = config.logs_dir
    path.write_text(doc.as_string())
