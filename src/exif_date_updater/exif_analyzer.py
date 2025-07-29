"""
EXIF Date Analyzer - Core module for analyzing and extracting date information from media files.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

import exifread
from PIL import Image
from PIL.ExifTags import TAGS


class MediaFile:
    """Represents a media file with its metadata and date information."""
    
    def __init__(self, file_path: Path):
        self.path = file_path
        self.name = file_path.name
        self.extension = file_path.suffix.lower()
        self.size = file_path.stat().st_size if file_path.exists() else 0
        self.modification_date = datetime.fromtimestamp(file_path.stat().st_mtime) if file_path.exists() else None
        self.creation_date = datetime.fromtimestamp(file_path.stat().st_ctime) if file_path.exists() else None
        
        # EXIF date fields
        self.datetime_original: Optional[datetime] = None
        self.date_created: Optional[datetime] = None
        self.datetime_digitized: Optional[datetime] = None
        
        # Other extracted dates
        self.filename_date: Optional[datetime] = None
        
        # Analysis results
        self.missing_dates: List[str] = []
        self.suggested_date: Optional[datetime] = None
        self.source: Optional[str] = None
        self.available_sources: List[tuple] = []  # List of (date, source_name) tuples


class ExifAnalyzer:
    """Main class for analyzing EXIF data and extracting date information."""
    
    # Supported file extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.tiff', '.tif', '.png', '.bmp', '.gif', '.webp', '.heic', '.heif'}
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mts', '.m2ts'}
    
    # Date patterns commonly found in filenames
    DATE_PATTERNS = [
        # Date and time patterns
        r'(\d{4})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})',  # YYYY-MM-DD-HH-MM-SS or YYYY_MM_DD_HH_MM_SS
        r'(\d{4})(\d{2})(\d{2})[-_](\d{2})(\d{2})(\d{2})',                  # YYYYMMDD-HHMMSS or YYYYMMDD_HHMMSS
        r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})',                      # YYYYMMDDHHMMSS
        r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})',                 # YYYY-MM-DD_HH-MM-SS
        r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})',                 # YYYY-MM-DDTHH:MM:SS (ISO-like)
        r'IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',                 # IMG_YYYYMMDD_HHMMSS
        r'VID_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',                 # VID_YYYYMMDD_HHMMSS
        r'(\d{4})[-_](\d{2})[-_](\d{2})[-_](\d{2})\.(\d{2})\.(\d{2})',      # YYYY-MM-DD-HH.MM.SS
        r'(\d{4})(\d{2})(\d{2})[-_](\d{2})\.(\d{2})\.(\d{2})',              # YYYYMMDD-HH.MM.SS
        
        # Date-only patterns (fallback)
        r'(\d{4})[-_](\d{2})[-_](\d{2})',                                    # YYYY-MM-DD or YYYY_MM_DD
        r'(\d{4})(\d{2})(\d{2})',                                            # YYYYMMDD
        r'(\d{2})[-_](\d{2})[-_](\d{4})',                                    # DD-MM-YYYY or DD_MM_YYYY
        r'(\d{2})(\d{2})(\d{4})',                                            # DDMMYYYY
        r'IMG_(\d{4})(\d{2})(\d{2})',                                        # IMG_YYYYMMDD
        r'VID_(\d{4})(\d{2})(\d{2})',                                        # VID_YYYYMMDD
        
        # Screenshot patterns with timestamps
        r'Screenshot_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})',      # Screenshot_YYYY-MM-DD-HH-MM-SS
        r'Screen Shot (\d{4})-(\d{2})-(\d{2}) at (\d{1,2})\.(\d{2})\.(\d{2})', # Screen Shot YYYY-MM-DD at H.MM.SS
    ]
    
    def __init__(self):
        self.media_files: List[MediaFile] = []
        self.stats = {
            'total_files': 0,
            'image_files': 0,
            'video_files': 0,
            'missing_datetime_original': 0,
            'missing_date_created': 0,
            'files_with_suggestions': 0
        }
    
    def analyze_folder(self, folder_path: Union[str, Path]) -> List[MediaFile]:
        """Analyze all media files in a folder for missing EXIF date information."""
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")
        
        self.media_files = []
        self.stats = {key: 0 for key in self.stats.keys()}
        
        # Find all media files
        media_files = []
        for ext in self.IMAGE_EXTENSIONS | self.VIDEO_EXTENSIONS:
            media_files.extend(folder.rglob(f'*{ext}'))
        
        self.stats['total_files'] = len(media_files)
        
        # Analyze each file
        for file_path in media_files:
            try:
                media_file = self._analyze_file(file_path)
                self.media_files.append(media_file)
                
                # Update statistics
                if media_file.extension in self.IMAGE_EXTENSIONS:
                    self.stats['image_files'] += 1
                else:
                    self.stats['video_files'] += 1
                
                if not media_file.datetime_original:
                    self.stats['missing_datetime_original'] += 1
                
                if not media_file.date_created:
                    self.stats['missing_date_created'] += 1
                
                if media_file.suggested_date:
                    self.stats['files_with_suggestions'] += 1
                    
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                continue
        
        return self.media_files
    
    def _analyze_file(self, file_path: Path) -> MediaFile:
        """Analyze a single media file for date information."""
        media_file = MediaFile(file_path)
        
        # Extract EXIF data
        if media_file.extension in self.IMAGE_EXTENSIONS:
            self._extract_image_exif(media_file)
        elif media_file.extension in self.VIDEO_EXTENSIONS:
            self._extract_video_metadata(media_file)
        
        # Extract date from filename
        self._extract_filename_date(media_file)
        
        # Determine missing dates
        self._identify_missing_dates(media_file)
        
        # Suggest the best available date
        self._suggest_date(media_file)
        
        return media_file
    
    def _extract_image_exif(self, media_file: MediaFile):
        """Extract EXIF data from image files."""
        try:
            # Try with PIL first
            with Image.open(media_file.path) as img:
                # Use getexif() instead of deprecated _getexif()
                exif_dict = img.getexif()
                
                if exif_dict:
                    for tag_id, value in exif_dict.items():
                        tag = TAGS.get(tag_id, tag_id)
                        
                        if tag == 'DateTimeOriginal':
                            media_file.datetime_original = self._parse_exif_datetime(value)
                        elif tag == 'DateTime':
                            media_file.date_created = self._parse_exif_datetime(value)
                        elif tag == 'DateTimeDigitized':
                            media_file.datetime_digitized = self._parse_exif_datetime(value)
            
            # Fallback to exifread for more detailed extraction
            if not media_file.datetime_original:
                try:
                    with open(media_file.path, 'rb') as f:
                        tags = exifread.process_file(f, stop_tag='EXIF DateTimeDigitized')
                        
                        if 'EXIF DateTimeOriginal' in tags:
                            media_file.datetime_original = self._parse_exif_datetime(str(tags['EXIF DateTimeOriginal']))
                        
                        if 'EXIF DateTime' in tags and not media_file.date_created:
                            media_file.date_created = self._parse_exif_datetime(str(tags['EXIF DateTime']))
                        
                        if 'EXIF DateTimeDigitized' in tags:
                            media_file.datetime_digitized = self._parse_exif_datetime(str(tags['EXIF DateTimeDigitized']))
                except Exception as e:
                    # Some image files might have corrupted or unsupported EXIF data
                    print(f"Info: Could not extract detailed EXIF from {media_file.name}: {e}")
                        
        except Exception as e:
            print(f"Error extracting EXIF from {media_file.path}: {e}")
    
    def _extract_video_metadata(self, media_file: MediaFile):
        """Video metadata extraction is not currently implemented."""
        # Video metadata extraction is not implemented - skip processing
        # Users can still rely on filename parsing and file system dates
        pass
    
    def _extract_filename_date(self, media_file: MediaFile):
        """Extract date information from filename."""
        filename = media_file.name
        
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    
                    # Initialize default values
                    year, month, day = None, None, None
                    hour, minute, second = 0, 0, 0
                    
                    # Handle different date formats based on number of groups and first group length
                    if len(groups) >= 3:
                        if len(groups[0]) == 4:  # Year first format (YYYY-MM-DD...)
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                            
                            # Extract time components if available
                            if len(groups) >= 6:  # Has time components
                                hour = int(groups[3])
                                minute = int(groups[4])
                                second = int(groups[5])
                            elif len(groups) == 4:  # Special case for some formats
                                # Could be hour only, skip for now
                                pass
                                
                        elif len(groups[0]) == 2 and len(groups[2]) == 4:  # Day first format (DD-MM-YYYY)
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                            
                        elif len(groups[0]) == 2 and len(groups[1]) == 2 and len(groups[2]) == 4:  # DDMMYYYY
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                            
                        # Validate date components
                        if year and month and day:
                            if 1 <= month <= 12 and 1 <= day <= 31 and 1990 <= year <= 2100:
                                if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                                    media_file.filename_date = datetime(year, month, day, hour, minute, second)
                                    break
                        
                except (ValueError, IndexError):
                    continue
    
    def _identify_missing_dates(self, media_file: MediaFile):
        """Identify which date fields are missing."""
        media_file.missing_dates = []
        
        if not media_file.datetime_original:
            media_file.missing_dates.append('DateTimeOriginal')
        
        if not media_file.date_created:
            media_file.missing_dates.append('DateCreated')
    
    def _suggest_date(self, media_file: MediaFile):
        """Suggest the best available date for missing fields, prioritizing the earliest date."""
        candidates = []
        
        # Collect all available date sources in order of preference
        if media_file.datetime_original:
            candidates.append((media_file.datetime_original, 'EXIF DateTimeOriginal'))
        
        if media_file.date_created:
            candidates.append((media_file.date_created, 'EXIF DateTime'))
        
        if media_file.datetime_digitized:
            candidates.append((media_file.datetime_digitized, 'EXIF DateTimeDigitized'))
        
        if media_file.filename_date:
            candidates.append((media_file.filename_date, 'Filename Date'))
        
        if media_file.creation_date:
            candidates.append((media_file.creation_date, 'File Creation Date'))
        
        if media_file.modification_date:
            candidates.append((media_file.modification_date, 'File Modification Date'))
        
        # Filter out obviously invalid dates (future dates or dates before digital photography era)
        valid_candidates = []
        for date, source in candidates:
            if date.year >= 1990 and date <= datetime.now():
                valid_candidates.append((date, source))
        
        # Store all available sources
        media_file.available_sources = valid_candidates.copy()
        
        # Only suggest if there are missing dates
        if not media_file.missing_dates or not valid_candidates:
            return
        
        # Priority logic: If one EXIF date exists and the other is missing, use the existing one
        best_date = None
        source = None
        
        # Check for existing EXIF dates to use as suggestions for missing counterparts
        if 'DateTimeOriginal' in media_file.missing_dates and media_file.date_created:
            # DateTimeOriginal is missing but DateCreated exists - use DateCreated
            best_date = media_file.date_created
            source = 'EXIF DateTime'
        elif 'DateCreated' in media_file.missing_dates and media_file.datetime_original:
            # DateCreated is missing but DateTimeOriginal exists - use DateTimeOriginal
            best_date = media_file.datetime_original
            source = 'EXIF DateTimeOriginal'
        
        # If no EXIF date prioritization applies, use the original earliest-date logic
        if not best_date:
            # Define reliable sources (non-file system dates)
            reliable_sources = {'EXIF DateTimeOriginal', 'EXIF DateTime', 'EXIF DateTimeDigitized', 'Filename Date'}
            reliable_candidates = [c for c in valid_candidates if c[1] in reliable_sources]
            
            if reliable_candidates:
                # Among reliable sources, choose the earliest date
                best_date, source = min(reliable_candidates, key=lambda x: x[0])
            else:
                # If no reliable sources, fall back to earliest of all available dates
                best_date, source = min(valid_candidates, key=lambda x: x[0])
        
        media_file.suggested_date = best_date
        media_file.source = source
    
    def _parse_exif_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse EXIF datetime string."""
        try:
            # EXIF datetime format: 'YYYY:MM:DD HH:MM:SS'
            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except (ValueError, TypeError):
            return None
    
    def get_files_with_missing_dates(self) -> List[MediaFile]:
        """Get all files that have missing date information."""
        return [f for f in self.media_files if f.missing_dates]
    
    def get_files_with_suggestions(self) -> List[MediaFile]:
        """Get all files that have date suggestions."""
        return [f for f in self.media_files if f.suggested_date]
    
    def print_summary(self):
        """Print a summary of the analysis."""
        print("\n" + "="*60)
        print("EXIF DATE ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total files analyzed: {self.stats['total_files']}")
        print(f"Image files: {self.stats['image_files']}")
        print(f"Video files: {self.stats['video_files']}")
        print(f"Files missing DateTimeOriginal: {self.stats['missing_datetime_original']}")
        print(f"Files missing DateCreated: {self.stats['missing_date_created']}")
        print(f"Files with date suggestions: {self.stats['files_with_suggestions']}")
        print("="*60)
