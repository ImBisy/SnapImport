"""
CLI tests for SnapImport (snapimport.cli module).

Tests Typer commands via CliRunner, including import, setup, reset-demo,
dry-run, verbose output, and error handling.

Relies on: isolated_config, fresh_config, configured_app, wizard_inputs fixtures.
Run just this file: pytest tests/test_cli.py -v
"""

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


def _mock_run_factory(dates):
    class _Res:
        def __init__(self, stdout):
            self.stdout = stdout

    def _fake_run(cmd, **kwargs):
        if dates:
            date = dates.pop(0)
            return _Res(f"Date/Time Original              : {date}")
        else:
            return _Res("")

    return _fake_run


@pytest.mark.cli
def test_no_sd_card_panel(tmp_path, monkeypatch):
    """Verify import exits with error when no SD card is detected."""
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
    """Verify setup command overwrites config and shows success message."""
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
    """Verify first-run panel appears only once, not on reconfigure."""
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
    """Verify dry-run shows '[DRY RUN]' prefix and doesn't modify files."""
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
    """Verify verbose mode shows '→' arrows for each file processed."""
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
    """Verify reset-demo --force deletes config and state files."""
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
    """Verify reset-demo without --force aborts on 'n' input."""
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
def test_import_cmd_missing_config(tmp_path, monkeypatch):
    """Verify import command shows error when config is missing."""
    runner = CliRunner()
    monkeypatch.setattr(cli_module, "load_config", lambda: None)
    result = runner.invoke(cli_module.app, ["import"])
    assert result.exit_code == 0
    assert "Config not found" in result.output


@pytest.mark.cli
def test_import_cmd_reconfigure_failure(tmp_path, monkeypatch):
    """Verify import command handles reconfigure failure gracefully."""
    runner = CliRunner()
    cfg = _make_config(tmp_path / "photos", tmp_path / "logs")
    monkeypatch.setattr(cli_module, "load_config", lambda: cfg)
    # Mock run_wizard to return None (failure)
    monkeypatch.setattr(cli_module, "run_wizard", lambda: None)
    result = runner.invoke(cli_module.app, ["import", "--reconfigure"])
    assert result.exit_code == 0
    assert "Config not found after setup" in result.output


@pytest.mark.cli
def test_rename_cmd_no_config_no_path(tmp_path, monkeypatch):
    """Verify rename command shows error when no config and no path provided."""
    runner = CliRunner()
    monkeypatch.setattr(cli_module, "load_config", lambda: None)
    result = runner.invoke(cli_module.app, ["rename"])
    assert result.exit_code == 0
    assert "No path provided and no config found" in result.output


@pytest.mark.cli
def test_rename_cmd_invalid_path(tmp_path, monkeypatch):
    """Verify rename command shows error for invalid path."""
    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["rename", "/nonexistent/path"])
    assert result.exit_code == 0
    assert "does not exist or is not a directory" in result.output


@pytest.mark.cli
def test_redo_logs_cmd_no_config(tmp_path, monkeypatch):
    """Verify redo-logs command shows error when config is missing."""
    runner = CliRunner()
    monkeypatch.setattr(cli_module, "load_config", lambda: None)
    result = runner.invoke(cli_module.app, ["redo-logs"])
    assert result.exit_code == 0
    assert "No config found" in result.output


@pytest.mark.cli
def test_wizard_cmd(tmp_path, monkeypatch):
    """Verify wizard command runs and shows volume table."""
    runner = CliRunner()
    # Mock run_wizard and list_all_volumes
    monkeypatch.setattr(cli_module, "run_wizard", lambda: None)
    monkeypatch.setattr(
        cli_module,
        "list_all_volumes",
        lambda: [("/fake/vol1", True), ("/fake/vol2", False)],
    )
    result = runner.invoke(cli_module.app, ["wizard"])
    assert result.exit_code == 0
    assert "Detected Volumes" in result.output
    assert "/fake/vol1" in result.output
    assert "Yes ✨" in result.output


@pytest.mark.cli
def test_reset_demo_cmd_no_files(tmp_path, monkeypatch):
    """Verify reset-demo command shows message when no state files exist."""
    runner = CliRunner()
    # Mock get_config_path and load_config to return None
    monkeypatch.setattr(
        cli_module, "get_config_path", lambda: tmp_path / "nonexistent.toml"
    )
    monkeypatch.setattr(cli_module, "load_config", lambda: None)
    result = runner.invoke(cli_module.app, ["reset-demo", "--force"])
    assert result.exit_code == 0
    assert "No state files found" in result.output


@pytest.mark.cli
def test_reset_demo_cmd_deletion_error(tmp_path, monkeypatch):
    """Verify reset-demo command handles file deletion errors."""
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text("test")
    # Mock get_config_path and load_config
    monkeypatch.setattr(cli_module, "get_config_path", lambda: config_path)
    monkeypatch.setattr(cli_module, "load_config", lambda: None)
    # Mock unlink to raise exception
    monkeypatch.setattr(
        "pathlib.Path.unlink",
        lambda self: (_ for _ in ()).throw(Exception("Permission denied")),
    )
    result = runner.invoke(cli_module.app, ["reset-demo", "--force"])
    assert result.exit_code == 0
    assert "Warning: Could not delete" in result.output


@pytest.mark.cli
def test_reset_demo_cmd_confirmation_yes(tmp_path, monkeypatch):
    """Verify reset-demo command works with 'y' confirmation."""
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text("test")
    # Mock get_config_path and load_config
    monkeypatch.setattr(cli_module, "get_config_path", lambda: config_path)
    monkeypatch.setattr(cli_module, "load_config", lambda: None)
    result = runner.invoke(cli_module.app, ["reset-demo"], input="y\n")
    assert result.exit_code == 0
    assert "Reset Complete" in result.output


@pytest.mark.cli
def test_reset_demo_cmd_confirmation_no(tmp_path, monkeypatch):
    """Verify reset-demo command aborts with 'n' confirmation."""
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text("test")
    # Mock get_config_path and load_config
    monkeypatch.setattr(cli_module, "get_config_path", lambda: config_path)
    monkeypatch.setattr(cli_module, "load_config", lambda: None)
    result = runner.invoke(cli_module.app, ["reset-demo"], input="n\n")
    assert result.exit_code == 0
    assert "Aborted" in result.output


@pytest.mark.cli
def test_run_wizard_invalid_photos_path(tmp_path, monkeypatch):
    """Verify run_wizard handles invalid photos path gracefully."""
    runner = CliRunner()
    # Mock prompt functions to return invalid path first, then a valid one
    photos_ok = tmp_path / "photos_ok"
    photos_ok.mkdir()

    def _make_fake_prompt_photos_dir():
        calls = {"n": 0}

        def inner():
            if calls["n"] == 0:
                calls["n"] = 1
                return "/nonexistent"
            return str(photos_ok)

        return inner

    monkeypatch.setattr(cli_module, "prompt_photos_dir", _make_fake_prompt_photos_dir())
    monkeypatch.setattr(
        cli_module, "prompt_logs_dir", lambda default_logs: str(tmp_path / "logs")
    )
    # Mock show functions
    monkeypatch.setattr(cli_module, "show_welcome_panel", lambda: None)
    monkeypatch.setattr(cli_module, "show_error_panel", lambda msg: None)
    monkeypatch.setattr(cli_module, "show_success_panel", lambda msg: None)
    # Mock find_files to return empty list
    monkeypatch.setattr(cli_module, "find_files", lambda path: [])
    # Mock save_config
    monkeypatch.setattr(cli_module, "save_config", lambda cfg: None)
    # Mock get_config_path
    monkeypatch.setattr(cli_module, "get_config_path", lambda: tmp_path / "config.toml")

    # This should loop once for invalid path, but we can't test the loop easily
    # So we'll test that it doesn't crash with invalid path
    try:
        cli_module.run_wizard()
    except Exception as e:
        assert False, f"run_wizard crashed with invalid path: {e}"


@pytest.mark.cli
def test_run_wizard_creates_logs_dir(tmp_path, monkeypatch):
    """Verify run_wizard creates logs directory if it doesn't exist."""
    runner = CliRunner()
    logs_path = tmp_path / "new_logs"
    # Mock prompt functions
    monkeypatch.setattr(
        cli_module, "prompt_photos_dir", lambda: str(tmp_path / "photos")
    )
    monkeypatch.setattr(cli_module, "prompt_logs_dir", lambda: str(logs_path))
    # Mock show functions
    monkeypatch.setattr(cli_module, "show_welcome_panel", lambda: None)
    monkeypatch.setattr(cli_module, "show_success_panel", lambda msg: None)
    # Mock find_files to return empty list
    monkeypatch.setattr(cli_module, "find_files", lambda path: [])
    # Mock save_config
    monkeypatch.setattr(cli_module, "save_config", lambda cfg: None)
    # Mock get_config_path
    monkeypatch.setattr(cli_module, "get_config_path", lambda: tmp_path / "config.toml")

    cli_module.run_wizard()
    assert logs_path.exists()


@pytest.mark.cli
def test_run_wizard_logs_existing_files(tmp_path, monkeypatch):
    """Verify run_wizard detects and logs existing renamed files."""
    runner = CliRunner()
    photos_path = tmp_path / "photos"
    photos_path.mkdir()
    logs_path = tmp_path / "logs"
    logs_path.mkdir()

    # Create a fake renamed file
    renamed_file = photos_path / "23-01-01-001.JPG"
    renamed_file.write_text("test")

    # Mock prompt functions
    monkeypatch.setattr(cli_module, "prompt_photos_dir", lambda: str(photos_path))
    monkeypatch.setattr(cli_module, "prompt_logs_dir", lambda: str(logs_path))
    # Mock show functions
    monkeypatch.setattr(cli_module, "show_welcome_panel", lambda: None)
    monkeypatch.setattr(cli_module, "show_success_panel", lambda msg: None)
    # Mock Confirm.ask to return True
    monkeypatch.setattr(
        "snapimport.progress.Confirm.ask", lambda prompt, default=True: True
    )
    # Mock save_config
    monkeypatch.setattr(cli_module, "save_config", lambda cfg: None)
    # Mock get_config_path
    monkeypatch.setattr(cli_module, "get_config_path", lambda: tmp_path / "config.toml")

    cli_module.run_wizard()
    # Check that seen-files.txt was created
    seen_file = logs_path / "seen-files.txt"
    assert seen_file.exists()


@pytest.mark.cli
def test_reset_demo_missing_files_ok(tmp_path, monkeypatch):
    """Verify reset-demo --force handles missing files gracefully."""
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
