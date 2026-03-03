# SnapImport

SD card to dated perfection in one drag. Prettier, friendlier, still macOS native.

> Full wizard setup, EXIF renaming, live progress, dry-run, verbose mode, conflict handling, and robust error reporting.

![Version](https://img.shields.io/badge/version-1.0.0-green?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-macOS-black?style=for-the-badge)
![Language](https://img.shields.io/badge/language-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

### Quick Start (20 seconds)

1. `snapimport` (first run → wizard)
2. `snapimport import --dry-run` (preview)
3. `snapimport import` (do it)

### Reconfigure Anytime

- `snapimport setup` - Re-run the wizard
- `snapimport reset-demo` - Developer reset to first-run state

## Features

- **Seamless Setup**: First-time wizard guides you through configuration in under 20 seconds.
- **Smart SD Detection**: Automatically detects macOS SD cards with camera files, skips system volumes.
- **Chunked Copy with Progress**: Fast, resumable file copying with a silky smooth Rich progress bar.
- **EXIF-Based Renaming**: Renames photos using `DateTimeOriginal` to YY-MM-DD-###.ext format, sequences restart per day.
- **Permission Handling**: Prompts for `sudo chown` if files are root-owned, just like the original.
- **Logging**: Tracks imported files in `seen-files.txt` for auditing.
- **Dry Run Mode**: Preview exact renames before committing.
- **Rich Terminal UI**: Eye candy everywhere – panels, tables, prompts, all dark/light theme friendly.

## Installation

### Recommended: uv

```bash
uv tool install snapimport
```

### Alternative: pipx

```bash
pipx install snapimport
```

### From Source

```bash
git clone https://github.com/ImBisy/SnapImport.git
cd snapimport
uv build
uv tool install --force .
```

## Usage

### First Time Setup

Run `snapimport` without arguments. The wizard will prompt for your photos and logs directories.

### Import Photos

```bash
snapimport import
```

Copies from detected SD card to your photos folder, renames, and logs.

### Dry Run

```bash
snapimport import --dry-run
```

Shows a table of all planned renames without touching files.

### Rename Existing Folder

```bash
snapimport rename /path/to/photos
```

Renames files in the given folder using the same logic.

### Detect SD Cards

```bash
snapimport detect-sd
```

Lists all /Volumes with camera file detection status.

## Configuration

Stored in `~/.config/snapimport/config.toml`:

```toml
# SnapImport Configuration
# Edit these paths anytime. Nothing else needed for v1.

photos_dir = "~/Pictures/Photos"
logs_dir = "~/Pictures/SnapImport-Logs"
```

## Supported Formats

All common RAW and JPG: ORF, JPG, CR2, CR3, NEF, NRW, ARW, SR2, SRF, RAF, RW2, PEF, PTX, DNG, RWL, 3FR, IIQ, X3F, XMP.

## Why SnapImport?

SnapImport is the spiritual successor to [Photo-Renamer](https://github.com/ImBisy/Photo-Renamer), rebuilt from the ground up in Python for modern macOS. It preserves the exact import + rename + log workflow but adds:

- Beautiful, wizard-driven setup
- Live progress bars during copy
- Dry-run previews
- Robust error handling
- Fully typed, tested code

No more shell script hassles – pure Python magic.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest -q --tb=short

# Run with coverage
uv run pytest --cov=snapimport --cov-report=term-missing
```

### Test Markers

- `unit`: Fast isolated tests for individual functions
- `integration`: Full journey tests using fixtures
- `cli`: Tests that exercise the Typer CLI via CliRunner

### Developer Commands

- `snapimport reset-demo` - Developer tool that resets SnapImport to first-run state. Deletes config.toml, first-run marker, seen-files.txt, and import-errors.log. Use `--force` to skip confirmation prompt (useful for scripting).

### Testing Fixtures

Tests use isolated fixtures in `tests/conftest.py`:

- `isolated_config` - Creates a temp config dir, patches all config paths
- `fresh_config` - Ensures no config exists (true first-run state)
- `configured_app` - Pre-writes a valid config.toml
- `fake_sd` - Creates a temp dir mimicking a real SD card
- `wizard_inputs` - Patches Prompt.ask to feed deterministic answers
