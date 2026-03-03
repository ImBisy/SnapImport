"""Core import functionality for SnapImport.

Contains the main import_photos function and supporting utilities for
copying files, handling permissions, and managing the import process.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import psutil
import sys
from rich.prompt import Confirm, Prompt

from .config import Config
from .progress import (
    confirm_import,
    create_progress,
    show_error_panel,
    show_success_panel,
    show_no_sd_card_panel,
    show_import_complete_panel,
    write_import_errors,
)
import snapimport.progress as progress_mod
from .progress import console
from typing import Set
from pathlib import Path as _Path
from .rename import get_exif_date
from .rename import find_files, get_renames, get_exif_date
from .sd import detect_sds


def copy_file_with_progress(src: Path, dst: Path, progress, task_id) -> bool:
    """Copy a single file with progress tracking.

    Args:
        src: Source file path.
        dst: Destination file path.
        progress: Rich progress instance.
        task_id: Progress task ID to update.

    Returns:
        True if copy succeeded, False if it failed.
    """
    try:
        with src.open("rb") as fsrc, dst.open("wb") as fdst:
            while True:
                chunk = fsrc.read(8192)
                if not chunk:
                    break
                fdst.write(chunk)
                progress.advance(task_id, len(chunk))
        return True
    except Exception:
        return False


def copy_files_with_progress(
    files: List[Path],
    dst_dir: Path,
    progress,
    rename_map: dict | None = None,
    verbose: bool = False,
    overwrite: bool = False,
    seen_set: Set[str] | None = None,
):
    """Copy multiple files with progress tracking and conflict handling.

    Args:
        files: List of source files to copy.
        dst_dir: Destination directory.
        progress: Rich progress instance.
        rename_map: Optional mapping of source to destination paths.
        verbose: Whether to print per-file progress.
        overwrite: Whether to overwrite existing files.
        seen_set: Set of previously seen file paths to skip.

    Returns:
        Dictionary with copy statistics (copied, failed, skipped_seen,
        skipped_exists, overwritten, task_id).
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    total_size = sum(f.stat().st_size for f in files)
    task_id = progress.add_task("Importing photos", total=total_size)
    copied: List[str] = []
    failed: List[dict] = []
    skipped_seen = 0
    skipped_exists = 0
    overwritten = 0
    for file in files:
        # If a per-file rename is provided, honor it
        if rename_map and str(file) in rename_map:
            dst_path = Path(rename_map[str(file)])
        else:
            rel_path = file.relative_to(
                file.parents[-2]
            )  # Assuming SD is /Volumes/SD/DCIM/ etc.
            dst_path = dst_dir / rel_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        # Seen-files skip handling
        if seen_set is not None and str(file) in seen_set:
            status = "skipped_seen"
            skipped_seen += 1
            if verbose:
                date = get_exif_date(file) or "no EXIF - using mtime"
                new_name = dst_path.name
                console.log(f"[{file.name}] → [{new_name}] | EXIF: {date} | {status}")
            continue
        # Overwrite handling
        if dst_path.exists() and not overwrite:
            status = "skipped_exists"
            skipped_exists += 1
            if verbose:
                date = get_exif_date(file) or "no EXIF - using mtime"
                console.log(
                    f"[{file.name}] → [{dst_path.name}] | EXIF: {date} | {status}"
                )
            continue
        if dst_path.exists() and overwrite:
            overwritten += 1
        # Copy
        ok = copy_file_with_progress(file, dst_path, progress, task_id)
        if ok:
            copied.append(str(file))
            status = "copied"
        else:
            failed.append(
                {
                    "file": str(file),
                    "reason": "Copy failed",
                    "suggestion": "Check permissions",
                }
            )
            status = "failed"
        if verbose:
            date = get_exif_date(file) or "no EXIF - using mtime"
            new_name = dst_path.name
            console.log(f"[{file.name}] → [{new_name}] | EXIF: {date} | {status}")
    progress.remove_task(task_id)
    return {
        "copied": copied,
        "failed": failed,
        "skipped_seen": skipped_seen,
        "skipped_exists": skipped_exists,
        "overwritten": overwritten,
        "task_id": task_id,
    }


def check_permissions(photos_dir: Path):
    """Check for root-owned files and offer to fix permissions.

    Args:
        photos_dir: Directory to check for permission issues.

    Note:
        If root-owned files are found, prompts user to run sudo chown.
    """
    for file in photos_dir.rglob("*"):
        if file.is_file():
            stat = file.stat()
            if stat.st_uid == 0:  # root
                if Confirm.ask(
                    f"Some files are owned by root. Run sudo chown to fix permissions?",
                    default=True,
                ):
                    subprocess.run(
                        ["sudo", "chown", "-R", os.getlogin(), str(photos_dir)]
                    )
                break


def log_seen_files(logs_dir: Path, files: List[Path], base_folder: Path | None = None):
    """Log imported files to seen-files.txt for future duplicate detection.

    Args:
        logs_dir: Directory containing seen-files.txt.
        files: List of file paths that were successfully imported.
        base_folder: Optional base folder for relative path calculation.

    Note:
        Creates logs_dir if it doesn't exist.
        Appends to existing seen-files.txt without creating duplicates.
    """
    log_file = logs_dir / "seen-files.txt"
    logs_dir.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as f:
        for file in files:
            if base_folder:
                try:
                    rel_path = file.relative_to(base_folder.parent)
                    f.write(str(rel_path) + "\n")
                except ValueError:
                    f.write(str(file) + "\n")
            else:
                f.write(str(file) + "\n")


def import_photos(
    config: Config,
    dry_run: bool = False,
    verbose: bool = False,
    overwrite: bool = False,
):
    """Import photos from SD card to local directory with renaming.

    Args:
        config: Configuration containing photos_dir and logs_dir.
        dry_run: If True, show what would be done without copying files.
        verbose: If True, print per-file progress information.
        overwrite: If True, overwrite existing destination files.

    Returns:
        Dictionary with import statistics or None if no files found.

    Raises:
        SystemExit: If no SD card is detected (exit code 1).

    Note:
        - Detects SD cards automatically
        - Loads seen-files.txt to skip previously imported files
        - Copies files with progress tracking
        - Renames files using EXIF data (YY-MM-DD-###.ext format)
        - Logs failures to import-errors.log
        - Shows completion panel with statistics
    """
    sds = detect_sds()
    if not sds:
        # No SD detected – graceful fallback
        show_no_sd_card_panel()
        sys.exit(1)

    # Load seen-files.txt to skip files seen in prior imports
    logs_dir_for_seen = Path(config.logs_dir)
    seen_file_path = logs_dir_for_seen / "seen-files.txt"
    seen_set: Set[str] | None = None
    if seen_file_path.exists():
        try:
            with seen_file_path.open("r", encoding="utf-8") as sf:
                seen_set = {ln.strip() for ln in sf if ln.strip()}
        except Exception:
            seen_set = None

    if len(sds) > 1:
        console.print("Multiple SDs detected:")
        for i, sd in enumerate(sds):
            console.print(f"{i + 1}. {sd}")
        choice = Prompt.ask("Choose one", choices=[str(i + 1) for i in range(len(sds))])
        sd_path = sds[int(choice) - 1]
    else:
        sd_path = sds[0]

    photos_dir = Path(config.photos_dir)
    files = find_files(Path(sd_path))
    if not files:
        show_error_panel("No supported files found on SD.")
        return

    if dry_run:
        renames = get_renames(files, photos_dir)

        # Dry-run: do not copy, but show planned renames
        progress_mod.show_dry_run_table(renames)
        total_size = sum(f.stat().st_size for f in files)
        progress_mod.show_import_complete_panel(
            files_copied=0,
            total_size_bytes=total_size,
            files_skipped_seen=0,
            renamed_count=len(renames),
            no_exif_count=len(files) - len(renames),
            destination=str(photos_dir),
            is_dry_run=True,
            overwritten=0,
            skipped_exists=0,
        )
        return

    # Overwrite warning if enabled
    if overwrite:
        try:
            from .progress import show_overwrite_warning

            show_overwrite_warning()
        except Exception:
            pass
    # Confirm before starting
    if not confirm_import():
        return

    # Copy
    # Build a rename map for potential per-file hints (log/verbose).
    renames = get_renames(files, photos_dir)
    rename_map = {str(old): str(new) for old, new in renames}
    progress = create_progress()
    with progress:
        result = copy_files_with_progress(
            files,
            photos_dir,
            progress,
            rename_map=rename_map,
            verbose=verbose,
            overwrite=overwrite,
            seen_set=seen_set,
        )

    # Check permissions
    check_permissions(photos_dir)

    # Rename
    renames = get_renames(find_files(photos_dir), photos_dir)
    for old, new in renames:
        Path(old).rename(Path(new))

    # Log seen-files for future runs
    if isinstance(locals().get("result"), dict):
        # Append newly seen copied files to seen-files.txt
        copied_list = result.get("copied", [])
        log_seen_files(Path(config.logs_dir), [Path(p) for p in copied_list])

        # Write import errors if any
        failures = result.get("failed", [])
        if failures:
            progress_mod.write_import_errors(Path(config.logs_dir), failures)
            progress_mod.show_warnings_panel(failures)
    else:
        log_seen_files(Path(config.logs_dir), files)

    # Success
    total_size = sum(f.stat().st_size for f in photos_dir.rglob("*") if f.is_file())
    # Basic post-import stats (use actual counters from copy step)
    overwritten = (
        result.get("overwritten", 0) if isinstance(locals().get("result"), dict) else 0
    )
    skipped_exists = (
        result.get("skipped_exists", 0)
        if isinstance(locals().get("result"), dict)
        else 0
    )
    renames_post = get_renames(find_files(photos_dir), photos_dir)

    copied_files = (
        result.get("copied", []) if isinstance(locals().get("result"), dict) else []
    )
    file_names = [Path(f).name for f in copied_files]

    progress_mod.show_import_complete_panel(
        files_copied=len(files)
        if not isinstance(locals().get("result"), dict)
        else len(result.get("copied", [])),
        total_size_bytes=total_size,
        files_skipped_seen=result.get("skipped_seen", 0)
        if isinstance(locals().get("result"), dict)
        else 0,
        renamed_count=len(renames_post),
        no_exif_count=len(files) - len(renames_post),
        destination=str(photos_dir),
        overwritten=overwritten,
        skipped_exists=skipped_exists,
        is_dry_run=False,
        file_list=file_names if file_names else None,
    )
    show_success_panel(
        f"Imported {len(files)} photos like a fucking pro • {total_size / (1024**3):.2f} GB • Done!"
    )

    # Return stats for tests
    stats = {
        "copied": len(result.get("copied", []))
        if isinstance(locals().get("result"), dict)
        else len(files),
        "skipped_seen": result.get("skipped_seen", 0)
        if isinstance(locals().get("result"), dict)
        else 0,
        "failed": len(result.get("failed", []))
        if isinstance(locals().get("result"), dict)
        else 0,
        "overwritten": result.get("overwritten", 0)
        if isinstance(locals().get("result"), dict)
        else 0,
        "skipped_exists": result.get("skipped_exists", 0)
        if isinstance(locals().get("result"), dict)
        else 0,
        "renamed": len(renames_post),
        "total_size": total_size,
        "source_volume": Path(sd_path),
    }
    return stats
