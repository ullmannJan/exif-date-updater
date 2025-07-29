"""
Command-line interface for the EXIF Date Updater.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from .exif_analyzer import ExifAnalyzer, MediaFile
from .exif_updater import ExifUpdater


def print_file_analysis(media_files: List[MediaFile]):
    """Print detailed analysis of files with missing dates."""
    if not media_files:
        print("No files with missing dates found.")
        return
    
    print("\n" + "="*80)
    print("FILES WITH MISSING EXIF DATES")
    print("="*80)
    
    for file in media_files:
        print(f"\nFile: {file.name}")
        print(f"Path: {file.path}")
        print(f"Size: {file.size:,} bytes")
        print(f"Missing dates: {', '.join(file.missing_dates)}")
        
        # Show available dates
        print("Available dates:")
        if file.datetime_original:
            print(f"  - EXIF DateTimeOriginal: {file.datetime_original}")
        if file.date_created:
            print(f"  - EXIF DateTime: {file.date_created}")
        if file.datetime_digitized:
            print(f"  - EXIF DateTimeDigitized: {file.datetime_digitized}")
        if file.filename_date:
            print(f"  - Filename Date: {file.filename_date}")
        if file.creation_date:
            print(f"  - File Creation Date: {file.creation_date}")
        if file.modification_date:
            print(f"  - File Modification Date: {file.modification_date}")
        
        # Show suggestion
        if file.suggested_date:
            print(f"Suggested date: {file.suggested_date} "
                  f"(source: {file.source})")
        else:
            print("No date suggestion available")
        
        print("-" * 80)


def print_update_preview(media_files: List[MediaFile]):
    """Print preview of what dates will be written."""
    files_to_update = [f for f in media_files if f.suggested_date and f.missing_dates]
    
    if not files_to_update:
        print("No files will be updated.")
        return
    
    print("\n" + "="*80)
    print("UPDATE PREVIEW - The following dates will be written:")
    print("="*80)
    
    for file in files_to_update:
        print(f"\nFile: {file.name}")
        print(f"Suggested date: {file.suggested_date} (from {file.source})")
        print(f"Will update: {', '.join(file.missing_dates)}")
    
    print("-" * 80)
    print(f"Total files to update: {len(files_to_update)}")


def confirm_update() -> bool:
    """Ask user to confirm the update operation."""
    while True:
        response = input("\nProceed with updating EXIF dates? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Analyze and update missing EXIF date information in image files and extract dates from video filenames"
    )
    
    parser.add_argument(
        "folder",
        type=str,
        help="Path to the folder containing media files"
    )
    
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update EXIF dates (default: analyze only)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup files when updating"
    )
    
    parser.add_argument(
        "--datetime-original",
        action="store_true",
        default=True,
        help="Update DateTimeOriginal field (default: enabled)"
    )
    
    parser.add_argument(
        "--no-datetime-original",
        action="store_true",
        help="Don't update DateTimeOriginal field"
    )
    
    parser.add_argument(
        "--date-created",
        action="store_true",
        default=True,
        help="Update DateTime/DateCreated field (default: enabled)"
    )
    
    parser.add_argument(
        "--no-date-created",
        action="store_true",
        help="Don't update DateTime/DateCreated field"
    )
    
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed file analysis"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f"Error: Folder '{args.folder}' does not exist.")
        sys.exit(1)
    
    if not folder_path.is_dir():
        print(f"Error: '{args.folder}' is not a directory.")
        sys.exit(1)
    
    # Determine update flags
    update_datetime_original = args.datetime_original and not args.no_datetime_original
    update_date_created = args.date_created and not args.no_date_created
    
    if not update_datetime_original and not update_date_created:
        print("Error: At least one date field must be enabled for updates.")
        sys.exit(1)
    
    # Analyze files
    print(f"Analyzing media files in: {folder_path}")
    print("This may take a moment for large collections...")
    
    analyzer = ExifAnalyzer()
    try:
        analyzer.analyze_folder(folder_path)
    except Exception as e:
        print(f"Error analyzing folder: {e}")
        sys.exit(1)
    
    # Print summary
    analyzer.print_summary()
    
    # Get files with missing dates
    missing_dates_files = analyzer.get_files_with_missing_dates()
    
    if args.detailed:
        print_file_analysis(missing_dates_files)
    
    # If update mode
    if args.update or args.dry_run:
        files_with_suggestions = analyzer.get_files_with_suggestions()
        print_update_preview(files_with_suggestions)
        
        if not files_with_suggestions:
            print("No files have date suggestions for updating.")
            return
        
        if args.dry_run:
            print("\n[DRY RUN MODE] - No actual changes will be made")
            updater = ExifUpdater(create_backup=not args.no_backup)
            successful, failed = updater.update_multiple_files(
                files_with_suggestions,
                update_datetime_original,
                update_date_created,
                dry_run=True
            )
        else:
            # Confirm update
            if not confirm_update():
                print("Update cancelled.")
                return
            
            # Perform update
            print("\nUpdating EXIF dates...")
            updater = ExifUpdater(create_backup=not args.no_backup)
            successful, failed = updater.update_multiple_files(
                files_with_suggestions,
                update_datetime_original,
                update_date_created,
                dry_run=False
            )
            
            updater.print_update_summary()
            
            if successful > 0:
                print(f"\nSuccessfully updated {successful} files.")
                if not args.no_backup:
                    print("Original files have been backed up with .backup extension.")
            
            if failed > 0:
                print(f"Failed to update {failed} files. Check the output above for details.")
    
    else:
        # Analysis only mode
        if missing_dates_files:
            print(f"\nFound {len(missing_dates_files)} files with missing EXIF dates.")
            print("Use --update to update them or --detailed to see more information.")
        else:
            print("\nAll files have complete EXIF date information!")


if __name__ == "__main__":
    main()
