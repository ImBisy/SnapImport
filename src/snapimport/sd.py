"""SD card detection utilities for SnapImport.

Provides functions to detect mounted SD cards with camera files
and list all available volumes.
"""

EXTENSIONS = [
    '.ORF', '.JPG', '.CR2', '.CR3', '.NEF', '.NRW', '.ARW', '.SR2', '.SRF', '.RAF',
    '.RW2', '.PEF', '.PTX', '.DNG', '.RWL', '.3FR', '.IIQ', '.X3F', '.XMP'
]

SYSTEM_VOLUMES = ['Macintosh HD', 'Preboot', 'Recovery', 'VM', 'Update']

def has_camera_files(volume_path: str) -> bool:
    """Check if volume contains supported camera files.
    
    Args:
        volume_path: Path to mounted volume.
        
    Returns:
        True if volume contains any supported camera file types.
    """
    for ext in EXTENSIONS:
        pattern = os.path.join(volume_path, '**', f'*{ext}')
        if glob.glob(pattern, recursive=True):
            return True
    return False

def detect_sds() -> List[str]:
    """Detect mounted SD cards with camera files.
    
    Returns:
        List of paths to mounted volumes with camera files.
        
    Note:
        Excludes system volumes like Macintosh HD, Recovery, etc.
    """
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
    """List all mounted volumes with camera file status.
    
    Returns:
        List of (volume_path, has_camera_files) tuples.
        
    Note:
        Excludes system volumes.
    """
    volumes = []
    volumes_dir = '/Volumes'
    if not os.path.exists(volumes_dir):
        return volumes
    for item in os.listdir(volumes_dir):
        path = os.path.join(volumes_dir, item)
        if os.path.isdir(path) and item not in SYSTEM_VOLUMES: # pragma: no cover
            has_files = has_camera_files(path) # pragma: no cover
            volumes.append((path, has_files)) # pragma: no cover
    return volumes
