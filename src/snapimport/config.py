from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import TomlConfigSettingsSource
from platformdirs import user_config_dir
import tomlkit

class Config(BaseSettings):
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
    return Path(user_config_dir("snapimport")) / "config.toml"

def config_exists() -> bool:
    return get_config_path().exists()

def load_config() -> Config | None:
    if not config_exists():
        return None
    try:
        return Config()
    except Exception:
        return None

def save_config(config: Config) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = tomlkit.document()
    doc.add(tomlkit.comment("SnapImport Configuration"))
    doc.add(tomlkit.comment("Edit these paths anytime. Nothing else needed for v1."))
    doc.add(tomlkit.nl())
    doc["photos_dir"] = config.photos_dir
    doc["logs_dir"] = config.logs_dir
    path.write_text(doc.as_string())
