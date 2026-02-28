from pathlib import Path
import textwrap
from unittest.mock import patch, MagicMock

import pytest

from snapimport import cli as cli_module
from snapimport.config import Config as ConfigModel
from snapimport import core
from typer.testing import CliRunner


def _make_config(photos_path: Path, logs_path: Path) -> ConfigModel:
    photos_path.mkdir(parents=True, exist_ok=True)
    logs_path.mkdir(parents=True, exist_ok=True)
    return ConfigModel(photos_dir=str(photos_path), logs_dir=str(logs_path))


@pytest.mark.cli
def test_no_sd_card_panel(tmp_path, monkeypatch):
    runner = CliRunner()
    # Prepare a dummy config
    cfg = _make_config(tmp_path / "photos", tmp_path / "logs")
    monkeypatch.setattr(cli_module, "load_config", lambda: cfg)
    monkeypatch.setattr(core, "detect_sds", lambda: [])
    result = runner.invoke(cli_module.app, ["import"])
    assert result.exit_code == 1
    assert "No SD Card Detected" in result.output


@pytest.mark.cli
def test_setup_command_overwrites_config(tmp_path, monkeypatch):
    runner = CliRunner()
    # Patch get_config_path in config module (where save_config uses it)
    from snapimport import config as config_module

    monkeypatch.setattr(
        config_module, "get_config_path", lambda: tmp_path / "config.toml"
    )
    photos_dir = tmp_path / "photos"
    logs_dir = tmp_path / "logs"
    photos_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    # Patch Prompt.ask to return deterministic paths
    side_effects = [str(photos_dir), str(logs_dir)]

    with patch("snapimport.progress.Prompt.ask", side_effect=side_effects):
        result = runner.invoke(cli_module.app, ["setup"])
    assert result.exit_code == 0
    # Read the written config.toml
    content = (tmp_path / "config.toml").read_text()
    assert "photos_dir" in content and "logs_dir" in content
    assert "Config updated!" in result.output


@pytest.mark.cli
def test_first_run_panel_shows_once(tmp_path, monkeypatch):
    runner = CliRunner()
    # Patch get_config_path in cli module (where it's imported and used)
    monkeypatch.setattr(cli_module, "get_config_path", lambda: tmp_path / "config.toml")
    photos_dir = tmp_path / "photos_first_run"
    logs_dir = tmp_path / "logs_first_run"
    photos_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    with patch(
        "snapimport.progress.Prompt.ask", side_effect=[str(photos_dir), str(logs_dir)]
    ):
        # First run
        res1 = runner.invoke(cli_module.app, ["setup"])
    print("First run output:", res1.output)
    assert res1.exit_code == 0
    assert "SnapImport is Ready" in res1.output
    # Second run should not show Ready panel
    with patch(
        "snapimport.progress.Prompt.ask", side_effect=[str(photos_dir), str(logs_dir)]
    ):
        res2 = runner.invoke(cli_module.app, ["setup"])
    assert res2.exit_code == 0
    assert "SnapImport is Ready" not in res2.output


@pytest.mark.cli
def test_dry_run_summary_prefix(tmp_path, monkeypatch):
    runner = CliRunner()
    sd = tmp_path / "SD"
    (sd / "DCIM" / "IMG_001.JPG").parent.mkdir(parents=True, exist_ok=True)
    (sd / "DCIM" / "IMG_001.JPG").write_text("fake")
    cfg = _make_config(tmp_path / "dest_dry_run", tmp_path / "logs_dry_run")
    monkeypatch.setattr(cli_module, "load_config", lambda: cfg)
    monkeypatch.setattr(core, "detect_sds", lambda: [str(sd)])
    result = runner.invoke(cli_module.app, ["import", "--dry-run"])
    assert result.exit_code == 0
    assert "[DRY RUN]" in result.output
    # Destination should be untouched
    assert (
        not (cfg.photos_dir and Path(cfg.photos_dir).exists())
        or len(list(Path(cfg.photos_dir).rglob("*"))) == 0
    )


@pytest.mark.cli
def test_verbose_per_file_output(tmp_path, monkeypatch):
    runner = CliRunner()
    sd = tmp_path / "SD2"
    (sd / "DCIM" / "IMG_001.JPG").parent.mkdir(parents=True, exist_ok=True)
    (sd / "DCIM" / "IMG_001.JPG").write_text("a")
    (sd / "DCIM" / "IMG_002.JPG").write_text("b")
    cfg = _make_config(tmp_path / "dest_verbose", tmp_path / "logs_verbose")
    monkeypatch.setattr(cli_module, "load_config", lambda: cfg)
    monkeypatch.setattr(core, "detect_sds", lambda: [str(sd)])
    monkeypatch.setattr(core, "confirm_import", lambda: True)
    result = runner.invoke(cli_module.app, ["import", "--verbose"])
    assert result.exit_code == 0
    # Expect per-file lines with an arrow
    assert result.output.count("→") >= 1
    assert "IMG_001.JPG" in result.output


@pytest.mark.cli
def test_reset_demo_command(tmp_path, monkeypatch):
    """Pre-create fake config.toml and first-run marker in tmp_path, run reset-demo --force."""
    runner = CliRunner()

    config_dir = tmp_path / "snapimport"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"
    config_path.write_text('photos_dir = "/tmp/photos"\nlogs_dir = "/tmp/logs"\n')

    marker = config_dir / ".first_run_done"
    marker.write_text("done")

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    seen_file = logs_dir / "seen-files.txt"
    seen_file.write_text("/some/path/IMG_001.JPG\n")
    import_errors = logs_dir / "import-errors.log"
    import_errors.write_text("error log content\n")

    def mock_get_config_path():
        return config_path

    def mock_load_config():
        from types import SimpleNamespace

        return SimpleNamespace(photos_dir="/tmp/photos", logs_dir=str(logs_dir))

    def mock_user_config_dir(appname=None, roaming=False):
        return str(config_dir)

    monkeypatch.setattr(cli_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr("snapimport.config.get_config_path", mock_get_config_path)
    monkeypatch.setattr("snapimport.config.user_config_dir", mock_user_config_dir)

    result = runner.invoke(cli_module.app, ["reset-demo", "--force"])

    assert result.exit_code == 0
    assert "Reset Complete" in result.output
    assert not config_path.exists()
    assert not marker.exists()
    assert not seen_file.exists()
    assert not import_errors.exists()


@pytest.mark.cli
def test_reset_demo_aborts_on_no(tmp_path, monkeypatch):
    """Run reset-demo without --force, feed 'n' as input. Assert nothing is deleted."""
    runner = CliRunner()

    config_dir = tmp_path / "snapimport"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"
    config_path.write_text('photos_dir = "/tmp/photos"\nlogs_dir = "/tmp/logs"\n')

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    def mock_get_config_path():
        return config_path

    def mock_load_config():
        from types import SimpleNamespace

        return SimpleNamespace(photos_dir="/tmp/photos", logs_dir=str(logs_dir))

    def mock_user_config_dir(appname=None, roaming=False):
        return str(config_dir)

    monkeypatch.setattr(cli_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr("snapimport.config.get_config_path", mock_get_config_path)
    monkeypatch.setattr("snapimport.config.user_config_dir", mock_user_config_dir)

    result = runner.invoke(cli_module.app, ["reset-demo"], input="n\n")

    assert result.exit_code == 0
    assert "Aborted" in result.output
    assert config_path.exists()


@pytest.mark.cli
def test_reset_demo_missing_files_ok(tmp_path, monkeypatch):
    """Run reset-demo --force when no state files exist. Assert no errors, exits cleanly."""
    runner = CliRunner()

    config_dir = tmp_path / "snapimport_empty"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"

    def mock_get_config_path():
        return config_path

    def mock_load_config():
        return None

    def mock_user_config_dir(appname=None, roaming=False):
        return str(config_dir)

    monkeypatch.setattr(cli_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(cli_module, "load_config", mock_load_config)
    monkeypatch.setattr("snapimport.config.get_config_path", mock_get_config_path)
    monkeypatch.setattr("snapimport.config.user_config_dir", mock_user_config_dir)

    result = runner.invoke(cli_module.app, ["reset-demo", "--force"])

    assert result.exit_code == 0
    assert "No state files found" in result.output
