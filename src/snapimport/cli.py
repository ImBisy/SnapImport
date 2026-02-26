import sys
import typer
from pathlib import Path
from typing import Optional

from nicegui import ui

from .config import Config, config_exists, load_config, save_config
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
def import_cmd(dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without doing it.")):
    config = load_config()
    if not config:
        show_error_panel("Config not found. Run `snapimport` without args to set up.")
        return
    import_photos(config, dry_run)

@app.command()
def rename(path: str = typer.Argument(..., help="Path to the folder containing photos to rename.")):
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        show_error_panel("The provided path does not exist or is not a directory.")
        return
    renames = rename_files_in_folder(folder)
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
    os.execv(sys.executable, [
        sys.executable, "-c",
        "from snapimport.gui import start_gui; from nicegui import ui; ui.run(title='SnapImport', native=False, reload=False, window_size=(780, 580))"
    ])

def run_wizard():
    show_welcome_panel()
    while True:
        photos_path = prompt_photos_dir()
        photos_path = Path(photos_path).expanduser()
        if not photos_path.exists():
            show_error_panel("That folder doesn't exist, love. Drag a real one and try again.")
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
    show_success_panel("You're golden, Boss. Run `snapimport import` whenever you plug in an SD card.")

if __name__ == "__main__":
    app()
