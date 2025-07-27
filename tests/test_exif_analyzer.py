"""Tests for the ExifAnalyzer module."""

import unittest
from pathlib import Path
from datetime import datetime

from exif_date_updater import ExifAnalyzer
from tests.test_utils import TestFileManager, get_sample_files


class TestExifAnalyzer(unittest.TestCase):
    """Test cases for ExifAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ExifAnalyzer()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        self.assertIsInstance(self.analyzer, ExifAnalyzer)
        self.assertEqual(len(self.analyzer.media_files), 0)
        self.assertIsInstance(self.analyzer.stats, dict)
    
    def test_supported_extensions(self):
        """Test supported file extensions."""
        # Test image extensions
        expected_image_exts = {'.jpg', '.jpeg', '.tiff', '.tif', '.png', '.bmp', '.gif', '.webp', '.heic', '.heif'}
        self.assertEqual(self.analyzer.IMAGE_EXTENSIONS, expected_image_exts)
        
        # Test video extensions
        expected_video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mts', '.m2ts'}
        self.assertEqual(self.analyzer.VIDEO_EXTENSIONS, expected_video_exts)
    
    def test_filename_date_patterns(self):
        """Test filename date pattern recognition."""
        test_cases = [
            ("IMG_20231215_142030.jpg", datetime(2023, 12, 15, 14, 20, 30)),
            ("20231201_vacation.jpg", datetime(2023, 12, 1, 0, 0, 0)),
            ("DSC_2024-01-01_12-30-45.jpg", datetime(2024, 1, 1, 12, 30, 45)),
            ("VID_20240325_090000.mp4", datetime(2024, 3, 25, 9, 0, 0)),
            ("2023-12-25_christmas.jpg", datetime(2023, 12, 25, 0, 0, 0)),
            ("IMG20231130.jpg", datetime(2023, 11, 30, 0, 0, 0)),
            ("photo_without_date.jpg", None),
            ("random_file.jpg", None),
        ]
        
        for filename, expected_date in test_cases:
            with self.subTest(filename=filename):
                # Create a temporary MediaFile-like object to test date extraction
                from exif_date_updater.exif_analyzer import MediaFile
                temp_path = Path("/tmp") / filename  # Dummy path for testing
                
                # We'll test the pattern matching logic indirectly
                # by checking if our patterns would match
                import re
                
                found_date = None
                for pattern in self.analyzer.DATE_PATTERNS:
                    match = re.search(pattern, filename)
                    if match:
                        try:
                            groups = match.groups()
                            if len(groups) >= 3:
                                if len(groups[0]) == 4:  # Year first
                                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                                else:  # Day first
                                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                                
                                hour = int(groups[3]) if len(groups) > 3 else 0
                                minute = int(groups[4]) if len(groups) > 4 else 0
                                second = int(groups[5]) if len(groups) > 5 else 0
                                
                                found_date = datetime(year, month, day, hour, minute, second)
                                break
                        except (ValueError, IndexError):
                            continue
                
                self.assertEqual(found_date, expected_date, 
                               f"Failed to extract correct date from {filename}")
    
    def test_analyze_folder_with_test_files(self):
        """Test analyzing a folder with test files."""
        with TestFileManager() as temp_dir:
            # Analyze the test directory
            media_files = self.analyzer.analyze_folder(temp_dir)
            
            # Verify results
            self.assertGreater(len(media_files), 0, "Should find test files")
            
            # Check statistics
            self.assertEqual(self.analyzer.stats['total_files'], len(media_files))
            self.assertGreaterEqual(self.analyzer.stats['image_files'], 0)
            self.assertGreaterEqual(self.analyzer.stats['missing_datetime_original'], 0)
            
            # Verify that files with date patterns have suggestions
            files_with_date_patterns = [f for f in media_files 
                                      if any(pattern in f.name for pattern in ['IMG_', '2023', '2024'])]
            
            for file in files_with_date_patterns:
                if file.missing_dates:
                    self.assertIsNotNone(file.suggested_date, 
                                       f"File {file.name} should have a suggested date")
    
    def test_get_files_with_missing_dates(self):
        """Test getting files with missing dates."""
        with TestFileManager() as temp_dir:
            self.analyzer.analyze_folder(temp_dir)
            missing_files = self.analyzer.get_files_with_missing_dates()
            
            # All test files should have missing dates (no EXIF in test images)
            self.assertGreater(len(missing_files), 0)
            
            # Verify all returned files actually have missing dates
            for file in missing_files:
                self.assertTrue(len(file.missing_dates) > 0,
                              f"File {file.name} should have missing dates")
    
    def test_get_files_with_suggestions(self):
        """Test getting files with date suggestions."""
        with TestFileManager() as temp_dir:
            self.analyzer.analyze_folder(temp_dir)
            suggested_files = self.analyzer.get_files_with_suggestions()
            
            # Some files should have suggestions (those with date patterns)
            self.assertGreater(len(suggested_files), 0)
            
            # Verify all returned files actually have suggestions
            for file in suggested_files:
                self.assertIsNotNone(file.suggested_date,
                                   f"File {file.name} should have a suggested date")
                self.assertGreater(file.confidence, 0,
                                 f"File {file.name} should have confidence > 0")
    
    def test_analyze_nonexistent_folder(self):
        """Test analyzing a non-existent folder."""
        nonexistent_path = Path("/this/path/does/not/exist")
        
        with self.assertRaises(ValueError):
            self.analyzer.analyze_folder(nonexistent_path)
    
    def test_confidence_scoring(self):
        """Test that confidence scoring works correctly."""
        with TestFileManager() as temp_dir:
            self.analyzer.analyze_folder(temp_dir)
            suggested_files = self.analyzer.get_files_with_suggestions()
            
            for file in suggested_files:
                # Confidence should be between 0 and 1
                self.assertGreaterEqual(file.confidence, 0)
                self.assertLessEqual(file.confidence, 1)
                
                # Files with filename dates should have specific confidence
                if file.filename_date:
                    self.assertEqual(file.confidence, 0.7,
                                   f"Filename date should have 0.7 confidence for {file.name}")


if __name__ == '__main__':
    unittest.main()
