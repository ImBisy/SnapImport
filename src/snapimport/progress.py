"""Progress display and user interface utilities for SnapImport.

Provides Rich-based UI components including progress bars, panels,
tables, and prompts for the import process.
"""

from pathlib import Path
from typing import List, Dict
from typing import List, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
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


def format_size(num_bytes: int) -> str:
    """Format bytes as human-readable size.
    
    Args:
        num_bytes: Number of bytes to format.
        
    Returns:
        Human-readable string (e.g., "1.23 GB" or "456.78 MB").
    """
    # Pretty print bytes as GB/MB with two decimals
    gb = num_bytes / (1024**3)
    if gb >= 1:
        return f"{gb:.2f} GB"
    mb = num_bytes / (1024**2)
    return f"{mb:.2f} MB"


def show_no_sd_card_panel():
    """Display panel when no SD card is detected."""
    body = (
        "Make sure your SD card is inserted and mounted, then try again.\n"
        "Run `snapimport detect-sd` to see all mounted volumes and their status."
    )
    panel = Panel(body, title="No SD Card Detected", border_style="red")
    console.print(panel)


def show_import_complete_panel(
    files_copied: int,
    total_size_bytes: int,
    files_skipped_seen: int,
    renamed_count: int,
    no_exif_count: int,
    destination: str,
    is_dry_run: bool = False,
    overwritten: int = 0,
    skipped_exists: int = 0,
):
    """Display import completion summary panel.
    
    Args:
        files_copied: Number of files successfully copied.
        total_size_bytes: Total size of all files in bytes.
        files_skipped_seen: Number of files skipped due to being seen before.
        renamed_count: Number of files that were renamed.
        no_exif_count: Number of files without EXIF data.
        destination: Destination directory path.
        is_dry_run: Whether this was a dry run.
        overwritten: Number of files that were overwritten.
        skipped_exists: Number of files skipped due to existing destination.
    """
    # Build a compact summary using a table inside a panel
    title = "[DRY RUN] Import Complete" if is_dry_run else "Import Complete"
    table = Table(title=None)
    table.add_column("Metric", style="white", no_wrap=True)
    table.add_column("Value", style="white")

    # Style rows by category
    copied_style = "green"
    skipped_style = "yellow"
    rename_style = "green"
    noexif_style = "yellow"

    size_str = format_size(total_size_bytes)
    table.add_row(
        "Files copied", f"{files_copied} files • {size_str}", style=copied_style
    )
    table.add_row(
        "Files skipped (seen-files)", str(files_skipped_seen), style=skipped_style
    )
    table.add_row("Renamed (date-based)", str(renamed_count), style=rename_style)
    table.add_row("No EXIF (fallback)", str(no_exif_count), style=noexif_style)
    table.add_row("Overwritten", str(overwritten), style=copied_style)
    table.add_row("Skipped (exists)", str(skipped_exists), style=skipped_style)
    table.add_row("Destination", destination)

    panel = Panel(table, title=title, border_style="green")
    console.print(panel)


def show_warnings_panel(failures: List[Dict[str, str]]):
    """Display panel with import warnings/failures.
    
    Args:
        failures: List of failure dictionaries with file, reason, suggestion.
    """
    if not failures:
        return
    table = Table(title="⚠ Warnings")
    table.add_column("File", style="cyan")
    table.add_column("Reason", style="yellow")
    table.add_column("Suggestion", style="white")
    for f in failures:
        table.add_row(
            str(f.get("file")), str(f.get("reason")), str(f.get("suggestion"))
        )
    panel = Panel(table, border_style="yellow")
    console.print(panel)


def write_import_errors(logs_dir: Path, failures: List[Dict[str, str]]):
    """Write import errors to log file.
    
    Args:
        logs_dir: Directory to write the log file in.
        failures: List of failure dictionaries.
        
    Note:
        Only writes log if there are failures.
        Format: filename | reason | suggestion
    """
    if not failures:
        return
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / "import-errors.log"
    with path.open("a", encoding="utf-8") as f:
        for item in failures:
            line = f"{item.get('file')} | {item.get('reason')} | {item.get('suggestion')}\n"
            f.write(line)


def show_overwrite_warning():
    """Display warning when overwrite mode is enabled."""
    panel = Panel(
        "⚠ Overwrite mode enabled — existing files will be replaced.",
        border_style="yellow",
    )
    console.print(panel)


def show_header():
    """Display application header."""
    text = Text("SnapImport", style="bold magenta")
    console.print(
        Panel(
            text,
            title="✨ SD card to dated perfection in one drag",
            border_style="blue",
        )
    )


def show_welcome_panel():
    """Display welcome panel for first-time users."""
    panel = Panel(
        "Welcome to SnapImport ✨ Let's get you set up in 20 seconds flat",
        border_style="green",
    )
    console.print(panel)


def prompt_photos_dir() -> str:
    """Prompt user for photos directory path.
    
    Returns:
        User-provided photos directory path.
    """
    return Prompt.ask(
        "Drag your main photos folder from Finder into this window or paste the full path (it should live inside ~/Pictures/):"
    ).strip("'\"\\")


def prompt_logs_dir(default: str = "~/Pictures/SnapImport-Logs") -> str:
    """Prompt user for logs directory path.
    
    Args:
        default: Default path to suggest.
        
    Returns:
        User-provided logs directory path.
    """
    return Prompt.ask(
        "Where should I keep the logs? (I'll create it for you)\n"
        "Suggested: ~/Pictures/SnapImport-Logs\n"
        "Drag folder or just hit Enter:",
        default=default,
    ).strip("'\"\\")


def show_error_panel(message: str):
    """Display error panel.
    
    Args:
        message: Error message to display.
    """
    panel = Panel(message, border_style="red")
    console.print(panel)


def show_success_panel(message: str):
    """Display success panel.
    
    Args:
        message: Success message to display.
    """
    panel = Panel(message, border_style="green")
    console.print(panel)


def create_progress() -> Progress:
    """Create a Rich progress bar with standard columns.
    
    Returns:
        Configured Progress instance.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    )


def show_dry_run_table(renames: List[Tuple[str, str]]):
    """Display table of planned renames for dry run.
    
    Args:
        renames: List of (old_path, new_path) tuples.
    """
    table = Table(title="Dry Run: Planned Renames")
    table.add_column("Original", style="cyan")
    table.add_column("New", style="green")
    for old, new in renames:
        table.add_row(old, new)
    console.print(table)


def confirm_import() -> bool:
    """Ask user to confirm before starting import.
    
    Returns:
        True if user confirms, False otherwise.
    """
    return Confirm.ask(
        "Ready to import? This will copy and rename files.", default=True
    )
