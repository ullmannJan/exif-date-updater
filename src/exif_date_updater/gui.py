"""
GUI interface for the EXIF Date Updater using PySide6.
"""

import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from PySide6.QtCore import QThread, Signal, Qt, QDateTime
from PySide6.QtGui import QFont, QTextCursor, QColor, QKeySequence, QShortcut, QPalette, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QTextEdit, QProgressBar, QCheckBox, QGroupBox, QMessageBox,
    QSplitter, QHeaderView, QStatusBar, QComboBox, QDateTimeEdit, QDialog
)

from .exif_analyzer import ExifAnalyzer, MediaFile
from .exif_updater import ExifUpdater
from .table_row import TableRow

class NumericTableWidgetItem(QTableWidgetItem):
    """QTableWidgetItem that sorts numerically while displaying formatted text."""
    
    def __init__(self, text: str, numeric_value: float):
        super().__init__(text)
        self.numeric_value = numeric_value
    
    def __lt__(self, other):
        """Compare numerically for sorting."""
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events to prevent interfering with table scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to allow table scrolling."""
        event.ignore()


class ManualDateDialog(QDialog):
    """Dialog for manually entering date and time."""
    
    def __init__(self, parent=None, initial_date=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Manual Date and Time")
        self.setModal(True)
        self.resize(300, 150)
        
        layout = QVBoxLayout(self)
        
        # Add instruction label
        instruction = QLabel("Enter the date and time for this file:")
        layout.addWidget(instruction)
        
        # Date/time picker
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
        self.datetime_edit.setCalendarPopup(True)
        
        # Set initial date - use provided date, current file's suggestion, or current time
        if initial_date:
            qt_datetime = QDateTime.fromSecsSinceEpoch(int(initial_date.timestamp()))
            self.datetime_edit.setDateTime(qt_datetime)
        else:
            # Default to current date/time
            self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        
        layout.addWidget(self.datetime_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def get_datetime(self) -> datetime:
        """Return the selected datetime as a Python datetime object."""
        qt_datetime = self.datetime_edit.dateTime()
        # Use toPython() method which is more reliable than timestamp conversion
        try:
            result = qt_datetime.toPython()
            # Ensure we got a datetime object
            if isinstance(result, datetime):
                return result
            else:
                # Fallback if toPython() didn't return a datetime
                raise ValueError("toPython() did not return a datetime object")
        except (OSError, ValueError, OverflowError, AttributeError):
            # Fallback: manually construct datetime from components
            date = qt_datetime.date()
            time = qt_datetime.time()
            return datetime(
                date.year(), date.month(), date.day(),
                time.hour(), time.minute(), time.second()
            )


class AnalysisWorker(QThread):
    """Worker thread for analyzing media files."""
    
    progress = Signal(str)  # Progress message
    finished = Signal(list)  # List of MediaFile objects
    error = Signal(str)  # Error message
    
    def __init__(self, folder_path: Path, ignore_videos: bool = False, include_subfolders: bool = True):
        super().__init__()
        self.folder_path = folder_path
        self.ignore_videos = ignore_videos
        self.include_subfolders = include_subfolders
        self.analyzer = ExifAnalyzer()
    
    def run(self):
        try:
            self.progress.emit("Starting analysis...")
            media_files = self.analyzer.analyze_folder(
                self.folder_path, 
                ignore_videos=self.ignore_videos,
                include_subfolders=self.include_subfolders
            )
            self.progress.emit(f"Analysis complete! Found {len(media_files)} files.")
            self.finished.emit(media_files)
        except Exception as e:
            self.error.emit(str(e))


class UpdateWorker(QThread):
    """Worker thread for updating EXIF data."""
    
    progress = Signal(str)  # Progress message
    finished = Signal(int, int)  # (successful, failed) counts
    error = Signal(str)  # Error message
    
    def __init__(self, media_files: List[MediaFile], 
                 update_datetime_original: bool,
                 update_date_created: bool,
                 create_backup: bool,
                 dry_run: bool = False):
        super().__init__()
        self.media_files = media_files
        self.update_datetime_original = update_datetime_original
        self.update_date_created = update_date_created
        self.updater = ExifUpdater(create_backup=create_backup)
        self.dry_run = dry_run
    
    def run(self):
        try:
            if self.dry_run:
                self.progress.emit("Running dry-run simulation...")
            else:
                self.progress.emit("Updating EXIF data...")
            
            successful = 0
            failed = 0
            
            # Process each file individually to provide per-file logging
            for i, file in enumerate(self.media_files, 1):
                try:
                    # Update individual file (handles both dry_run and actual updates)
                    result = self.updater.update_file_dates(
                        file,
                        self.update_datetime_original,
                        self.update_date_created,
                        dry_run=self.dry_run
                    )
                    
                    if result:
                        action = "Simulated" if self.dry_run else "Updated"
                        self.progress.emit(f"{action}: {file.name}")
                        successful += 1
                    else:
                        failed += 1
                            
                except Exception:
                    failed += 1
            
            self.finished.emit(successful, failed)
        except Exception as e:
            self.error.emit(str(e))


class ExifDateUpdaterGUI(QMainWindow):
    """Main GUI application for EXIF Date Updater."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EXIF Date Updater")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set window icon
        self.setup_window_icon()
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Data
        self.folder_path: Optional[Path] = None
        self.media_files: List[MediaFile] = []
        self.analyzer = ExifAnalyzer()
        
        # Table rows containing all UI state
        self.table_rows: List[TableRow] = []
        
        # Workers
        self.analysis_worker: Optional[AnalysisWorker] = None
        self.update_worker: Optional[UpdateWorker] = None
        
        # Setup UI
        self.setup_ui()
        self.setup_connections()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Drop a folder here or use the Select Folder button")
    
    def setup_window_icon(self):
        """Setup the window icon using the logo files."""
        try:
            # Get the path to the icons directory
            icons_dir = Path(__file__).parent / "resources" / "icons"
            
            # Create QIcon with multiple resolutions for crisp display at different sizes
            icon = QIcon()
            
            # Add the 128x128 version
            icon_128_path = icons_dir / "logo_128.png"
            if icon_128_path.exists():
                icon.addFile(str(icon_128_path))
            
            # Add the 256x256 version for higher DPI displays
            icon_256_path = icons_dir / "logo_256.png"
            if icon_256_path.exists():
                icon.addFile(str(icon_256_path))
            
            # Set the window icon
            if not icon.isNull():
                self.setWindowIcon(icon)
            else:
                print("Warning: Could not load application icon")
                
        except Exception as e:
            print(f"Error loading window icon: {e}")
    
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Top section - Folder selection
        folder_group = QGroupBox("Folder Selection")
        folder_group.setToolTip("Drag and drop a folder here or use the Select Folder button")
        folder_layout = QHBoxLayout(folder_group)
        
        self.folder_label = QLabel("No folder selected - Drag a folder here or click Select Folder")
        self.folder_label.setStyleSheet("QLabel { color: palette(disabled-text); font-style: italic; }")
        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.setToolTip("Select a folder containing media files (or drag and drop a folder into the window)")
        self.analyze_btn = QPushButton("Analyze Files")
        self.analyze_btn.setEnabled(False)
        
        folder_layout.addWidget(QLabel("Folder:"))
        folder_layout.addWidget(self.folder_label, 1)
        folder_layout.addWidget(self.select_folder_btn)
        folder_layout.addWidget(self.analyze_btn)
        
        layout.addWidget(folder_group)
        
        # Progress bar
        self.progress_bar = QProgressBar(alignment=Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Main content - Splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top pane - File table
        self.table_group = QGroupBox("Files with Missing EXIF Dates")
        table_layout = QVBoxLayout(self.table_group)
        
        # Add option to show all files
        table_options_layout = QHBoxLayout()
        self.show_all_files_cb = QCheckBox("Show all files (including those with complete EXIF data)")
        self.show_all_files_cb.setChecked(True)
        table_options_layout.addWidget(self.show_all_files_cb)
        
        # Add option to ignore video files
        self.ignore_video_files_cb = QCheckBox("Ignore video files")
        self.ignore_video_files_cb.setChecked(False)
        self.ignore_video_files_cb.setToolTip("Skip video files during folder analysis")
        table_options_layout.addWidget(self.ignore_video_files_cb)
        
        # Add option to include subfolders
        self.include_subfolders_cb = QCheckBox("Include subfolders")
        self.include_subfolders_cb.setChecked(False)
        self.include_subfolders_cb.setToolTip("Search recursively in subfolders for media files")
        table_options_layout.addWidget(self.include_subfolders_cb)
        
        # Add select all/none buttons
        self.select_all_btn = QPushButton("Select All")
        self.select_none_btn = QPushButton("Select None")
        self.select_rows_btn = QPushButton("Invert Selection")
        
        self.select_all_btn.setToolTip("Select all files that have date suggestions available")
        self.select_none_btn.setToolTip("Deselect all files")
        self.select_rows_btn.setToolTip("Invert the selection state of all currently highlighted/selected table rows")
        
        table_options_layout.addStretch()
        table_options_layout.addWidget(QLabel("Selection:"))
        table_options_layout.addWidget(self.select_all_btn)
        table_options_layout.addWidget(self.select_none_btn)
        table_options_layout.addWidget(self.select_rows_btn)
        
        table_layout.addLayout(table_options_layout)
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(7)
        self.file_table.setHorizontalHeaderLabels([
            "Update", "Filename", "Type", "DateTimeOriginal", "DateCreated", "Source", "Size"
        ])
        
        # Enable multiselect functionality
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Enable column sorting
        self.file_table.setSortingEnabled(True)
        
        # Connect selection change to update row appearance
        self.file_table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)
        
        # Add tooltips to column headers
        header = self.file_table.horizontalHeader()
        header.setToolTip("EXIF date values - missing values highlighted in red, use dropdowns to select date sources")
        
        # Set tooltips for each column header
        for col in range(self.file_table.columnCount()):
            item = self.file_table.horizontalHeaderItem(col)
            if item:
                if col == 0:
                    item.setToolTip("Check to include this file in the update process")
                elif col == 1:
                    item.setToolTip("Filename")
                elif col == 2:
                    item.setToolTip("File type/extension")
                elif col == 3:
                    item.setToolTip("Current DateTimeOriginal EXIF value (empty if missing)")
                elif col == 4:
                    item.setToolTip("Current DateCreated EXIF value (empty if missing)")
                elif col == 5:
                    item.setToolTip("Select date source from available options")
                elif col == 6:
                    item.setToolTip("File size in bytes")
        
        # Make table responsive
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Update checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Filename
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # DateTimeOriginal
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # DateCreated
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Source (dropdown menu)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Size
        
        # Set minimum width for source column to accommodate dropdown
        header.resizeSection(5, 250)
        
        table_layout.addWidget(self.file_table)
        splitter.addWidget(self.table_group)
        
        # Bottom pane - Options and log
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        
        # Options panel
        options_group = QGroupBox("Update Options")
        options_layout = QVBoxLayout(options_group)
        
        self.update_datetime_original_cb = QCheckBox("Update DateTimeOriginal")
        self.update_datetime_original_cb.setChecked(True)
        self.update_date_created_cb = QCheckBox("Update DateCreated")
        self.update_date_created_cb.setChecked(True)
        self.create_backup_cb = QCheckBox("Create backup files")
        self.create_backup_cb.setChecked(False)
        
        options_layout.addWidget(self.update_datetime_original_cb)
        options_layout.addWidget(self.update_date_created_cb)
        options_layout.addWidget(self.create_backup_cb)
        
        # Update buttons
        button_layout = QVBoxLayout()
        self.dry_run_btn = QPushButton("Dry Run (Preview)")
        self.update_btn = QPushButton("Update EXIF Data")
        self.dry_run_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        
        button_layout.addWidget(self.dry_run_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addStretch()
        
        options_layout.addLayout(button_layout)
        bottom_layout.addWidget(options_group)
        
        # Log panel
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        font = QFont("Consolas", 9)
        self.log_text.setFont(font)
        
        log_layout.addWidget(self.log_text)
        bottom_layout.addWidget(log_group, 1)
        
        splitter.addWidget(bottom_widget)
        layout.addWidget(splitter)
        
        # Set splitter proportions
        splitter.setSizes([600, 200])
    
    def setup_connections(self):
        """Setup signal connections."""
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.analyze_btn.clicked.connect(self.analyze_files)
        self.dry_run_btn.clicked.connect(self.dry_run_update)
        self.update_btn.clicked.connect(self.update_files)
        self.show_all_files_cb.stateChanged.connect(self.on_show_all_files_changed)
        self.ignore_video_files_cb.stateChanged.connect(self.on_ignore_video_files_changed)
        self.include_subfolders_cb.stateChanged.connect(self.on_include_subfolders_changed)
        
        # Connect update checkboxes to repopulate table when output options change
        self.update_datetime_original_cb.toggled.connect(self.populate_file_table)
        self.update_date_created_cb.toggled.connect(self.populate_file_table)
        
        # Selection buttons
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.select_none_btn.clicked.connect(self.select_no_files)
        self.select_rows_btn.clicked.connect(self.toggle_selected_rows)
        
        # Keyboard shortcuts for table operations
        select_all_shortcut = QShortcut(QKeySequence.StandardKey.SelectAll, self.file_table)
        select_all_shortcut.activated.connect(self.select_all_files)
        
        # Also add Ctrl+D for deselect all
        deselect_shortcut = QShortcut(QKeySequence("Ctrl+D"), self.file_table)
        deselect_shortcut.activated.connect(self.select_no_files)
        
        # Add spacebar to toggle checkboxes for selected rows
        toggle_shortcut = QShortcut(QKeySequence("Space"), self.file_table)
        toggle_shortcut.activated.connect(self.toggle_selected_rows)
    
    def select_folder(self):
        """Open folder selection dialog."""
        # Use currently selected folder as starting directory, if available
        start_directory = str(self.folder_path) if hasattr(self, 'folder_path') and self.folder_path else ""
        
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder containing media files", start_directory
        )
        
        if folder:
            self.folder_path = Path(folder)
            self.folder_label.setText(str(self.folder_path))
            self.folder_label.setStyleSheet("")  # Clear custom styling to use theme default
            self.analyze_btn.setEnabled(True)
            self.log(f"Selected folder: {self.folder_path}")
    
    def analyze_files(self):
        """Start file analysis in worker thread."""
        if not self.folder_path:
            return
        
        self.log("Starting file analysis...")
        if self.ignore_video_files_cb.isChecked():
            self.log("Video files will be ignored during analysis")
        if self.include_subfolders_cb.isChecked():
            self.log("Including subfolders in analysis")
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start worker thread
        ignore_videos = self.ignore_video_files_cb.isChecked()
        include_subfolders = self.include_subfolders_cb.isChecked()
        self.analysis_worker = AnalysisWorker(self.folder_path, ignore_videos, include_subfolders)
        self.analysis_worker.progress.connect(self.log)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.error.connect(self.on_analysis_error)
        self.analysis_worker.start()
    
    def on_analysis_finished(self, media_files: List[MediaFile]):
        """Handle analysis completion."""
        self.media_files = media_files
        
        # Create table rows for all files and tie them directly to the files
        self.create_table_rows()
        
        self.populate_file_table()
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        # Show summary
        missing_files = [row for row in self.table_rows if row.has_missing_dates]
        self.log(f"Analysis complete! Found {len(missing_files)} files with missing dates.")
        
        if missing_files:
            self.dry_run_btn.setEnabled(True)
            self.update_btn.setEnabled(True)
        
        self.update_status_bar()
    
    def create_table_rows(self):
        """Create TableRow objects for each MediaFile."""
        self.table_rows.clear()
        
        for media_file in self.media_files:
            row = TableRow(media_file=media_file)
            # Set up the update callback so the row can notify us of changes
            row.set_update_callback(self._on_table_row_updated)
            self.table_rows.append(row)
    
    def on_analysis_error(self, error_msg: str):
        """Handle analysis error."""
        self.log(f"Analysis error: {error_msg}")
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Analysis Error", f"Failed to analyze files:\n{error_msg}")
    
    def on_show_all_files_changed(self):
        """Handle change in show all files checkbox."""
        if self.media_files:
            self.populate_file_table()
            self.update_status_bar()
    
    def on_ignore_video_files_changed(self):
        """Handle change in ignore video files checkbox."""
        if self.media_files:
            self.populate_file_table()
            self.update_status_bar()
    
    def on_include_subfolders_changed(self):
        """Handle change in include subfolders checkbox."""
        # Note: This only affects future analysis runs, not current data
        # The user needs to re-analyze to see the effect
        pass
    
    def get_filtered_rows(self) -> List[TableRow]:
        """Get the current filtered list of table rows based on UI settings."""
        if self.show_all_files_cb.isChecked():
            rows_to_show = self.table_rows
        else:
            rows_to_show = [row for row in self.table_rows if row.has_missing_dates]
        
        # Filter out video files if the ignore option is checked
        if self.ignore_video_files_cb.isChecked():
            rows_to_show = [row for row in rows_to_show if not row.is_video_file]
        
        return rows_to_show
    
    def on_source_changed(self, row: int, combo_index: int):
        """Handle source selection change in dropdown."""
        print(f"DEBUG: on_source_changed called with row={row}, combo_index={combo_index}")
        
        combo = self.file_table.cellWidget(row, 5)  # Source column is now index 5
        print(f"DEBUG: Got combo from visual row {row}: {combo is not None}")
        
        if isinstance(combo, (QComboBox, NoScrollComboBox)) and combo_index >= 0:
            # Get the selected source data
            item_data = combo.itemData(combo_index)
            
            # Handle case where itemData returns None
            if item_data is None:
                print(f"Warning: No data found for combo index {combo_index} in row {row}")
                return
            
            # Ensure we can unpack the data
            try:
                date, source_name = item_data
            except (TypeError, ValueError):
                print(f"Warning: Invalid data format for combo index {combo_index} in row {row}: {item_data}")
                return
            
            # Get the TableRow object for this visual row
            table_row = self.get_table_row_for_visual_row(row)
            if not table_row:
                print(f"Warning: Could not find TableRow for visual row {row}")
                return
            
            # Check if manual option was selected (either "Manual..." or "Manual (date)")
            if source_name == "Manual":
                # Open manual date dialog
                current_file = table_row.media_file
                
                # Use existing suggested date as initial value, if available
                initial_date = None
                if hasattr(current_file, 'suggested_date') and current_file.suggested_date:
                    initial_date = current_file.suggested_date
                elif isinstance(date, datetime):
                    # If we already have a manual date stored in the combo, use that
                    initial_date = date
                
                dialog = ManualDateDialog(self, initial_date)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # User confirmed the manual date
                    manual_date = dialog.get_datetime()
                    
                    # Update the MediaFile object
                    current_file.suggested_date = manual_date
                    current_file.source = "Manual"
                    
                    # Update the combo box to show the manual date
                    date_str = manual_date.strftime("%Y-%m-%d %H:%M:%S")
                    manual_display = f"Manual ({date_str})"
                    combo.setItemText(combo_index, manual_display)
                    combo.setItemData(combo_index, (manual_date, "Manual"))
                    
                    # Notify the TableRow that it has been updated
                    # This will automatically handle the GUI updates through the callback
                    table_row._notify_update()
                    
                else:
                    # User cancelled - revert to previous selection
                    if hasattr(current_file, 'source') and current_file.source != "Manual":
                        # Find the previous source in the combo and select it
                        for i in range(combo.count()):
                            item_date, item_source = combo.itemData(i)
                            if item_source == current_file.source:
                                combo.setCurrentIndex(i)
                                break
                    else:
                        # If no previous source, select the first item (if available)
                        if combo.count() > 1:  # More than just the manual option
                            combo.setCurrentIndex(0)
                
                return
            
            # Handle regular (non-manual) source selection - ensure date is a datetime object
            if isinstance(date, datetime):
                file = table_row.media_file
                print(f"DEBUG: Updating {file.name} - Old suggested: {file.suggested_date}, New: {date}")
                
                file.suggested_date = date
                file.source = source_name
                print(f"DEBUG: Updated {file.name} - New suggested: {file.suggested_date}")
                
                # Notify the TableRow that it has been updated
                # This will automatically handle the GUI updates through the callback
                table_row._notify_update()

    def on_source_changed_by_table_row(self, table_row: 'TableRow', combo_index: int):
        """Handle source selection change using TableRow object directly (sorting-safe)."""
        print(f"DEBUG: on_source_changed_by_table_row called for {table_row.filename}, combo_index={combo_index}")
        
        combo = table_row.source_combo
        if not isinstance(combo, (QComboBox, NoScrollComboBox)) or combo_index < 0:
            return
        
        # Get the selected source data
        item_data = combo.itemData(combo_index)
        
        # Handle case where itemData returns None
        if item_data is None:
            print(f"Warning: No data found for combo index {combo_index} for {table_row.filename}")
            return
        
        # Ensure we can unpack the data
        try:
            date, source_name = item_data
        except (TypeError, ValueError):
            print(f"Warning: Invalid data format for combo index {combo_index} for {table_row.filename}: {item_data}")
            return
        
        # Check if manual option was selected (either "Manual..." or "Manual (date)")
        if source_name == "Manual":
            # Open manual date dialog
            current_file = table_row.media_file
            
            # Use existing suggested date as initial value, if available
            initial_date = None
            if hasattr(current_file, 'suggested_date') and current_file.suggested_date:
                initial_date = current_file.suggested_date
            elif isinstance(date, datetime):
                # If we already have a manual date stored in the combo, use that
                initial_date = date
            
            dialog = ManualDateDialog(self, initial_date)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # User confirmed the manual date
                manual_date = dialog.get_datetime()
                
                # Update the MediaFile object
                current_file.suggested_date = manual_date
                current_file.source = "Manual"
                
                # Update the combo box to show the manual date
                date_str = manual_date.strftime("%Y-%m-%d %H:%M:%S")
                manual_display = f"Manual ({date_str})"
                combo.setItemText(combo_index, manual_display)
                combo.setItemData(combo_index, (manual_date, "Manual"))
                
                # Notify the TableRow that it has been updated
                # This will automatically handle the GUI updates through the callback
                table_row._notify_update()
                
            else:
                # User cancelled - revert to previous selection
                if hasattr(current_file, 'source') and current_file.source != "Manual":
                    # Find the previous source in the combo and select it
                    for i in range(combo.count()):
                        item_date, item_source = combo.itemData(i)
                        if item_source == current_file.source:
                            combo.setCurrentIndex(i)
                            break
                else:
                    # If no previous source, select the first item (if available)
                    if combo.count() > 1:  # More than just the manual option
                        combo.setCurrentIndex(0)
            
            return
        
        # Handle regular (non-manual) source selection - ensure date is a datetime object
        if isinstance(date, datetime):
            file = table_row.media_file
            print(f"DEBUG: Updating {file.name} - Old suggested: {file.suggested_date}, New: {date}")
            
            file.suggested_date = date
            file.source = source_name
            print(f"DEBUG: Updated {file.name} - New suggested: {file.suggested_date}")
            
            # Notify the TableRow that it has been updated
            # This will automatically handle the GUI updates through the callback
            table_row._notify_update()

    def _on_checkbox_changed_simple(self):
        """Simplified checkbox handler using TableRow."""
        sender_checkbox = self.sender()
        if not isinstance(sender_checkbox, QCheckBox):
            return
        
        # Get the TableRow from the checkbox property
        table_row = sender_checkbox.property("table_row")
        if not table_row:
            return
        
        # Update the TableRow's selection state
        # This will automatically trigger the _on_table_row_updated callback
        table_row.is_selected = sender_checkbox.isChecked()
    
    def _on_table_row_updated(self, table_row: 'TableRow'):
        """Handle updates from TableRow objects - update the visual row without relying on indices."""
        # Find the current visual row for this table_row
        visual_row = self.find_visual_row_for_table_row(table_row)
        if visual_row is not None:
            # Temporarily disable sorting to prevent row reordering during update
            was_sorting_enabled = self.file_table.isSortingEnabled()
            if was_sorting_enabled:
                self.file_table.setSortingEnabled(False)
            
            # Update checkbox sort data
            checkbox_item = self.file_table.item(visual_row, 0)
            if checkbox_item:
                sort_value = 1 if table_row.is_selected else 0
                checkbox_item.setData(Qt.ItemDataRole.UserRole, sort_value)
                checkbox_item.setText(str(sort_value))
            
            # Update date columns to reflect any changes
            self.update_date_columns_for_row(visual_row)
            
            # Re-enable sorting if it was enabled
            if was_sorting_enabled:
                self.file_table.setSortingEnabled(True)
                
                # Find the new visual row after sorting (might have changed)
                new_visual_row = self.find_visual_row_for_table_row(table_row)
                if new_visual_row is not None:
                    # Update row appearance at the new position
                    self.update_row_appearance(new_visual_row)
                else:
                    # Fallback: update all row appearances
                    self._update_all_row_appearances()
            else:
                # Update row appearance at current position
                self.update_row_appearance(visual_row)
            
            # Update status bar
            self.update_status_bar()
            
            # Force repaint to ensure changes are visible
            self.file_table.viewport().repaint()
    
    def _on_table_selection_changed(self):
        """Handle table row selection changes."""
        # Update appearance of all rows based on selection
        for row in range(self.file_table.rowCount()):
            self.update_row_appearance(row)
        self.file_table.viewport().repaint()
    
    def update_date_columns_for_row(self, visual_row: int):
        """Update the DateTimeOriginal and DateCreated columns for a specific visual row."""
        table_row = self.get_table_row_for_visual_row(visual_row)
        if not table_row:
            return
        
        
        # Update DateTimeOriginal column (column 3)
        datetime_original_item = self.file_table.item(visual_row, 3)
        if datetime_original_item:
            update_enabled = self.update_datetime_original_cb.isChecked()
            display_text = table_row.get_datetime_original_for_update(update_enabled)
            timestamp = table_row.get_datetime_original_timestamp_for_update(update_enabled)
            
            datetime_original_item.setText(display_text)
            datetime_original_item.setData(Qt.ItemDataRole.UserRole, timestamp)
        
        # Update DateCreated column (column 4)
        date_created_item = self.file_table.item(visual_row, 4)
        if date_created_item:
            update_enabled = self.update_date_created_cb.isChecked()
            display_text = table_row.get_date_created_for_update(update_enabled)
            timestamp = table_row.get_date_created_timestamp_for_update(update_enabled)
            
            date_created_item.setText(display_text)
            date_created_item.setData(Qt.ItemDataRole.UserRole, timestamp)
        
        # Update row appearance to reflect any highlighting changes
        self.update_row_appearance(visual_row)

    def get_table_row_for_visual_row(self, visual_row: int) -> Optional['TableRow']:
        """Get the TableRow object for a given visual row in the table."""
        if visual_row >= self.file_table.rowCount():
            return None
        
        # Get the checkbox widget from the visual row
        cell_widget = self.file_table.cellWidget(visual_row, 0)
        if cell_widget:
            checkbox_layout = cell_widget.layout()
            if checkbox_layout and checkbox_layout.count() > 0:
                layout_item = checkbox_layout.itemAt(0)
                if layout_item:
                    checkbox = layout_item.widget()
                    if isinstance(checkbox, QCheckBox):
                        return checkbox.property("table_row")
        return None
    
    def find_visual_row_for_table_row(self, target_table_row: 'TableRow') -> Optional[int]:
        """Find the current visual row index for a specific TableRow object."""
        for row_idx in range(self.file_table.rowCount()):
            table_row = self.get_table_row_for_visual_row(row_idx)
            if table_row is target_table_row:
                return row_idx
        return None
    
    def update_row_appearance(self, row: int):
        """Update the appearance of a table row based on its checkbox state and output tag selections."""
        # Skip appearance updates during table population to avoid interfering with content display
        if not self.file_table.isSortingEnabled():
            return
        
        # Get the TableRow object for this visual row
        table_row = self.get_table_row_for_visual_row(row)
        if not table_row:
            return
        
        is_checked = table_row.is_selected
        
        # Set colors based on checkbox state and content
        palette = self.palette()
        default_text = palette.color(QPalette.ColorRole.Text)
        disabled_color = palette.color(QPalette.ColorRole.PlaceholderText)
        default_bg = palette.color(QPalette.ColorRole.Base)
        red_color = QColor(220, 20, 20) if not self._is_dark_theme() else QColor(255, 100, 100)
        
        for col in range(self.file_table.columnCount()):
            item = self.file_table.item(row, col)
            if item:
                # Reset background to default
                item.setBackground(default_bg)
                
                # Determine text color based on row selection and column content
                if not is_checked:
                    # Grey out non-selected files, but still make them visible
                    item.setForeground(disabled_color)
                else:
                    # For checked files, determine color based on content and checkbox states
                    should_be_red = False
                    
                    if col == 3:  # DateTimeOriginal column
                        should_be_red = table_row.should_highlight_datetime_original(
                            self.update_datetime_original_cb.isChecked()
                        )
                    elif col == 4:  # DateCreated column
                        should_be_red = table_row.should_highlight_date_created(
                            self.update_date_created_cb.isChecked()
                        )
                    
                    # Apply the appropriate color
                    if should_be_red:
                        item.setForeground(red_color)
                    else:
                        item.setForeground(default_text)
    
    def _is_dark_theme(self) -> bool:
        """Check if the current theme is dark."""
        palette = self.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        # If the window background is darker than middle grey, assume dark theme
        return window_color.lightness() < 128
    
    def update_status_bar(self):
        """Update the status bar with current view information."""
        if not self.table_rows:
            self.status_bar.showMessage("Ready - Drop a folder here or use the Select Folder button")
            return
            
        # Get the current filtered row list
        rows_to_show = self.get_filtered_rows()
        filtered_count = len(rows_to_show)
        total_files = len(self.table_rows)
        
        # Count selected files (from the current filtered view)
        selected_count = sum(1 for row in rows_to_show if row.is_selected)
        
        # Build status message based on current filters
        video_filter_text = " (Images Only)" if self.ignore_video_files_cb.isChecked() else ""
        
        if self.show_all_files_cb.isChecked():
            updatable_count = sum(1 for row in rows_to_show if row.can_be_updated)
            self.status_bar.showMessage(f"Showing {filtered_count} of {total_files} files{video_filter_text}, {updatable_count} can be updated, {selected_count} selected")
        else:
            self.status_bar.showMessage(f"Showing {filtered_count} files with missing dates{video_filter_text} (total analyzed: {total_files}), {selected_count} selected")
    
    def populate_file_table(self):
        """Populate the file table with analysis results."""
        rows_to_show = self.get_filtered_rows()
        
        # Update group box title based on current filters
        if self.show_all_files_cb.isChecked():
            if self.ignore_video_files_cb.isChecked():
                self.table_group.setTitle("All Analyzed Files (Images Only)")
            else:
                self.table_group.setTitle("All Analyzed Files")
        else:
            if self.ignore_video_files_cb.isChecked():
                self.table_group.setTitle("Files with Missing EXIF Dates (Images Only)")
            else:
                self.table_group.setTitle("Files with Missing EXIF Dates")
        
        self.file_table.setRowCount(len(rows_to_show))
        
        # Temporarily disable sorting while populating the table
        self.file_table.setSortingEnabled(False)
        
        for row, table_row in enumerate(rows_to_show):
            # Get a fresh checkbox from the TableRow
            update_checkbox = table_row.checkbox
            
            # Connect the checkbox signal for this new checkbox
            update_checkbox.stateChanged.connect(self._on_checkbox_changed_simple)
            
            # Center the checkbox in the cell
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(update_checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.file_table.setCellWidget(row, 0, checkbox_widget)
            
            # Add hidden item with sort data for the checkbox column
            checkbox_item = QTableWidgetItem()
            # Use numeric values for reliable sorting: 1 for checked, 0 for unchecked
            sort_value = 1 if update_checkbox.isChecked() else 0
            checkbox_item.setData(Qt.ItemDataRole.UserRole, sort_value)
            checkbox_item.setText(str(sort_value))  # Set text to numeric value for sorting
            self.file_table.setItem(row, 0, checkbox_item)
            
            # Use TableRow properties for easier access to data
            file = table_row.media_file
            
            # Filename
            filename_item = QTableWidgetItem(table_row.filename)
            filename_item.setToolTip(str(file.path))
            self.file_table.setItem(row, 1, filename_item)
            
            # File Type - show the file extension
            type_item = QTableWidgetItem(table_row.file_type)
            type_item.setToolTip(f"File extension: {file.extension}")
            self.file_table.setItem(row, 2, type_item)
            
            # DateTimeOriginal column (shifted to index 3)
            datetime_original_item = QTableWidgetItem()
            update_enabled = self.update_datetime_original_cb.isChecked()
            display_text = table_row.get_datetime_original_for_update(update_enabled)
            timestamp = table_row.get_datetime_original_timestamp_for_update(update_enabled)
            
            datetime_original_item.setText(display_text)
            datetime_original_item.setData(Qt.ItemDataRole.UserRole, timestamp)
            self.file_table.setItem(row, 3, datetime_original_item)
            
            # DateCreated column
            date_created_item = QTableWidgetItem()
            update_enabled = self.update_date_created_cb.isChecked()
            display_text = table_row.get_date_created_for_update(update_enabled)
            timestamp = table_row.get_date_created_timestamp_for_update(update_enabled)
            
            date_created_item.setText(display_text)
            date_created_item.setData(Qt.ItemDataRole.UserRole, timestamp)
            self.file_table.setItem(row, 4, date_created_item)
            
            # Source dropdown
            if table_row.can_be_updated:
                source_combo = NoScrollComboBox()
                source_combo.setToolTip("Select the date source to use for this file")
                
                # Add all available sources to the dropdown
                if table_row.has_available_sources:
                    current_source_index = 0
                    for idx, (date, source_name) in enumerate(file.available_sources):
                        date_str_combo = date.strftime("%Y-%m-%d %H:%M:%S")
                        display_text = f"{source_name} ({date_str_combo})"
                        source_combo.addItem(display_text, (date, source_name))
                        
                        # Set current selection to the originally suggested source
                        if hasattr(file, 'source') and source_name == file.source:
                            current_source_index = idx
                    
                    # Add manual option at the end
                    source_combo.addItem("Manual...", ("manual", "Manual"))
                    source_combo.setCurrentIndex(current_source_index)
                else:
                    # Fallback if no available_sources but has suggested_date
                    source = table_row.source_name
                    source_combo.addItem(source, (file.suggested_date, source))
                    source_combo.addItem("Manual...", ("manual", "Manual"))
                
                # Store reference in TableRow
                table_row.source_combo = source_combo
                
                # Connect the combo box change event - use TableRow object to avoid row index issues after sorting
                source_combo.currentIndexChanged.connect(
                    lambda index, table_row=table_row: self.on_source_changed_by_table_row(table_row, index)
                )
                
                self.file_table.setCellWidget(row, 5, source_combo)
                
                # Add hidden item for sorting by source name
                source_sort_item = QTableWidgetItem(table_row.source_name)
                source_sort_item.setData(Qt.ItemDataRole.UserRole, table_row.source_name)
                self.file_table.setItem(row, 5, source_sort_item)
            else:
                # Source dropdown for files without any date options - still allow manual entry
                source_combo = NoScrollComboBox()
                source_combo.addItem("Manual...", ("manual", "Manual"))
                source_combo.setToolTip("Manually enter a date and time for this file")
                
                # Store reference in TableRow
                table_row.source_combo = source_combo
                
                # Connect the combo box change event - use TableRow object to avoid row index issues after sorting
                source_combo.currentIndexChanged.connect(
                    lambda index, table_row=table_row: self.on_source_changed_by_table_row(table_row, index)
                )
                
                self.file_table.setCellWidget(row, 5, source_combo)
                
                # Add hidden item for sorting (empty sources sort to bottom)
                empty_source_item = QTableWidgetItem("Manual")
                empty_source_item.setData(Qt.ItemDataRole.UserRole, "Manual")
                self.file_table.setItem(row, 5, empty_source_item)
            
            # File size
            size_item = NumericTableWidgetItem(table_row.file_size_display, table_row.file_size)
            size_item.setData(Qt.ItemDataRole.UserRole, table_row.file_size)
            self.file_table.setItem(row, 6, size_item)
        
        # Re-enable sorting after table population is complete
        self.file_table.setSortingEnabled(True)
        
        # Now that sorting is enabled, update row appearances
        for row in range(self.file_table.rowCount()):
            self.update_row_appearance(row)
        
        # Update status bar immediately
        self.update_status_bar()
    
    def _update_all_row_appearances(self):
        """Update the appearance of all rows after table population is complete."""
        for row in range(self.file_table.rowCount()):
            self.update_row_appearance(row)
        # Force immediate GUI rendering
        self.file_table.viewport().repaint()
    
    def dry_run_update(self):
        """Start dry run update."""
        self.start_update(dry_run=True)
    
    def update_files(self):
        """Start actual file update."""
        # Confirm with user
        reply = QMessageBox.question(
            self, "Confirm Update",
            "Are you sure you want to update EXIF data in the selected files?\n\n"
            "This operation will modify your files. "
            + ("Backup copies will be created." if self.create_backup_cb.isChecked() else "No backups will be created."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.start_update(dry_run=False)
    
    def update_all_checkbox_states(self):
        """Update all visible checkbox states to match their TableRow is_selected values."""
        for row_idx in range(self.file_table.rowCount()):
            table_row = self.get_table_row_for_visual_row(row_idx)
            if table_row:
                cell_widget = self.file_table.cellWidget(row_idx, 0)
                if cell_widget:
                    checkbox_layout = cell_widget.layout()
                    if checkbox_layout and checkbox_layout.count() > 0:
                        layout_item = checkbox_layout.itemAt(0)
                        if layout_item:
                            checkbox = layout_item.widget()
                            if isinstance(checkbox, QCheckBox):
                                # Update checkbox state without triggering signals
                                checkbox.blockSignals(True)
                                checkbox.setChecked(table_row.is_selected)
                                checkbox.blockSignals(False)
                                
                                # Update the sort data for the checkbox column
                                checkbox_item = self.file_table.item(row_idx, 0)
                                if checkbox_item:
                                    sort_value = 1 if table_row.is_selected else 0
                                    checkbox_item.setData(Qt.ItemDataRole.UserRole, sort_value)
                                    checkbox_item.setText(str(sort_value))
        
        # Update row appearances, date columns, and status bar
        for row in range(self.file_table.rowCount()):
            self.update_row_appearance(row)
            self.update_date_columns_for_row(row)
        self.update_status_bar()
        self.file_table.viewport().repaint()

    def select_all_files(self):
        """Select all files that can be updated."""
        rows_to_show = self.get_filtered_rows()
        # Temporarily disable callbacks to avoid multiple updates
        for row in rows_to_show:
            if row.can_be_updated:
                row._is_selected = True  # Set directly to avoid triggering callback
        # Update all at once
        self.update_all_checkbox_states()
    
    def select_no_files(self):
        """Deselect all files."""
        rows_to_show = self.get_filtered_rows()
        # Temporarily disable callbacks to avoid multiple updates
        for row in rows_to_show:
            row._is_selected = False  # Set directly to avoid triggering callback
        # Update all at once
        self.update_all_checkbox_states()
    
    def toggle_selected_rows(self):
        """Toggle checkboxes for currently selected table rows."""
        selected_indexes = self.file_table.selectionModel().selectedRows()
        
        for index in selected_indexes:
            row = index.row()
            table_row = self.get_table_row_for_visual_row(row)
            if table_row:
                table_row.is_selected = not table_row.is_selected
        # Note: Individual callbacks will handle updates for each toggled row
    
    def get_selected_files(self):
        """Get list of files selected for update."""
        selected_files = []
        rows_to_show = self.get_filtered_rows()
        
        for row in rows_to_show:
            if row.is_selected:
                selected_files.append(row.media_file)
        
        return selected_files
    
    def start_update(self, dry_run: bool = False):
        """Start update process in worker thread."""
        # Sync all dropdown selections to MediaFile objects
        self.sync_dropdown_selections()
        
        # Get only the selected files
        files_to_update = self.get_selected_files()
        
        # Filter to only files that have date suggestions (after dropdown sync)
        files_to_update = [f for f in files_to_update if f.suggested_date]
        
        if not files_to_update:
            QMessageBox.information(self, "No Updates", "No files are selected for update or have date suggestions.")
            return
        
        self.log(f"Starting {'dry run' if dry_run else 'update'} for {len(files_to_update)} selected files...")
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # Start worker thread
        self.update_worker = UpdateWorker(
            files_to_update,
            self.update_datetime_original_cb.isChecked(),
            self.update_date_created_cb.isChecked(),
            self.create_backup_cb.isChecked(),
            dry_run
        )
        self.update_worker.progress.connect(self.log)
        self.update_worker.finished.connect(self.on_update_finished)
        self.update_worker.error.connect(self.on_update_error)
        self.update_worker.start()
    
    def sync_dropdown_selections(self):
        """Sync all dropdown selections back to MediaFile objects using the new approach."""
        rows_to_show = self.get_filtered_rows()
        
        for row_index, table_row in enumerate(rows_to_show):
            combo = table_row.source_combo
            if combo and combo.currentIndex() >= 0:
                table_row.sync_from_combo_selection(combo.currentIndex())
    
    def on_update_finished(self, successful: int, failed: int):
        """Handle update completion."""
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        self.log(f"Update complete! Successful: {successful}, Failed: {failed}")
        
        if successful > 0:
            QMessageBox.information(
                self, "Update Complete",
                f"Successfully updated {successful} files.\n"
                + (f"{failed} files failed to update." if failed > 0 else "")
            )
        elif failed > 0:
            QMessageBox.warning(
                self, "Update Failed",
                f"Failed to update {failed} files. Check the log for details."
            )
    
    def on_update_error(self, error_msg: str):
        """Handle update error."""
        self.log(f"Update error: {error_msg}")
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Update Error", f"Failed to update files:\n{error_msg}")
    
    def set_ui_enabled(self, enabled: bool):
        """Enable/disable UI controls."""
        self.select_folder_btn.setEnabled(enabled)
        self.analyze_btn.setEnabled(enabled and self.folder_path is not None)
        self.dry_run_btn.setEnabled(enabled and bool(self.media_files))
        self.update_btn.setEnabled(enabled and bool(self.media_files))
        
        # Enable/disable selection buttons
        self.select_all_btn.setEnabled(enabled and bool(self.media_files))
        self.select_none_btn.setEnabled(enabled and bool(self.media_files))
        self.select_rows_btn.setEnabled(enabled and bool(self.media_files))
    
    def log(self, message: str):
        """Add message to log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            # Check if any of the URLs are directories
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = Path(url.toLocalFile())
                    if file_path.is_dir():
                        event.acceptProposedAction()
                        # Provide visual feedback
                        self.setStyleSheet("QMainWindow { border: 3px dashed #4CAF50; }")
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Remove visual feedback
        self.setStyleSheet("")
        event.accept()
    
    def dropEvent(self, event):
        """Handle drop event."""
        # Remove visual feedback
        self.setStyleSheet("")
        
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = Path(url.toLocalFile())
                    if file_path.is_dir():
                        # Set the dropped folder as the selected folder
                        self.folder_path = file_path
                        self.folder_label.setText(str(self.folder_path))
                        self.folder_label.setStyleSheet("")  # Clear custom styling to use theme default
                        self.analyze_btn.setEnabled(True)
                        self.log(f"Folder dropped: {self.folder_path}")
                        event.acceptProposedAction()
                        return
        event.ignore()


def run_gui():
    """Run the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("EXIF Date Updater")
    app.setApplicationVersion("1.0")
    
    # Set application icon for taskbar/system tray
    try:
        icons_dir = Path(__file__).parent / "resources" / "icons"
        icon = QIcon()
        icon_128_path = icons_dir / "logo_128.png"
        icon_256_path = icons_dir / "logo_256.png"
        
        if icon_128_path.exists():
            icon.addFile(str(icon_128_path))
        if icon_256_path.exists():
            icon.addFile(str(icon_256_path))
            
        if not icon.isNull():
            app.setWindowIcon(icon)
    except Exception as e:
        print(f"Error setting application icon: {e}")
    
    window = ExifDateUpdaterGUI()
    window.show()
    
    sys.exit(app.exec())
