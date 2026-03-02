"""Generate demo files for fake SD card testing.

Creates 10 minimal valid JPEG files with .ORF extension, each containing
a DateTimeOriginal EXIF tag with distinct dates spanning 2022-2024.
Also creates empty XMP sidecar files.
"""

import io
import piexif
from pathlib import Path


def create_minimal_jpeg_with_exif(output_path: Path, date_original: str):
    """Create a minimal valid JPEG with EXIF DateTimeOriginal tag.

    Args:
        output_path: Path to write the file.
        date_original: DateTimeOriginal value in format "YYYY:MM:DD HH:MM:SS".
    """
    img = io.BytesIO()
    from PIL import Image

    img_obj = Image.new("RGB", (8, 8), color="white")
    img_obj.save(img, "JPEG")
    img_data = img.getvalue()

    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"OLYMPUS",
            piexif.ImageIFD.Model: b"E-M5",
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: date_original.encode("utf-8"),
            piexif.ExifIFD.DateTimeDigitized: date_original.encode("utf-8"),
        },
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, img_data, str(output_path))


def create_empty_xmp(output_path: Path):
    """Create a minimal valid XMP envelope.

    Args:
        output_path: Path to write the XMP file.
    """
    xmp_content = """<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
</x:xmpmeta>
<?xpacket end="w"?>
"""
    output_path.write_text(xmp_content)


def main():
    """Generate all demo files."""
    demo_dir = Path(__file__).parent

    dates = [
        "2022:03:14 09:00:00",
        "2022:08:22 14:30:00",
        "2023:01:05 11:15:00",
        "2023:06:18 16:45:00",
        "2023:09:30 08:20:00",
        "2023:12:25 12:00:00",
        "2024:02:14 19:30:00",
        "2024:05:10 10:00:00",
        "2024:08:05 15:45:00",
        "2024:11:28 17:30:00",
    ]

    for i, date in enumerate(dates, start=1):
        orf_path = demo_dir / f"IMG_{i:04d}.ORF"
        xmp_path = demo_dir / f"IMG_{i:04d}.XMP"

        create_minimal_jpeg_with_exif(orf_path, date)
        create_empty_xmp(xmp_path)

        print(f"Created {orf_path.name} with date {date}")
        print(f"Created {xmp_path.name}")

    print(f"\nGenerated {len(dates)} demo files in {demo_dir}")


if __name__ == "__main__":
    main()
