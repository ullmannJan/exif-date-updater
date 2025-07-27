#!/usr/bin/env python3
"""
Example usage of the EXIF Date Updater module.
"""

from pathlib import Path
from exif_date_updater import ExifAnalyzer, ExifUpdater


def main():
    """Example usage of the EXIF Date Updater."""
    
    # Example folder path - replace with your own
    folder_path = Path("./sample_photos")
    
    if not folder_path.exists():
        print(f"Example folder {folder_path} does not exist.")
        print("Please create a folder with some image/video files to test.")
        return
    
    print("EXIF Date Updater - Example Usage")
    print("=" * 50)
    
    # Step 1: Initialize the analyzer
    analyzer = ExifAnalyzer()
    
    # Step 2: Analyze the folder
    print(f"\nAnalyzing files in: {folder_path}")
    media_files = analyzer.analyze_folder(folder_path)
    
    # Step 3: Print summary
    analyzer.print_summary()
    
    # Step 4: Show files with missing dates
    missing_files = analyzer.get_files_with_missing_dates()
    
    if not missing_files:
        print("\nAll files have complete EXIF date information!")
        return
    
    print(f"\n{len(missing_files)} files have missing EXIF dates:")
    print("-" * 50)
    
    for file in missing_files:
        print(f"\nFile: {file.name}")
        print(f"Missing: {', '.join(file.missing_dates)}")
        
        if file.suggested_date:
            print(f"Suggested date: {file.suggested_date}")
            print(f"Source: {getattr(file, 'source', 'Unknown')}")
            print(f"Confidence: {file.confidence:.1%}")
        else:
            print("No date suggestion available")
    
    # Step 5: Ask user if they want to update
    print("\n" + "=" * 50)
    choice = input("Do you want to update these files? (y/n): ").lower().strip()
    
    if choice not in ['y', 'yes']:
        print("Update cancelled.")
        return
    
    # Step 6: Perform dry run first
    print("\nPerforming dry run...")
    updater = ExifUpdater(create_backup=True)
    
    files_to_update = [f for f in missing_files if f.suggested_date]
    successful, failed = updater.update_multiple_files(
        files_to_update,
        update_datetime_original=True,
        update_date_created=True,
        dry_run=True
    )
    
    print(f"Dry run complete: {successful} would succeed, {failed} would fail")
    
    # Step 7: Confirm actual update
    choice = input("\nProceed with actual update? (y/n): ").lower().strip()
    
    if choice not in ['y', 'yes']:
        print("Update cancelled.")
        return
    
    # Step 8: Perform actual update
    print("\nUpdating files...")
    updater = ExifUpdater(create_backup=True)
    
    successful, failed = updater.update_multiple_files(
        files_to_update,
        update_datetime_original=True,
        update_date_created=True,
        dry_run=False
    )
    
    updater.print_update_summary()
    
    print(f"\nUpdate complete!")
    print(f"Successfully updated: {successful} files")
    print(f"Failed: {failed} files")
    
    if successful > 0:
        print("\nBackup files have been created with .backup extension.")
        print("You can restore them using updater.restore_backup() if needed.")


if __name__ == "__main__":
    main()
