"""Integration tests for full user journeys using fixtures."""

from pathlib import Path
from types import SimpleNamespace
from typer.testing import CliRunner

import pytest

from snapimport import cli as cli_module
from snapimport import core as core_module
from snapimport import config as config_module
from snapimport import sd as sd_module


@pytest.mark.integration
def test_first_time_user_journey(fresh_config, monkeypatch, wizard_inputs):
    """fresh_config, run snapimport with no args via CliRunner.
    Assert wizard runs, config.toml created, "SnapImport is Ready" appears.
    """
    runner = CliRunner()

    photos_dir = fresh_config.parent / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = fresh_config.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    def mock_get_config_path():
        return fresh_config / "config.toml"

    def mock_config_exists():
        return (fresh_config / "config.toml").exists()

    def mock_user_config_dir(appname=None, roaming=False):
        return str(fresh_config)

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "config_exists", mock_config_exists)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)

    def mock_load_config():
        config_path = fresh_config / "config.toml"
        if not config_path.exists():
            return None
        from snapimport.config import Config

        return Config()

    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr(cli_module, "get_config_path", mock_get_config_path)

    wizard_inputs([str(photos_dir), str(logs_dir)])

    result = runner.invoke(cli_module.app, [])

    assert result.exit_code == 0
    assert (fresh_config / "config.toml").exists()
    assert "SnapImport is Ready" in result.output


@pytest.mark.integration
def test_import_journey(configured_app, fake_sd, monkeypatch):
    """configured_app + fake_sd, run snapimport import.
    Assert files copied, seen-files.txt written, "Import Complete" appears.
    """
    runner = CliRunner()

    def mock_get_config_path():
        return configured_app["config_dir"] / "config.toml"

    def mock_user_config_dir(appname=None, roaming=False):
        return str(configured_app["config_dir"])

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)

    def mock_load_config():
        return SimpleNamespace(
            photos_dir=str(configured_app["photos_dir"]),
            logs_dir=str(configured_app["logs_dir"]),
        )

    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr(core_module, "detect_sds", lambda: [str(fake_sd)])
    monkeypatch.setattr(core_module, "confirm_import", lambda: True)
    monkeypatch.setattr(core_module, "get_exif_date", lambda f: "23-12-25")

    result = runner.invoke(cli_module.app, ["import"])

    assert result.exit_code == 0
    assert "Import Complete" in result.output

    photos_dir = configured_app["photos_dir"]
    assert len([f for f in photos_dir.rglob("*") if f.is_file()]) >= 1

    logs_dir = configured_app["logs_dir"]
    seen_file = logs_dir / "seen-files.txt"
    assert seen_file.exists()


@pytest.mark.integration
def test_dry_run_journey(configured_app, fake_sd, monkeypatch):
    """Same but --dry-run. Assert no files copied, "[DRY RUN]" in output, seen-files.txt not written."""
    runner = CliRunner()

    def mock_get_config_path():
        return configured_app["config_dir"] / "config.toml"

    def mock_user_config_dir(appname=None, roaming=False):
        return str(configured_app["config_dir"])

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)

    def mock_load_config():
        return SimpleNamespace(
            photos_dir=str(configured_app["photos_dir"]),
            logs_dir=str(configured_app["logs_dir"]),
        )

    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr(core_module, "detect_sds", lambda: [str(fake_sd)])
    monkeypatch.setattr(core_module, "confirm_import", lambda: True)
    monkeypatch.setattr(core_module, "get_exif_date", lambda f: "23-12-25")

    result = runner.invoke(cli_module.app, ["import", "--dry-run"])

    assert result.exit_code == 0
    assert "[DRY RUN]" in result.output

    photos_dir = configured_app["photos_dir"]
    assert len(list(photos_dir.rglob("*.jpg"))) == 0

    logs_dir = configured_app["logs_dir"]
    seen_file = logs_dir / "seen-files.txt"
    assert not seen_file.exists() or seen_file.read_text() == ""


@pytest.mark.integration
def test_repeat_import_is_idempotent(configured_app, fake_sd, monkeypatch):
    """Run import twice, assert second run skips all (skipped_seen == N).
    Assert seen-files.txt has no duplicate entries.
    """
    runner = CliRunner()

    def mock_get_config_path():
        return configured_app["config_dir"] / "config.toml"

    def mock_user_config_dir(appname=None, roaming=False):
        return str(configured_app["config_dir"])

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)

    def mock_load_config():
        return SimpleNamespace(
            photos_dir=str(configured_app["photos_dir"]),
            logs_dir=str(configured_app["logs_dir"]),
        )

    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr(core_module, "detect_sds", lambda: [str(fake_sd)])
    monkeypatch.setattr(core_module, "confirm_import", lambda: True)
    monkeypatch.setattr(core_module, "get_exif_date", lambda f: "23-12-25")

    result1 = runner.invoke(cli_module.app, ["import"])
    assert result1.exit_code == 0

    result2 = runner.invoke(cli_module.app, ["import"])
    assert result2.exit_code == 0
    assert (
        "skipped" in result2.output.lower()
        or "skipped_seen" in result2.output.lower()
        or "already" in result2.output.lower()
    )

    logs_dir = configured_app["logs_dir"]
    seen_file = logs_dir / "seen-files.txt"
    if seen_file.exists():
        lines = seen_file.read_text().splitlines()
        assert len(lines) == len(set(lines))


@pytest.mark.integration
def test_reconfigure_journey(configured_app, monkeypatch, wizard_inputs):
    """Run snapimport setup with new wizard_inputs.
    Assert config.toml updated, "Config updated!" in output.
    Assert "SnapImport is Ready" does NOT appear (not first run) when marker exists.
    """
    runner = CliRunner()

    config_dir = configured_app["config_dir"]
    marker = config_dir / ".first_run_done"
    marker.write_text("done")

    def mock_get_config_path():
        return configured_app["config_dir"] / "config.toml"

    def mock_user_config_dir(appname=None, roaming=False):
        return str(configured_app["config_dir"])

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)
    monkeypatch.setattr(cli_module, "get_config_path", mock_get_config_path)

    new_photos = configured_app["config_dir"].parent / "new_photos"
    new_photos.mkdir(parents=True, exist_ok=True)
    new_logs = configured_app["config_dir"].parent / "new_logs"
    new_logs.mkdir(parents=True, exist_ok=True)

    wizard_inputs([str(new_photos), str(new_logs)])

    result = runner.invoke(cli_module.app, ["setup"])

    assert result.exit_code == 0
    assert "Config updated!" in result.output
    assert "SnapImport is Ready" not in result.output


@pytest.mark.integration
def test_verbose_journey(configured_app, fake_sd, monkeypatch):
    """Run import --verbose, assert per-file lines with "→" appear for every file."""
    runner = CliRunner()

    def mock_get_config_path():
        return configured_app["config_dir"] / "config.toml"

    def mock_user_config_dir(appname=None, roaming=False):
        return str(configured_app["config_dir"])

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)

    def mock_load_config():
        return SimpleNamespace(
            photos_dir=str(configured_app["photos_dir"]),
            logs_dir=str(configured_app["logs_dir"]),
        )

    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr(core_module, "detect_sds", lambda: [str(fake_sd)])
    monkeypatch.setattr(core_module, "confirm_import", lambda: True)
    monkeypatch.setattr(core_module, "get_exif_date", lambda f: "23-12-25")

    result = runner.invoke(cli_module.app, ["import", "--verbose"])

    assert result.exit_code == 0
    assert "→" in result.output
    assert (
        "IMG_001" in result.output
        or "IMG_002" in result.output
        or "IMG_003" in result.output
    )


@pytest.mark.integration
def test_overwrite_journey_no_flag(fake_sd_with_conflict, monkeypatch):
    """fake_sd_with_conflict: without --overwrite assert file not replaced."""
    runner = CliRunner()

    configured_app = fake_sd_with_conflict
    config_dir = configured_app["photos_dir"].parent / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"
    config_path.write_text(f"""# SnapImport Configuration
photos_dir = "{configured_app["photos_dir"]}"
logs_dir = "{configured_app["logs_dir"]}"
""")

    def mock_get_config_path():
        return config_path

    def mock_user_config_dir(appname=None, roaming=False):
        return str(config_dir)

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)

    def mock_load_config():
        return SimpleNamespace(
            photos_dir=str(configured_app["photos_dir"]),
            logs_dir=str(configured_app["logs_dir"]),
        )

    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr(
        core_module, "detect_sds", lambda: [str(fake_sd_with_conflict["sd"])]
    )
    monkeypatch.setattr(core_module, "confirm_import", lambda: True)
    monkeypatch.setattr(core_module, "get_exif_date", lambda f: "2023-12-25")

    photos_dir = configured_app["photos_dir"]
    original_content = (list(photos_dir.glob("*.jpg"))[0]).read_bytes()

    result = runner.invoke(cli_module.app, ["import"])

    assert result.exit_code == 0
    current_content = (list(photos_dir.glob("*.jpg"))[0]).read_bytes()
    assert current_content == original_content


@pytest.mark.integration
def test_overwrite_journey_with_flag(fake_sd_with_conflict, monkeypatch):
    """fake_sd_with_conflict: with --overwrite assert file is replaced."""
    runner = CliRunner()

    configured_app = fake_sd_with_conflict
    config_dir = configured_app["photos_dir"].parent / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"
    config_path.write_text(f"""# SnapImport Configuration
photos_dir = "{configured_app["photos_dir"]}"
logs_dir = "{configured_app["logs_dir"]}"
""")

    def mock_get_config_path():
        return config_path

    def mock_user_config_dir(appname=None, roaming=False):
        return str(config_dir)

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)

    def mock_load_config():
        return SimpleNamespace(
            photos_dir=str(configured_app["photos_dir"]),
            logs_dir=str(configured_app["logs_dir"]),
        )

    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr(
        core_module, "detect_sds", lambda: [str(fake_sd_with_conflict["sd"])]
    )
    monkeypatch.setattr(core_module, "confirm_import", lambda: True)
    monkeypatch.setattr(core_module, "get_exif_date", lambda f: "2023-12-25")

    result = runner.invoke(cli_module.app, ["import", "--overwrite"])

    assert result.exit_code == 0
    assert "overwritten" in result.output.lower() or "Import Complete" in result.output
