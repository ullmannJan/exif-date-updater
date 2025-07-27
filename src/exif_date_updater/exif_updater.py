"""
EXIF Date Updater - Module for updating EXIF date information in media files.
"""

import shutil
from pathlib import Path
from typing import List

from PIL import Image
import piexif

from .exif_analyzer import MediaFile


class ExifUpdater:
    """Class for updating EXIF date information in media files."""
    
    def __init__(self, create_backup: bool = True):
        self.create_backup = create_backup
        self.updated_files = []
        self.failed_updates = []
    
    def update_file_dates(self, media_file: MediaFile, 
                         update_datetime_original: bool = True,
                         update_date_created: bool = True,
                         dry_run: bool = False) -> bool:
        """
        Update EXIF dates for a single media file.
        
        Args:
            media_file: MediaFile object with suggested date
            update_datetime_original: Whether to update DateTimeOriginal
            update_date_created: Whether to update DateCreated/DateTime
            dry_run: If True, only simulate the update without actual changes
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not media_file.suggested_date:
            print(f"No suggested date for {media_file.name}")
            return False
        
        if not media_file.missing_dates:
            print(f"No missing dates for {media_file.name}")
            return False
        
        try:
            if dry_run:
                print(f"[DRY RUN] Would update {media_file.name} with date {media_file.suggested_date}")
                return True
            
            # Create backup if requested
            if self.create_backup:
                self._create_backup(media_file.path)
            
            # Update based on file type
            if media_file.path.suffix.lower() in {'.jpg', '.jpeg', '.tiff', '.tif'}:
                success = self._update_image_exif(media_file, update_datetime_original, update_date_created)
            else:
                print(f"EXIF update not supported for {media_file.path.suffix} files")
                return False
            
            if success:
                self.updated_files.append(media_file.path)
                print(f"Successfully updated {media_file.name}")
            else:
                self.failed_updates.append(media_file.path)
                print(f"Failed to update {media_file.name}")
            
            return success
            
        except Exception as e:
            print(f"Error updating {media_file.name}: {e}")
            self.failed_updates.append(media_file.path)
            return False
    
    def update_multiple_files(self, media_files: List[MediaFile],
                            update_datetime_original: bool = True,
                            update_date_created: bool = True,
                            dry_run: bool = False) -> tuple[int, int]:
        """
        Update EXIF dates for multiple media files.
        
        Returns:
            tuple: (successful_updates, failed_updates)
        """
        successful = 0
        failed = 0
        
        for media_file in media_files:
            if self.update_file_dates(media_file, update_datetime_original, 
                                    update_date_created, dry_run):
                successful += 1
            else:
                failed += 1
        
        return successful, failed
    
    def _create_backup(self, file_path: Path):
        """Create a backup of the original file."""
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        counter = 1
        
        # Handle multiple backups
        while backup_path.exists():
            backup_path = file_path.with_suffix(f'{file_path.suffix}.backup.{counter}')
            counter += 1
        
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path.name}")
    
    def _update_image_exif(self, media_file: MediaFile, 
                          update_datetime_original: bool,
                          update_date_created: bool) -> bool:
        """Update EXIF data for image files using piexif."""
        try:
            # Ensure we have a suggested date (double-check for safety)
            if not media_file.suggested_date:
                print(f"No suggested date available for {media_file.name}")
                return False
            
            # Format the date for EXIF (YYYY:MM:DD HH:MM:SS)
            try:
                exif_date_str = media_file.suggested_date.strftime('%Y:%m:%d %H:%M:%S')
            except AttributeError:
                print(f"Error formatting date for {media_file.name}: suggested_date is {media_file.suggested_date}")
                return False
            
            # Load existing EXIF data or create new
            try:
                exif_dict = piexif.load(str(media_file.path))
            except piexif.InvalidImageDataError:
                # Create new EXIF structure
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            # Update DateTimeOriginal if requested and missing
            if (update_datetime_original and 
                'DateTimeOriginal' in media_file.missing_dates):
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = exif_date_str
                print(f"  - Setting DateTimeOriginal: {exif_date_str}")
            
            # Update DateTime (DateCreated) if requested and missing
            if (update_date_created and 
                'DateCreated' in media_file.missing_dates):
                exif_dict["0th"][piexif.ImageIFD.DateTime] = exif_date_str
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = exif_date_str
                print(f"  - Setting DateTime/DateTimeDigitized: {exif_date_str}")
            
            # Convert back to bytes and save
            exif_bytes = piexif.dump(exif_dict)
            
            # Use PIL to save the image with new EXIF data
            with Image.open(media_file.path) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                img.save(media_file.path, exif=exif_bytes, quality=95, optimize=True)
            
            return True
            
        except Exception as e:
            print(f"Error updating EXIF for {media_file.name}: {e}")
            return False
    
    def restore_backup(self, file_path: Path) -> bool:
        """Restore a file from its backup."""
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        
        if not backup_path.exists():
            print(f"No backup found for {file_path.name}")
            return False
        
        try:
            shutil.copy2(backup_path, file_path)
            print(f"Restored {file_path.name} from backup")
            return True
        except Exception as e:
            print(f"Error restoring backup for {file_path.name}: {e}")
            return False
    
    def restore_all_backups(self, folder_path: Path) -> int:
        """Restore all backup files in a folder."""
        restored_count = 0
        backup_files = list(folder_path.glob('*.backup*'))
        
        for backup_file in backup_files:
            # Determine original filename
            if backup_file.name.endswith('.backup'):
                original_name = backup_file.name[:-7]  # Remove '.backup'
            else:
                # Handle .backup.1, .backup.2, etc.
                parts = backup_file.name.split('.backup.')
                if len(parts) == 2:
                    original_name = parts[0]
                else:
                    continue
            
            original_path = folder_path / original_name
            
            if self.restore_backup(original_path):
                restored_count += 1
        
        return restored_count
    
    def cleanup_backups(self, folder_path: Path) -> int:
        """Remove all backup files in a folder."""
        removed_count = 0
        backup_files = list(folder_path.glob('*.backup*'))
        
        for backup_file in backup_files:
            try:
                backup_file.unlink()
                print(f"Removed backup: {backup_file.name}")
                removed_count += 1
            except Exception as e:
                print(f"Error removing backup {backup_file.name}: {e}")
        
        return removed_count
    
    def print_update_summary(self):
        """Print a summary of the update operations."""
        print("\n" + "="*60)
        print("EXIF UPDATE SUMMARY")
        print("="*60)
        print(f"Successfully updated files: {len(self.updated_files)}")
        print(f"Failed updates: {len(self.failed_updates)}")
        
        if self.updated_files:
            print("\nSuccessfully updated:")
            for file_path in self.updated_files:
                print(f"  - {file_path.name}")
        
        if self.failed_updates:
            print("\nFailed to update:")
            for file_path in self.failed_updates:
                print(f"  - {file_path.name}")
        
        print("="*60)
