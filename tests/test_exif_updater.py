"""Tests for the ExifUpdater module."""

import unittest
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from exif_date_updater import ExifUpdater
from exif_date_updater.exif_analyzer import MediaFile
from tests.test_utils import create_test_image


class TestExifUpdater(unittest.TestCase):
    """Test cases for ExifUpdater class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.updater = ExifUpdater(create_backup=True)
        self.temp_dir = None
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def create_temp_dir(self):
        """Create a temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        return Path(self.temp_dir)
    
    def create_test_media_file(self, filename: str, suggested_date: Optional[datetime], 
                              missing_dates: list, confidence: float = 0.7) -> MediaFile:
        """Create a test MediaFile object."""
        temp_dir = self.create_temp_dir()
        file_path = temp_dir / filename
        
        # Create actual image file
        create_test_image(file_path)
        
        # Create MediaFile object
        media_file = MediaFile(file_path)
        media_file.suggested_date = suggested_date
        media_file.missing_dates = missing_dates
        media_file.confidence = confidence
        media_file.source = "Test Source"
        
        return media_file
    
    def test_updater_initialization(self):
        """Test updater initialization."""
        updater = ExifUpdater(create_backup=True)
        self.assertTrue(updater.create_backup)
        self.assertEqual(len(updater.updated_files), 0)
        self.assertEqual(len(updater.failed_updates), 0)
        
        updater_no_backup = ExifUpdater(create_backup=False)
        self.assertFalse(updater_no_backup.create_backup)
    
    def test_dry_run_update(self):
        """Test dry run update (should not modify files)."""
        media_file = self.create_test_media_file(
            "test_image.jpg",
            datetime(2023, 12, 15, 14, 20, 30),
            ["DateTimeOriginal", "DateCreated"]
        )
        
        # Get original file modification time
        original_mtime = media_file.path.stat().st_mtime
        
        # Perform dry run
        success = self.updater.update_file_dates(media_file, dry_run=True)
        
        # Verify dry run was successful but file wasn't modified
        self.assertTrue(success)
        self.assertEqual(media_file.path.stat().st_mtime, original_mtime)
        self.assertEqual(len(self.updater.updated_files), 0)
    
    def test_update_file_without_suggestion(self):
        """Test updating a file without a suggested date."""
        media_file = self.create_test_media_file(
            "test_image.jpg",
            None,  # No suggested date
            ["DateTimeOriginal"]
        )
        media_file.suggested_date = None
        
        success = self.updater.update_file_dates(media_file)
        self.assertFalse(success)
    
    def test_update_file_without_missing_dates(self):
        """Test updating a file with no missing dates."""
        media_file = self.create_test_media_file(
            "test_image.jpg",
            datetime(2023, 12, 15, 14, 20, 30),
            []  # No missing dates
        )
        
        success = self.updater.update_file_dates(media_file)
        self.assertFalse(success)
    
    def test_backup_creation(self):
        """Test that backup files are created."""
        media_file = self.create_test_media_file(
            "test_image.jpg",
            datetime(2023, 12, 15, 14, 20, 30),
            ["DateTimeOriginal"]
        )
        
        # Update file (this should create a backup)
        self.updater.update_file_dates(media_file, dry_run=False)
        
        # Check if backup was created
        backup_path = media_file.path.with_suffix(media_file.path.suffix + '.backup')
        self.assertTrue(backup_path.exists(), "Backup file should be created")
    
    def test_multiple_backup_handling(self):
        """Test handling of multiple backups."""
        media_file = self.create_test_media_file(
            "test_image.jpg",
            datetime(2023, 12, 15, 14, 20, 30),
            ["DateTimeOriginal"]
        )
        
        # Create first backup manually
        backup_path = media_file.path.with_suffix(media_file.path.suffix + '.backup')
        backup_path.write_text("first backup")
        
        # Update file (should create .backup.1)
        self.updater.update_file_dates(media_file, dry_run=False)
        
        backup_path_1 = media_file.path.with_suffix(media_file.path.suffix + '.backup.1')
        self.assertTrue(backup_path_1.exists(), "Second backup should be .backup.1")
    
    def test_restore_backup(self):
        """Test restoring a file from backup."""
        media_file = self.create_test_media_file(
            "test_image.jpg",
            datetime(2023, 12, 15, 14, 20, 30),
            ["DateTimeOriginal"]
        )
        
        # Get original content
        original_content = media_file.path.read_bytes()
        
        # Update file
        self.updater.update_file_dates(media_file, dry_run=False)
        
        # Modify the file to simulate changes
        media_file.path.write_text("modified content")
        
        # Restore from backup
        success = self.updater.restore_backup(media_file.path)
        self.assertTrue(success)
        
        # Verify restoration (content should be back to original)
        restored_content = media_file.path.read_bytes()
        self.assertEqual(restored_content, original_content)
    
    def test_restore_nonexistent_backup(self):
        """Test restoring when no backup exists."""
        media_file = self.create_test_media_file(
            "test_image.jpg",
            datetime(2023, 12, 15, 14, 20, 30),
            ["DateTimeOriginal"]
        )
        
        success = self.updater.restore_backup(media_file.path)
        self.assertFalse(success)
    
    def test_cleanup_backups(self):
        """Test cleaning up backup files."""
        temp_dir = self.create_temp_dir()
        
        # Create some test files and backups
        test_file = temp_dir / "test.jpg"
        backup_file = temp_dir / "test.jpg.backup"
        backup_file_1 = temp_dir / "test.jpg.backup.1"
        
        create_test_image(test_file)
        backup_file.write_text("backup 1")
        backup_file_1.write_text("backup 2")
        
        # Clean up backups
        removed_count = self.updater.cleanup_backups(temp_dir)
        
        self.assertEqual(removed_count, 2)
        self.assertFalse(backup_file.exists())
        self.assertFalse(backup_file_1.exists())
        self.assertTrue(test_file.exists())  # Original should remain
    
    def test_update_multiple_files(self):
        """Test updating multiple files."""
        media_files = [
            self.create_test_media_file(
                f"test_image_{i}.jpg",
                datetime(2023, 12, 15 + i, 14, 20, 30),
                ["DateTimeOriginal"]
            )
            for i in range(3)
        ]
        
        successful, failed = self.updater.update_multiple_files(
            media_files, dry_run=True
        )
        
        self.assertEqual(successful, 3)
        self.assertEqual(failed, 0)
    
    def test_unsupported_file_format(self):
        """Test updating unsupported file format."""
        media_file = self.create_test_media_file(
            "test_video.mp4",  # Unsupported for EXIF updates
            datetime(2023, 12, 15, 14, 20, 30),
            ["DateTimeOriginal"]
        )
        
        success = self.updater.update_file_dates(media_file, dry_run=False)
        self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()
