import sys
import typer
from pathlib import Path
from typing import Optional

from nicegui import ui
from rich.panel import Panel
from rich.prompt import Confirm

from .config import Config, config_exists, load_config, save_config, get_config_path
from .core import import_photos
from .progress import (
    console,
    prompt_logs_dir,
    prompt_photos_dir,
    show_error_panel,
    show_header,
    show_success_panel,
    show_welcome_panel,
)
from .rename import rename_files_in_folder
from .sd import list_all_volumes

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    show_header()
    if ctx.invoked_subcommand is None:
        if not config_exists():
            run_wizard()
            console.print("Run `snapimport import` whenever you plug in an SD card.")
        else:
            console.print("Run `snapimport import` to import photos from SD card.")
            console.print("Use `snapimport --help` for more options.")


@app.command("import")
def import_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without doing it."
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Verbose per-file output."
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing files at the destination."
    ),
    reconfigure: bool = typer.Option(
        False, "--reconfigure", help="Re-run setup before importing."
    ),
):
    config = load_config()
    if not config:
        show_error_panel("Config not found. Run `snapimport` without args to set up.")
        return
    if reconfigure:
        run_wizard()
        config = load_config()
        if not config:
            show_error_panel("Config not found after setup.")
            return
    import_photos(config, dry_run, verbose=verbose, overwrite=overwrite)


@app.command()
def rename(
    path: str = typer.Argument(
        ..., help="Path to the folder containing photos to rename."
    ),
    log: bool = typer.Option(
        False,
        "--log",
        help="Log renamed files as imported (requires config).",
    ),
):
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        show_error_panel("The provided path does not exist or is not a directory.")
        return

    renames = rename_files_in_folder(folder)

    if log:
        config = load_config()
        if not config:
            show_error_panel("No config found. Run `snapimport` first to set up.")
            return
        from .core import log_seen_files

        logs_dir = Path(config.logs_dir)
        files_to_log = [Path(new) for old, new in renames]
        log_seen_files(logs_dir, files_to_log)
        show_success_panel(
            f"Renamed {len(renames)} files in {path} and logged as imported."
        )
    else:
        show_success_panel(f"Renamed {len(renames)} files in {path}.")


@app.command("detect-sd")
def detect_sd():
    volumes = list_all_volumes()
    from rich.table import Table

    table = Table(title="Detected Volumes")
    table.add_column("Volume", style="cyan")
    table.add_column("Has Camera Files", style="green")
    for path, has in volumes:
        table.add_row(path, "Yes ✨" if has else "No")
    console.print(table)


@app.command("gui")
def gui():
    import os

    os.execv(
        sys.executable,
        [
            sys.executable,
            "-c",
            "from snapimport.gui import start_gui; from nicegui import ui; ui.run(title='SnapImport', native=False, reload=False, window_size=(780, 580))",
        ],
    )


@app.command("setup")
def setup_cmd():
    run_wizard()
    cfg = load_config()
    if cfg:
        console.print(
            f"Config updated! Photos → {cfg.photos_dir}, Logs → {cfg.logs_dir}"
        )


@app.command("reset-demo")
def reset_demo_cmd(
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip confirmation prompt (for scripting).",
    ),
):
    """
    Developer tool — resets SnapImport to first-run state.

    Deletes config.toml, first-run marker, seen-files.txt, and import-errors.log.
    """
    config_path = get_config_path()
    config_dir = config_path.parent
    first_run_marker = config_dir / ".first_run_done"

    logs_dir = None
    if config_path.exists():
        cfg = load_config()
        if cfg:
            logs_dir = Path(cfg.logs_dir)

    files_to_delete = []
    items_to_show = []

    if config_path.exists():
        files_to_delete.append(config_path)
        items_to_show.append(f"config.toml")

    if first_run_marker.exists():
        files_to_delete.append(first_run_marker)
        items_to_show.append(".first_run_done")

    if logs_dir and logs_dir.exists():
        seen_files = logs_dir / "seen-files.txt"
        if seen_files.exists():
            files_to_delete.append(seen_files)
            items_to_show.append(str(seen_files))

        import_errors = logs_dir / "import-errors.log"
        if import_errors.exists():
            files_to_delete.append(import_errors)
            items_to_show.append(str(import_errors))

    if not files_to_delete:
        console.print("No state files found. Nothing to reset.")
        return

    panel_content = "Will delete:\n" + "\n".join(
        f"  • {item}" for item in items_to_show
    )
    console.print(Panel(panel_content, title="Reset SnapImport"))

    if not force:
        confirmed = Confirm.ask(
            "Reset SnapImport to first-run state?",
            default=False,
        )
        if not confirmed:
            console.print("Aborted.")
            return

    for f in files_to_delete:
        try:
            f.unlink()
        except Exception as e:
            console.print(f"Warning: Could not delete {f}: {e}")

    console.print("✓ Reset Complete — run `snapimport` to start fresh")


def run_wizard():
    show_welcome_panel()
    while True:
        photos_path = prompt_photos_dir()
        photos_path = Path(photos_path).expanduser()
        if not photos_path.exists():
            show_error_panel(
                "That folder doesn't exist, love. Drag a real one and try again."
            )
            continue
        break
    console.print(f"Photos locked to [bold green]{photos_path}[/bold green]")
    default_logs = str(Path.home() / "Pictures" / "SnapImport-Logs")
    logs_path = prompt_logs_dir(default_logs)
    logs_path = Path(logs_path).expanduser()
    if not logs_path.exists():
        console.print("Creating your log folder…")
        logs_path.mkdir(parents=True, exist_ok=True)
        console.print("✔")
    config = Config(photos_dir=str(photos_path), logs_dir=str(logs_path))
    save_config(config)
    # First-run confirmation panel (only once)
    marker = Path(get_config_path()).parent / ".first_run_done"
    if not marker.exists():
        panel_text = (
            f"SnapImport is Ready\nPhotos → {photos_path}\nLogs → {logs_path}\n"
            "Hint: Run `snapimport import --dry-run` to preview your first import."
        )
        show_success_panel(panel_text)
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("done")
        except Exception:
            pass


if __name__ == "__main__":
    app()
