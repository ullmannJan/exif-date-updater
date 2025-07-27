# EXIF Date Updater

A Python tool to analyze and update missing EXIF date information in image and video files.

<img width="1804" height="1247" alt="image" src="https://github.com/user-attachments/assets/cadd5c35-a5b2-47fe-98d7-b749c6eb5dd2" />

## Features

- **Comprehensive Analysis**: Scans folders for image and video files with missing EXIF date information
- **Smart Date Detection**: Extracts dates from multiple sources:
  - Existing EXIF data (DateTimeOriginal, DateTime, DateTimeDigitized)
  - Video metadata (creation_time, encoded_date)
  - Filename patterns (various date formats)
  - File creation/modification dates
- **Intelligent Suggestions**: Prioritizes date sources by reliability and confidence
- **Safe Updates**: Creates backup files before making changes
- **Multiple Interfaces**: Both command-line and GUI interfaces available
- **Dry Run Mode**: Preview changes before applying them
- **Extensive File Support**: 
  - Images: JPG, JPEG, TIFF, TIF, PNG, BMP, GIF, WebP, HEIC, HEIF
  - Videos: MP4, MOV, AVI, MKV, WMV, FLV, WebM, M4V, 3GP, MTS, M2TS

## Installation

### Using uv (recommended)

```bash
cd exif_date_updater
uv sync
```

### Using pip

```bash
pip install -e .
```

## Usage

### Command Line Interface

#### Basic Analysis
```bash
# Analyze files in a folder
exif-date-updater /path/to/photos

# Show detailed analysis
exif-date-updater /path/to/photos --detailed
```

#### Updating Files
```bash
# Dry run (preview changes)
exif-date-updater /path/to/photos --dry-run

# Update files
exif-date-updater /path/to/photos --update

# Update without creating backups
exif-date-updater /path/to/photos --update --no-backup

# Update only DateTimeOriginal field
exif-date-updater /path/to/photos --update --no-date-created
```

#### Full Command Reference
```bash
exif-date-updater [-h] [--update] [--dry-run] [--no-backup] 
                  [--datetime-original] [--no-datetime-original]
                  [--date-created] [--no-date-created] [--detailed]
                  folder

positional arguments:
  folder                Path to the folder containing media files

optional arguments:
  -h, --help           show this help message and exit
  --update             Update EXIF dates (default: analyze only)
  --dry-run            Show what would be updated without making changes
  --no-backup          Don't create backup files when updating
  --datetime-original  Update DateTimeOriginal field (default: enabled)
  --no-datetime-original  Don't update DateTimeOriginal field
  --date-created       Update DateTime/DateCreated field (default: enabled)
  --no-date-created    Don't update DateTime/DateCreated field
  --detailed           Show detailed file analysis
```

### GUI Interface

Launch the graphical interface:
```bash
exif-date-updater-gui
```

The GUI provides:
- Folder selection and analysis
- Interactive file table showing missing dates and suggestions
- Update options configuration
- Progress tracking
- Activity log
- Dry run capability

### Python API

```python
from pathlib import Path
from exif_date_updater import ExifAnalyzer, ExifUpdater

# Initialize analyzer
analyzer = ExifAnalyzer()

# Analyze folder
folder_path = Path("/path/to/photos")
media_files = analyzer.analyze_folder(folder_path)

# Print summary
analyzer.print_summary()

# Get files with missing dates
missing_files = analyzer.get_files_with_missing_dates()

# Get files with date suggestions
suggested_files = analyzer.get_files_with_suggestions()

# Update files
updater = ExifUpdater(create_backup=True)
successful, failed = updater.update_multiple_files(
    suggested_files,
    update_datetime_original=True,
    update_date_created=True,
    dry_run=False
)

print(f"Updated {successful} files, {failed} failed")
```

## How It Works

### Date Source Priority

The tool prioritizes date sources in the following order:

1. **EXIF DateTimeOriginal** (confidence: 100%) - Most reliable
2. **EXIF DateTimeDigitized** (confidence: 90%) - Very reliable
3. **Video Creation Date** (confidence: 80%) - Reliable for videos
4. **Filename Date** (confidence: 70%) - Good if filename contains date
5. **File Creation Date** (confidence: 50%) - May not be original
6. **File Modification Date** (confidence: 30%) - Least reliable

### Filename Date Patterns

The tool recognizes various date patterns in filenames:
- `YYYY-MM-DD` or `YYYY_MM_DD`
- `YYYYMMDD`
- `DD-MM-YYYY` or `DD_MM_YYYY`
- `IMG_YYYYMMDD` or `VID_YYYYMMDD`
- `YYYY-MM-DD_HH-MM-SS`

### EXIF Fields Updated

- **DateTimeOriginal**: The date and time when the image was captured
- **DateTime**: The date and time when the image was last modified
- **DateTimeDigitized**: The date and time when the image was digitized

## Examples

### Example Output

```
==============================================================
EXIF DATE ANALYSIS SUMMARY
==============================================================
Total files analyzed: 150
Image files: 120
Video files: 30
Files missing DateTimeOriginal: 25
Files missing DateCreated: 15
Files with date suggestions: 30
==============================================================

FILES WITH MISSING EXIF DATES
==============================================================

File: IMG_20231215_142030.jpg
Path: /photos/IMG_20231215_142030.jpg
Size: 2,456,789 bytes
Missing dates: DateTimeOriginal
Available dates:
  - Filename Date: 2023-12-15 14:20:30
  - File Creation Date: 2023-12-20 10:15:22
  - File Modification Date: 2023-12-20 10:15:22
Suggested date: 2023-12-15 14:20:30 (confidence: 70.0%, source: Filename Date)
```

### Backup and Recovery

When updating files, the tool creates backup copies:
```python
# Restore a single file from backup
updater.restore_backup(Path("/path/to/photo.jpg"))

# Restore all backups in a folder
restored_count = updater.restore_all_backups(Path("/path/to/photos"))

# Clean up backup files
removed_count = updater.cleanup_backups(Path("/path/to/photos"))
```

## Requirements

- Python 3.11+
- Required packages (automatically installed):
  - exifread - Reading EXIF data
  - Pillow - Image processing
  - python-dateutil - Date parsing
  - ffmpeg-python - Video metadata extraction
  - piexif - Writing EXIF data
  - PySide6 - GUI interface

## Platform Support

- Windows ✅
- macOS ✅
- Linux ✅

## Limitations

- EXIF writing currently only supports JPEG and TIFF images
- Video file EXIF updating is not yet supported (analysis only)
- Some proprietary RAW formats may not be fully supported

## Safety Features

- **Backup Creation**: Original files are backed up before modification
- **Dry Run Mode**: Preview changes without making modifications
- **Confidence Scoring**: Understand the reliability of date suggestions
- **Error Handling**: Graceful handling of corrupt or unsupported files
- **Validation**: Ensures date values are reasonable before writing

## Contributing

This tool is designed to be easily extensible. You can add support for:
- Additional date patterns in filenames
- New metadata sources
- Additional file formats
- Custom confidence scoring algorithms

## License

This project is licensed under the MIT License.
