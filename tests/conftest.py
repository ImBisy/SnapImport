import os
from pathlib import Path
from unittest.mock import patch

import pytest

from snapimport import config as config_module
from snapimport import sd as sd_module


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Creates a temp config dir in tmp_path, patches all config paths to use it."""
    config_dir = tmp_path / "snapimport"
    config_dir.mkdir(parents=True, exist_ok=True)

    photos_dir = tmp_path / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    def mock_get_config_path():
        return config_dir / "config.toml"

    def mock_user_config_dir(appname=None, roaming=False):
        return str(config_dir)

    monkeypatch.setattr(config_module, "get_config_path", mock_get_config_path)
    monkeypatch.setattr(config_module, "user_config_dir", mock_user_config_dir)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    yield config_dir


@pytest.fixture
def fresh_config(isolated_config):
    """Ensures no config.toml exists (true first-run state)."""
    config_path = isolated_config / "config.toml"
    if config_path.exists():
        config_path.unlink()
    marker = isolated_config / ".first_run_done"
    if marker.exists():
        marker.unlink()
    return isolated_config


@pytest.fixture
def configured_app(isolated_config):
    """Pre-writes a valid config.toml pointing to tmp_path subdirs."""
    photos_dir = isolated_config.parent / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    logs_dir = isolated_config.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    config_content = f"""# SnapImport Configuration
photos_dir = "{photos_dir}"
logs_dir = "{logs_dir}"
"""
    config_path = isolated_config / "config.toml"
    config_path.write_text(config_content)

    yield {
        "config_dir": isolated_config,
        "photos_dir": photos_dir,
        "logs_dir": logs_dir,
    }


@pytest.fixture
def fake_sd(tmp_path):
    """Creates a temp dir mimicking a real SD card with camera files."""
    sd = tmp_path / "fake_sd"
    dcim = sd / "DCIM" / "100OLYMP"
    dcim.mkdir(parents=True, exist_ok=True)

    (dcim / "IMG_001.ORF").write_bytes(b"ORF fake data")
    (dcim / "IMG_002.ORF").write_bytes(b"ORF fake data")
    (dcim / "IMG_003.JPG").write_bytes(b"JPG fake data")

    yield sd


@pytest.fixture
def fake_sd_with_exif(tmp_path):
    """Creates a temp dir with minimal EXIF-tagged JPEG files using piexif."""
    try:
        import piexif
    except ImportError:
        pytest.skip("piexif not installed")

    sd = tmp_path / "fake_sd_exif"
    dcim = sd / "DCIM" / "100OLYMP"
    dcim.mkdir(parents=True, exist_ok=True)

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"TestCamera",
            piexif.ImageIFD.Model: b"TestModel",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2023:12:25 10:30:00",
        },
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }

    for i in range(1, 4):
        img_path = dcim / f"IMG_00{i}.JPG"
        img_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb"
        img_data += b"\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f"
        img_data += b"\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0"
        img_data += b"\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01"
        img_data += b"\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01"
        img_data += b'\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142'
        img_data += b"\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92"
        img_data += b"\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2"
        img_data += b"\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8"
        img_data += b"\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd5\xff\xd9"

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(img_path))

    yield sd


@pytest.fixture
def fake_sd_empty(tmp_path):
    """SD detected but DCIM contains no supported files."""
    sd = tmp_path / "fake_sd_empty"
    dcim = sd / "DCIM" / "100OLYMP"
    dcim.mkdir(parents=True, exist_ok=True)

    (dcim / "README.txt").write_text("No camera files here")

    yield sd


@pytest.fixture
def fake_sd_all_seen(fake_sd, configured_app):
    """All files pre-written to seen-files.txt."""
    logs_dir = configured_app["logs_dir"]
    seen_file = logs_dir / "seen-files.txt"
    seen_file.parent.mkdir(parents=True, exist_ok=True)

    files = list((fake_sd / "DCIM" / "100OLYMP").glob("*"))
    seen_file.write_text("\n".join(str(f) for f in files))

    yield {
        "sd": fake_sd,
        "logs_dir": logs_dir,
    }


@pytest.fixture
def fake_sd_with_conflict(fake_sd, configured_app):
    """One file's destination already exists in photos_dir."""
    from snapimport.rename import get_exif_date

    photos_dir = configured_app["photos_dir"]
    sd_path = fake_sd / "DCIM" / "100OLYMP"
    files = list(sd_path.glob("*"))

    for f in files:
        date = get_exif_date(f) or "2023-12-25"
        dst = photos_dir / f"{date}-001.jpg"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"existing content")

    yield {
        "sd": fake_sd,
        "photos_dir": photos_dir,
        "logs_dir": configured_app["logs_dir"],
    }


@pytest.fixture
def wizard_inputs(monkeypatch):
    """Patches Prompt.ask to feed a list of answers in order."""
    answers = []

    def mock_ask(prompt, **kwargs):
        if answers:
            return answers.pop(0)
        return kwargs.get("default", "")

    monkeypatch.setattr("snapimport.progress.Prompt.ask", mock_ask)

    def set_answers(answer_list):
        answers.extend(answer_list)

    yield set_answers
