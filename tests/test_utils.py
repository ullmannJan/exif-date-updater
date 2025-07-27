"""Test utilities for creating test images and data."""

import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional
from PIL import Image
import piexif


def create_test_image(path: Path, add_exif: bool = False, exif_date: Optional[datetime] = None) -> None:
    """
    Create a simple test image, optionally with EXIF data.
    
    Args:
        path: Path where to save the image
        add_exif: Whether to add EXIF data
        exif_date: Date to add to EXIF (if add_exif is True)
    """
    # Create a simple red image
    img = Image.new('RGB', (100, 100), color='red')
    
    if add_exif and exif_date:
        # Create EXIF data with the specified date
        exif_date_str = exif_date.strftime('%Y:%m:%d %H:%M:%S')
        
        exif_dict = {
            "0th": {},
            "Exif": {
                piexif.ExifIFD.DateTimeOriginal: exif_date_str,
                piexif.ExifIFD.DateTimeDigitized: exif_date_str,
            },
            "GPS": {},
            "1st": {},
            "thumbnail": None
        }
        
        # Add DateTime to main IFD
        exif_dict["0th"][piexif.ImageIFD.DateTime] = exif_date_str
        
        exif_bytes = piexif.dump(exif_dict)
        img.save(path, format='JPEG', exif=exif_bytes)
    else:
        img.save(path, format='JPEG')


def create_test_directory() -> Path:
    """
    Create a temporary directory with various test files.
    
    Returns:
        Path to the temporary directory
    """
    temp_dir = Path(tempfile.mkdtemp())
    
    # Test files with different filename patterns
    test_files = [
        ("IMG_20231215_142030.jpg", False, None),  # Date in filename, no EXIF
        ("photo_without_date.jpg", False, None),   # No date pattern
        ("20231201_vacation.jpg", False, None),    # Different date pattern
        ("DSC_20240101_120000.jpg", True, datetime(2024, 1, 1, 12, 0, 0)),  # Has EXIF
        ("VID_20231120_153045.jpg", False, None),  # Video-style filename
        ("2023-12-25_christmas.jpg", False, None), # ISO date format
    ]
    
    for filename, has_exif, exif_date in test_files:
        create_test_image(temp_dir / filename, has_exif, exif_date)
    
    return temp_dir


class TestFileManager:
    """Context manager for handling test directories."""
    
    def __init__(self):
        self.temp_dir = None
    
    def __enter__(self):
        self.temp_dir = create_test_directory()
        return self.temp_dir
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)


def get_sample_files():
    """Get a list of sample filenames for testing date pattern recognition."""
    return [
        "IMG_20231215_142030.jpg",      # Should detect: 2023-12-15 14:20:30
        "photo_without_date.jpg",       # Should detect: None
        "20231201_vacation.jpg",        # Should detect: 2023-12-01 00:00:00
        "DSC_2024-01-01_12-30-45.jpg", # Should detect: 2024-01-01 12:30:45
        "VID_20240325_090000.mp4",     # Should detect: 2024-03-25 09:00:00
        "2023-12-25_christmas.jpg",     # Should detect: 2023-12-25 00:00:00
        "IMG20231130.jpg",              # Should detect: 2023-11-30 00:00:00
        "random_file.jpg",              # Should detect: None
        "31-12-2023_newyear.jpg",      # Should detect: 2023-12-31 00:00:00
        "holiday_25122023.jpg",         # Should detect: 2023-12-25 00:00:00
    ]
