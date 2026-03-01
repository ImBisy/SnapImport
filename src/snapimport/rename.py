import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

from .sd import EXTENSIONS

DATE_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{3,}$")


def is_already_renamed(file: Path) -> bool:
    name_without_ext = file.stem
    return DATE_PATTERN.match(name_without_ext) is not None


def find_files(folder: Path) -> List[Path]:
    files = []
    for ext in EXTENSIONS:
        files.extend(folder.glob(f"*{ext}"))
        files.extend(folder.glob(f"*{ext.lower()}"))
    return sorted(set(files))


def get_exif_date(file: Path) -> str | None:
    try:
        result = subprocess.run(
            ["exiftool", "-DateTimeOriginal", "-d", "%y-%m-%d", str(file)],
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        # exiftool outputs like "Date/Time Original              : 24-02-24"
        if output and ":" in output:
            return output.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def get_renames(files: List[Path], target_folder: Path) -> List[Tuple[str, str]]:
    date_counts = defaultdict(int)
    renames = []

    for file in sorted(files):
        ext = file.suffix
        if ext.lower() == ".xmp":
            continue
        if not is_already_renamed(file):
            continue
        if ext == ext.upper():
            continue
        new_name = file.stem + file.suffix.upper()
        new_path = target_folder / new_name
        renames.append((str(file), str(new_path)))

    for file in sorted(files):
        if is_already_renamed(file):
            continue
        if file.suffix.lower() == ".xmp":
            continue
        date = get_exif_date(file)
        if not date:
            continue
        date_counts[date] += 1
        ext = file.suffix.upper()
        new_name = f"{date}-{date_counts[date]:03d}{ext}"
        new_path = target_folder / new_name
        renames.append((str(file), str(new_path)))

        xmp_path = file.with_suffix(".xmp")
        if xmp_path.exists():
            xmp_new_path = target_folder / (new_name.rsplit(".", 1)[0] + ".XMP")
            renames.append((str(xmp_path), str(xmp_new_path)))

    for file in sorted(files):
        if file.suffix.lower() != ".xmp":
            continue
        if is_already_renamed(file):
            continue
        date = get_exif_date(file)
        if not date:
            continue
        date_counts[date] += 1
        new_name = f"{date}-{date_counts[date]:03d}.XMP"
        new_path = target_folder / new_name
        renames.append((str(file), str(new_path)))

    return renames


def rename_files_in_folder(
    folder: Path, dry_run: bool = False
) -> List[Tuple[str, str]]:
    files = find_files(folder)
    renames = get_renames(files, folder)
    return execute_renames(renames, dry_run=dry_run)


def get_renames_for_folder(folder: Path) -> List[Tuple[str, str]]:
    files = find_files(folder)
    return get_renames(files, folder)


def execute_renames(
    renames: List[Tuple[str, str]], dry_run: bool = False
) -> List[Tuple[str, str]]:
    if not dry_run:
        for old, new in renames:
            Path(old).rename(Path(new))
    return renames
