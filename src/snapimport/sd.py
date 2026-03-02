"""SD card detection utilities for SnapImport.

Provides functions to detect mounted SD cards with camera files
and list all available volumes.
"""

import glob
import os
from pathlib import Path
from typing import List, Tuple

EXTENSIONS = [
    ".ORF",
    ".JPG",
    ".CR2",
    ".CR3",
    ".NEF",
    ".NRW",
    ".ARW",
    ".SR2",
    ".SRF",
    ".RAF",
    ".RW2",
    ".PEF",
    ".PTX",
    ".DNG",
    ".RWL",
    ".3FR",
    ".IIQ",
    ".X3F",
    ".XMP",
]

SYSTEM_VOLUMES = {
    "Macintosh",
    "Macintosh HD",
    "Macintosh SSD",
    "APFS",
    "Recovery",
    "System",
}

FAKE_SD_PATH = Path.home() / "fake-sd"


def has_camera_files(volume_path: str) -> bool:
    """Check if volume contains supported camera files.

    Args:
        volume_path: Path to mounted volume.

    Returns:
        True if volume contains any supported camera file types.
    """
    for ext in EXTENSIONS:
        pattern = os.path.join(volume_path, "**", f"*{ext}")
        if glob.glob(pattern, recursive=True):
            return True
    return False


def detect_sds() -> List[str]:
    """Detect mounted SD cards with camera files.

    Returns:
        List of paths to mounted volumes with camera files.

    Note:
        Excludes system volumes like Macintosh HD, Recovery, etc.
        Includes ~/fake-sd if it exists and contains camera files.
    """
    volumes = []
    volumes_dir = "/Volumes"
    if os.path.exists(volumes_dir):
        for item in os.listdir(volumes_dir):
            path = os.path.join(volumes_dir, item)
            if (
                os.path.isdir(path)
                and item not in SYSTEM_VOLUMES
                and has_camera_files(path)
            ):
                volumes.append(path)

    if FAKE_SD_PATH.exists() and has_camera_files(str(FAKE_SD_PATH)):
        volumes.insert(0, str(FAKE_SD_PATH))

    return volumes


def list_all_volumes() -> List[Tuple[str, bool]]:
    """List all mounted volumes with camera file status.

    Returns:
        List of (volume_path, has_camera_files) tuples.

    Note:
        Excludes system volumes.
        Includes ~/fake-sd if it exists.
    """
    volumes = []
    volumes_dir = "/Volumes"
    if os.path.exists(volumes_dir):
        for item in os.listdir(volumes_dir):
            path = os.path.join(volumes_dir, item)
            if os.path.isdir(path) and item not in SYSTEM_VOLUMES:  # pragma: no cover
                has_files = has_camera_files(path)  # pragma: no cover
                volumes.append((path, has_files))  # pragma: no cover

    if FAKE_SD_PATH.exists():
        has_files = has_camera_files(str(FAKE_SD_PATH))
        volumes.insert(0, (str(FAKE_SD_PATH), has_files))

    return volumes
