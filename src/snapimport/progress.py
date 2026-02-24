from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()

def show_header():
    text = Text("SnapImport", style="bold magenta")
    console.print(Panel(text, title="✨ SD card to dated perfection in one drag", border_style="blue"))

def show_welcome_panel():
    panel = Panel(
        "Welcome to SnapImport ✨ Let's get you set up in 20 seconds flat",
        border_style="green",
    )
    console.print(panel)

def prompt_photos_dir() -> str:
    return Prompt.ask(
        "Drag your main photos folder from Finder into this window or paste the full path (it should live inside ~/Pictures/):"
    ).strip("'\"\\")

def prompt_logs_dir(default: str) -> str:
    return Prompt.ask(
        "Where should I keep the logs? (I'll create it for you)\n"
        f"Suggested: {default}\n"
        "Drag folder or just hit Enter:",
        default=default,
    ).strip("'\"\\")

def show_error_panel(message: str):
    panel = Panel(message, border_style="red")
    console.print(panel)

def show_success_panel(message: str):
    panel = Panel(message, border_style="green")
    console.print(panel)

def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    )

def show_dry_run_table(renames: List[Tuple[str, str]]):
    table = Table(title="Dry Run: Planned Renames")
    table.add_column("Original", style="cyan")
    table.add_column("New", style="green")
    for old, new in renames:
        table.add_row(old, new)
    console.print(table)

def confirm_import() -> bool:
    return Confirm.ask("Ready to import? This will copy and rename files.", default=True)
