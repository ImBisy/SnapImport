import subprocess
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

from .sd import EXTENSIONS

def find_files(folder: Path) -> List[Path]:
    files = []
    for ext in EXTENSIONS:
        files.extend(folder.rglob(f'*{ext}'))
    return sorted(files)

def get_exif_date(file: Path) -> str | None:
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-d', '%y-%m-%d', str(file)],
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if output:
            # exiftool outputs like "Date/Time Original              : 24-02-24"
            # So, extract the date part
            parts = output.split(':')
            if len(parts) > 1:
                return parts[1].strip()
    except Exception:
        pass
    return None

def get_renames(files: List[Path], target_folder: Path) -> List[Tuple[str, str]]:
    date_counts = defaultdict(int)
    renames = []
    for file in sorted(files):
        date = get_exif_date(file)
        if not date:
            continue
        date_counts[date] += 1
        new_name = f"{date}-{date_counts[date]:03d}{file.suffix.lower()}"
        new_path = target_folder / new_name
        renames.append((str(file), str(new_path)))
    return renames

def rename_files_in_folder(folder: Path, dry_run: bool = False) -> List[Tuple[str, str]]:
    files = find_files(folder)
    renames = get_renames(files, folder)
    if not dry_run:
        for old, new in renames:
            Path(old).rename(Path(new))
    return renames
