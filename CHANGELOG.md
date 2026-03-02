# Changelog

## [1.0.0] - 2026-03-02

### Added
- First-time setup wizard with guided path configuration
- Smart SD card detection (macOS /Volumes, skips system volumes)
- EXIF-based photo renaming to YY-MM-DD-###.ext format
- Fallback to mtime when no EXIF date is present
- Chunked file copy with live Rich progress bar
- seen-files.txt tracking to skip already-imported photos
- Dry-run mode: preview all renames without touching files
- Verbose mode: per-file log lines during import
- Overwrite mode: replace existing destination files when needed
- Post-import summary panel with full stats
- Graceful error reporting with import-errors.log
- Helpful "No SD Card Detected" panel with guidance
- `snapimport setup` command to reconfigure paths anytime
- `snapimport detect-sd` command to list and diagnose volumes
- `snapimport rename` command to rename an existing folder
- `snapimport reset-demo` developer command to reset to first-run state
- 30+ tests covering unit, CLI, and integration paths
- 80%+ test coverage
- Google-style docstrings throughout the codebase

### Supported Formats
ORF, JPG, CR2, CR3, NEF, NRW, ARW, SR2, SRF, RAF, RW2, PEF, PTX, 
DNG, RWL, 3FR, IIQ, X3F, XMP
