"""Command-line interface for SnapImport.

Provides Typer-based CLI commands for importing photos from SD cards,
detecting SD cards, and managing configuration.
"""

import sys
import os
import typer
from pathlib import Path
from typing import Optional

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
from .rename import (
    rename_files_in_folder,
    get_renames_for_folder,
    execute_renames,
    find_files,
    is_already_renamed,
)
from .sd import list_all_volumes

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Main entry point - shows help or runs wizard/import.
    
    Args:
        ctx: Typer context for command detection.
    """
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
    """Import photos from detected SD card.
    
    Args:
        dry_run: Show planned actions without executing.
        verbose: Print per-file progress.
        overwrite: Replace existing destination files.
        reconfigure: Re-run setup before importing.
    """
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
        None, help="Path to the folder containing photos to rename."
    ),
    log: bool = typer.Option(
        False,
        "--log",
        help="Log renamed files as imported (requires config).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Rename all files, even if already logged as imported.",
    ),
):
    """Rename files in a folder using EXIF data.
    
    Args:
        path: Folder path to rename files in (uses config.photos_dir if None).
        log: Log renamed files as imported in seen-files.txt.
        force: Rename files even if already marked as imported.
    """
    config = load_config()
    if path is None:
        if not config:
            show_error_panel(
                "No path provided and no config found. Run `snapimport wizard` first."
            )
            return
        folder = Path(config.photos_dir)
    else:
        folder = Path(path)

    if not folder.exists() or not folder.is_dir():
        show_error_panel("The provided path does not exist or is not a directory.")
        return

    seen_set: set[str] = set()
    should_log = log and config
    if not force and should_log:
        seen_file_path = Path(config.logs_dir) / "seen-files.txt"
        if seen_file_path.exists():
            try:
                with seen_file_path.open("r", encoding="utf-8") as sf:
                    seen_set = {ln.strip() for ln in sf if ln.strip()}
            except Exception:
                pass

    all_renames = get_renames_for_folder(folder)
    renames = []
    for old, new in all_renames:
        if force or not should_log or (new not in seen_set and old not in seen_set):
            renames.append((old, new))

    execute_renames(renames)

    if config and renames:
        from .core import log_seen_files

        logs_dir = Path(config.logs_dir)
        files_to_log = [Path(new) for old, new in renames]
        log_seen_files(logs_dir, files_to_log, base_folder=folder)
        show_success_panel(
            f"Renamed {len(renames)} files in {folder} and logged as imported."
        )
    elif renames:
        show_success_panel(f"Renamed {len(renames)} files in {folder}.")
    else:
        show_success_panel(f"No files to rename in {folder}.")


@app.command("redo-logs")
def redo_logs_cmd():
    """Re-scan photos folder and overwrite logs with all renamed files."""
    config = load_config()
    if not config:
        show_error_panel("No config found. Run `snapimport wizard` first.")
        return

    photos_path = Path(config.photos_dir)
    logs_dir = Path(config.logs_dir)

    files = find_files(photos_path)
    already_renamed = [f for f in files if is_already_renamed(f)]

    log_file = logs_dir / "seen-files.txt"
    logs_dir.mkdir(parents=True, exist_ok=True)

    with log_file.open("w") as f:
        for file in already_renamed:
            try:
                rel_path = file.relative_to(photos_path.parent)
                f.write(str(rel_path) + "\n")
            except ValueError:
                f.write(str(file) + "\n")

    show_success_panel(f"Logged {len(already_renamed)} files to {log_file}")


@app.command("wizard")
def wizard_cmd():
    """Run the setup wizard again."""
    run_wizard()
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
    """Launch the web-based GUI interface."""
    os.execv(  # pragma: no cover
        sys.executable,
        [
            sys.executable,
            "-c",
            "from snapimport.gui import start_gui; from nicegui import ui; ui.run(title='SnapImport', native=False, reload=False, window_size=(780, 580))",
        ],
    )


@app.command("setup")
def setup_cmd():
    """Run the setup wizard to configure SnapImport."""
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
    """Run the interactive setup wizard to configure SnapImport.
    
    Prompts user for photos and logs directories, saves config,
    and shows welcome panel.
    """
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

    files = find_files(photos_path)
    already_renamed = [f for f in files if is_already_renamed(f)]

    if already_renamed:
        console.print(
            f"\n[bold]Detected {len(already_renamed)} already-renamed images in your photos folder.[/bold]"
        )
        should_log = Confirm.ask(
            "Would you like me to log them as already imported?",
            default=True,
        )
        if should_log:
            from .core import log_seen_files

            log_seen_files(logs_path, already_renamed, base_folder=photos_path)
            console.print(f"✔ Logged {len(already_renamed)} files")

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


if __name__ == "__main__":  # pragma: no cover
    app()
