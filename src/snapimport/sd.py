import glob
import os
from pathlib import Path
from typing import List

EXTENSIONS = [
    '.ORF', '.JPG', '.CR2', '.CR3', '.NEF', '.NRW', '.ARW', '.SR2', '.SRF', '.RAF',
    '.RW2', '.PEF', '.PTX', '.DNG', '.RWL', '.3FR', '.IIQ', '.X3F', '.XMP'
]

SYSTEM_VOLUMES = ['Macintosh HD', 'Preboot', 'Recovery', 'VM', 'Update']

def has_camera_files(volume_path: str) -> bool:
    for ext in EXTENSIONS:
        pattern = os.path.join(volume_path, '**', f'*{ext}')
        if glob.glob(pattern, recursive=True):
            return True
    return False

def detect_sds() -> List[str]:
    volumes = []
    volumes_dir = '/Volumes'
    if not os.path.exists(volumes_dir):
        return volumes
    for item in os.listdir(volumes_dir):
        path = os.path.join(volumes_dir, item)
        if os.path.isdir(path) and item not in SYSTEM_VOLUMES and has_camera_files(path):
            volumes.append(path)
    return volumes

def list_all_volumes() -> List[Tuple[str, bool]]:
    volumes = []
    volumes_dir = '/Volumes'
    if not os.path.exists(volumes_dir):
        return volumes
    for item in os.listdir(volumes_dir):
        path = os.path.join(volumes_dir, item)
        if os.path.isdir(path) and item not in SYSTEM_VOLUMES:
            has_files = has_camera_files(path)
            volumes.append((path, has_files))
    return volumes
