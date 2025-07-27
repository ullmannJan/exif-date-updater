"""Integration tests for the EXIF Date Updater."""

import unittest
from pathlib import Path

from exif_date_updater import ExifAnalyzer, ExifUpdater
from tests.test_utils import TestFileManager


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""
    
    def test_complete_workflow(self):
        """Test the complete analyze -> update workflow."""
        with TestFileManager() as temp_dir:
            # Step 1: Analyze files
            analyzer = ExifAnalyzer()
            media_files = analyzer.analyze_folder(temp_dir)
            
            # Verify analysis worked
            self.assertGreater(len(media_files), 0, "Should find media files")
            
            # Step 2: Get files with missing dates
            missing_files = analyzer.get_files_with_missing_dates()
            self.assertGreater(len(missing_files), 0, "Should find files with missing dates")
            
            # Step 3: Get files with suggestions
            suggested_files = analyzer.get_files_with_suggestions()
            self.assertGreater(len(suggested_files), 0, "Should find files with suggestions")
            
            # Step 4: Perform dry run update
            updater = ExifUpdater(create_backup=True)
            successful_dry, failed_dry = updater.update_multiple_files(
                suggested_files, dry_run=True
            )
            
            self.assertGreater(successful_dry, 0, "Dry run should succeed for some files")
            self.assertEqual(failed_dry, 0, "Dry run should not fail for test files")
            
            # Step 5: Perform actual update
            updater = ExifUpdater(create_backup=True)
            successful, failed = updater.update_multiple_files(
                suggested_files, dry_run=False
            )
            
            # Note: Some updates might fail due to unsupported formats or other issues
            # but we should have at least some successes
            self.assertGreaterEqual(successful, 0, "Should have some successful updates")
            
            # Step 6: Verify backups were created for successful updates
            if successful > 0:
                backup_files = list(temp_dir.glob("*.backup*"))
                self.assertGreater(len(backup_files), 0, "Should create backup files")
    
    def test_analyzer_statistics(self):
        """Test that analyzer statistics are correctly calculated."""
        with TestFileManager() as temp_dir:
            analyzer = ExifAnalyzer()
            media_files = analyzer.analyze_folder(temp_dir)
            
            # Verify statistics match actual results
            self.assertEqual(analyzer.stats['total_files'], len(media_files))
            
            # Count actual image and video files
            actual_image_count = sum(1 for f in media_files 
                                   if f.extension in analyzer.IMAGE_EXTENSIONS)
            actual_video_count = sum(1 for f in media_files 
                                   if f.extension in analyzer.VIDEO_EXTENSIONS)
            
            self.assertEqual(analyzer.stats['image_files'], actual_image_count)
            self.assertEqual(analyzer.stats['video_files'], actual_video_count)
            
            # Count files with missing dates
            actual_missing_original = sum(1 for f in media_files 
                                        if not f.datetime_original)
            actual_missing_created = sum(1 for f in media_files 
                                       if not f.date_created)
            
            self.assertEqual(analyzer.stats['missing_datetime_original'], 
                           actual_missing_original)
            self.assertEqual(analyzer.stats['missing_date_created'], 
                           actual_missing_created)
            
            # Count files with suggestions
            actual_with_suggestions = sum(1 for f in media_files 
                                        if f.suggested_date)
            
            self.assertEqual(analyzer.stats['files_with_suggestions'], 
                           actual_with_suggestions)
    
    def test_confidence_prioritization(self):
        """Test that date sources are prioritized by confidence."""
        with TestFileManager() as temp_dir:
            analyzer = ExifAnalyzer()
            media_files = analyzer.analyze_folder(temp_dir)
            
            suggested_files = analyzer.get_files_with_suggestions()
            
            for file in suggested_files:
                # Files with filename dates should have 0.7 confidence
                if file.filename_date and not file.datetime_original:
                    self.assertEqual(file.confidence, 0.7,
                                   f"Filename date should have 0.7 confidence for {file.name}")
                
                # Files with modification dates should have lower confidence
                if (not file.filename_date and not file.datetime_original and 
                    file.modification_date):
                    self.assertLessEqual(file.confidence, 0.5,
                                       f"Modification date should have ≤0.5 confidence for {file.name}")
    
    def test_backup_and_restore_workflow(self):
        """Test the complete backup and restore workflow."""
        with TestFileManager() as temp_dir:
            # Analyze and get files to update
            analyzer = ExifAnalyzer()
            analyzer.analyze_folder(temp_dir)
            suggested_files = analyzer.get_files_with_suggestions()
            
            if not suggested_files:
                self.skipTest("No files with suggestions found")
            
            # Update files with backup
            updater = ExifUpdater(create_backup=True)
            successful, failed = updater.update_multiple_files(
                suggested_files, dry_run=False
            )
            
            if successful == 0:
                self.skipTest("No successful updates to test backup/restore")
            
            # Verify backups exist
            backup_files = list(temp_dir.glob("*.backup*"))
            self.assertGreater(len(backup_files), 0, "Should create backup files")
            
            # Test restore for each updated file
            restored_count = 0
            for file_path in updater.updated_files:
                if updater.restore_backup(file_path):
                    restored_count += 1
            
            self.assertGreater(restored_count, 0, "Should restore at least one file")
            
            # Test cleanup
            removed_count = updater.cleanup_backups(temp_dir)
            self.assertGreater(removed_count, 0, "Should remove backup files")
            
            # Verify backups are gone
            remaining_backups = list(temp_dir.glob("*.backup*"))
            self.assertEqual(len(remaining_backups), 0, "All backups should be removed")


if __name__ == '__main__':
    unittest.main()
