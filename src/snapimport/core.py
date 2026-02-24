import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import psutil
from rich.prompt import Confirm, Prompt

from .config import Config
from .progress import confirm_import, create_progress, show_error_panel, show_success_panel
from .rename import find_files, get_renames
from .sd import detect_sds

def copy_file_with_progress(src: Path, dst: Path, progress, task_id):
    with src.open('rb') as fsrc, dst.open('wb') as fdst:
        while True:
            chunk = fsrc.read(8192)
            if not chunk:
                break
            fdst.write(chunk)
            progress.advance(task_id, len(chunk))

def copy_files_with_progress(files: List[Path], dst_dir: Path, progress):
    dst_dir.mkdir(parents=True, exist_ok=True)
    total_size = sum(f.stat().st_size for f in files)
    task_id = progress.add_task("Importing photos", total=total_size)
    for file in files:
        rel_path = file.relative_to(file.parents[-2])  # Assuming SD is /Volumes/SD/DCIM/ etc.
        dst_path = dst_dir / rel_path
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        copy_file_with_progress(file, dst_path, progress, task_id)
    progress.remove_task(task_id)

def check_permissions(photos_dir: Path):
    for file in photos_dir.rglob('*'):
        if file.is_file():
            stat = file.stat()
            if stat.st_uid == 0:  # root
                if Confirm.ask(f"Some files are owned by root. Run sudo chown to fix permissions?", default=True):
                    subprocess.run(['sudo', 'chown', '-R', os.getlogin(), str(photos_dir)])
                break

def log_seen_files(logs_dir: Path, files: List[Path]):
    log_file = logs_dir / "seen-files.txt"
    logs_dir.mkdir(parents=True, exist_ok=True)
    with log_file.open('a') as f:
        for file in files:
            f.write(str(file) + '\n')

def import_photos(config: Config, dry_run: bool = False):
    sds = detect_sds()
    if not sds:
        show_error_panel("No SD cards with camera files detected. Plug in an SD card and try again.")
        return

    if len(sds) > 1:
        console.print("Multiple SDs detected:")
        for i, sd in enumerate(sds):
            console.print(f"{i+1}. {sd}")
        choice = Prompt.ask("Choose one", choices=[str(i+1) for i in range(len(sds))])
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
        from .progress import show_dry_run_table
        show_dry_run_table(renames)
        return

    # Confirm before starting
    if not confirm_import():
        return

    # Copy
    progress = create_progress()
    with progress:
        copy_files_with_progress(files, photos_dir, progress)

    # Check permissions
    check_permissions(photos_dir)

    # Rename
    renames = get_renames(find_files(photos_dir), photos_dir)
    for old, new in renames:
        Path(old).rename(Path(new))

    # Log
    log_seen_files(Path(config.logs_dir), files)

    # Success
    total_size = sum(f.stat().st_size for f in photos_dir.rglob('*') if f.is_file())
    show_success_panel(f"Imported {len(files)} photos like a fucking pro • {total_size / (1024**3):.2f} GB • Done!")
