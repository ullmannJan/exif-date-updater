"""
GUI interface for the EXIF Date Updater using PySide6.
"""

import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QTextCursor, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QTextEdit, QProgressBar, QCheckBox, QGroupBox, QMessageBox,
    QSplitter, QHeaderView, QStatusBar, QComboBox
)

from .exif_analyzer import ExifAnalyzer, MediaFile
from .exif_updater import ExifUpdater


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events to prevent interfering with table scrolling."""
    
    def wheelEvent(self, event):
        """Ignore wheel events to allow table scrolling."""
        event.ignore()


class AnalysisWorker(QThread):
    """Worker thread for analyzing media files."""
    
    progress = Signal(str)  # Progress message
    finished = Signal(list)  # List of MediaFile objects
    error = Signal(str)  # Error message
    
    def __init__(self, folder_path: Path):
        super().__init__()
        self.folder_path = folder_path
        self.analyzer = ExifAnalyzer()
    
    def run(self):
        try:
            self.progress.emit("Starting analysis...")
            media_files = self.analyzer.analyze_folder(self.folder_path)
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
            
            successful, failed = self.updater.update_multiple_files(
                self.media_files,
                self.update_datetime_original,
                self.update_date_created,
                self.dry_run
            )
            
            self.finished.emit(successful, failed)
        except Exception as e:
            self.error.emit(str(e))


class ExifDateUpdaterGUI(QMainWindow):
    """Main GUI application for EXIF Date Updater."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EXIF Date Updater")
        self.setGeometry(100, 100, 1200, 800)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Data
        self.folder_path: Optional[Path] = None
        self.media_files: List[MediaFile] = []
        self.analyzer = ExifAnalyzer()
        
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
        self.progress_bar = QProgressBar()
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
        self.show_all_files_cb.setChecked(False)
        table_options_layout.addWidget(self.show_all_files_cb)
        
        # Add select all/none buttons
        self.select_all_btn = QPushButton("Select All")
        self.select_none_btn = QPushButton("Select None")
        self.select_missing_btn = QPushButton("Select Reliable Sources")
        
        self.select_all_btn.setToolTip("Select all files that can be updated")
        self.select_none_btn.setToolTip("Deselect all files")
        self.select_missing_btn.setToolTip("Select only files with reliable date sources (EXIF, video metadata, filename dates)")
        
        table_options_layout.addStretch()
        table_options_layout.addWidget(QLabel("Selection:"))
        table_options_layout.addWidget(self.select_all_btn)
        table_options_layout.addWidget(self.select_none_btn)
        table_options_layout.addWidget(self.select_missing_btn)
        
        table_layout.addLayout(table_options_layout)
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(7)
        self.file_table.setHorizontalHeaderLabels([
            "Update", "Filename", "DateTimeOriginal", "DateTime/DateCreated", "Suggested Date", "Source", "Size"
        ])
        
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
                    item.setToolTip("Current DateTimeOriginal EXIF value (empty if missing)")
                elif col == 3:
                    item.setToolTip("Current DateTime/DateCreated EXIF value (empty if missing)")
                elif col == 4:
                    item.setToolTip("Suggested date based on selected source")
                elif col == 5:
                    item.setToolTip("Select date source from available options")
                elif col == 6:
                    item.setToolTip("File size in bytes")
        
        # Make table responsive
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Update checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Filename
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # DateTimeOriginal
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # DateTime/DateCreated
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Suggested Date
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
        self.update_date_created_cb = QCheckBox("Update DateTime/DateCreated")
        self.update_date_created_cb.setChecked(True)
        self.create_backup_cb = QCheckBox("Create backup files")
        self.create_backup_cb.setChecked(True)
        
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
        
        # Selection buttons
        self.select_all_btn.clicked.connect(self.select_all_files)
        self.select_none_btn.clicked.connect(self.select_no_files)
        self.select_missing_btn.clicked.connect(self.select_high_confidence)
    
    def select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder containing media files"
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
        self.set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start worker thread
        self.analysis_worker = AnalysisWorker(self.folder_path)
        self.analysis_worker.progress.connect(self.log)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.error.connect(self.on_analysis_error)
        self.analysis_worker.start()
    
    def on_analysis_finished(self, media_files: List[MediaFile]):
        """Handle analysis completion."""
        self.media_files = media_files
        self.populate_file_table()
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        # Show summary
        missing_files = [f for f in media_files if f.missing_dates]
        self.log(f"Analysis complete! Found {len(missing_files)} files with missing dates.")
        
        if missing_files:
            self.dry_run_btn.setEnabled(True)
            self.update_btn.setEnabled(True)
        
        self.update_status_bar()
    
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
    
    def on_source_changed(self, row: int, combo_index: int):
        """Handle source selection change in dropdown."""
        combo = self.file_table.cellWidget(row, 5)  # Source column is now index 5
        if isinstance(combo, (QComboBox, NoScrollComboBox)) and combo_index >= 0:
            # Get the selected source data
            date, source_name = combo.itemData(combo_index)
            
            # Update the suggested date column
            date_str = date.strftime("%Y-%m-%d %H:%M:%S")
            date_item = self.file_table.item(row, 4)  # Suggested date column is now index 4
            if date_item:
                date_item.setText(date_str)
            
            # Update the MediaFile object if needed
            if hasattr(self, 'media_files') and row < len(self.media_files):
                # Find the corresponding file (accounting for filtering)
                if self.show_all_files_cb.isChecked():
                    files_to_show = self.media_files
                else:
                    files_to_show = [f for f in self.media_files if f.missing_dates]
                
                if row < len(files_to_show):
                    file = files_to_show[row]
                    file.suggested_date = date
                    file.source = source_name
    
    def on_checkbox_changed(self):
        """Handle checkbox state change to update status bar."""
        self.update_status_bar()
    
    def update_status_bar(self):
        """Update the status bar with current view information."""
        if not self.media_files:
            self.status_bar.showMessage("Ready - Drop a folder here or use the Select Folder button")
            return
            
        missing_files = [f for f in self.media_files if f.missing_dates]
        total_files = len(self.media_files)
        missing_count = len(missing_files)
        
        # Count selected files
        selected_files = self.get_selected_files()
        selected_count = len(selected_files)
        
        if self.show_all_files_cb.isChecked():
            self.status_bar.showMessage(f"Showing all {total_files} files, {missing_count} need updates, {selected_count} selected")
        else:
            self.status_bar.showMessage(f"Showing {missing_count} files with missing dates (total analyzed: {total_files}), {selected_count} selected")
    
    def populate_file_table(self):
        """Populate the file table with analysis results."""
        if self.show_all_files_cb.isChecked():
            # Show all files
            files_to_show = self.media_files
            # Update group box title
            self.table_group.setTitle("All Analyzed Files")
        else:
            # Show only files with missing dates
            files_to_show = [f for f in self.media_files if f.missing_dates]
            # Update group box title
            self.table_group.setTitle("Files with Missing EXIF Dates")
        
        self.file_table.setRowCount(len(files_to_show))
        
        for row, file in enumerate(files_to_show):
            # Update checkbox - only enable for files with missing dates and suggestions
            update_checkbox = QCheckBox()
            if file.missing_dates and file.suggested_date:
                update_checkbox.setChecked(True)  # Default to checked for files that can be updated
                update_checkbox.setToolTip("Check to include this file in the update")
            else:
                update_checkbox.setChecked(False)
                update_checkbox.setEnabled(False)
                if not file.missing_dates:
                    update_checkbox.setToolTip("File has complete EXIF data")
                else:
                    update_checkbox.setToolTip("No date suggestion available")
            
            # Center the checkbox in the cell
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(update_checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.file_table.setCellWidget(row, 0, checkbox_widget)
            
            # Store reference to checkbox for easy access
            update_checkbox.setProperty("file_row", row)
            update_checkbox.stateChanged.connect(self.on_checkbox_changed)
            
            # Filename
            filename_item = QTableWidgetItem(file.name)
            filename_item.setToolTip(str(file.path))
            self.file_table.setItem(row, 1, filename_item)
            
            # DateTimeOriginal column
            datetime_original_item = QTableWidgetItem()
            if file.datetime_original:
                datetime_original_item.setText(file.datetime_original.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                datetime_original_item.setText("")
                if 'DateTimeOriginal' in file.missing_dates:
                    # Highlight missing values with light red background
                    datetime_original_item.setBackground(QColor(255, 220, 220))  # Light red
            self.file_table.setItem(row, 2, datetime_original_item)
            
            # DateTime/DateCreated column
            datetime_created_item = QTableWidgetItem()
            if file.date_created:
                datetime_created_item.setText(file.date_created.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                datetime_created_item.setText("")
                if 'DateTime' in file.missing_dates:
                    # Highlight missing values with light red background
                    datetime_created_item.setBackground(QColor(255, 220, 220))  # Light red
            self.file_table.setItem(row, 3, datetime_created_item)
            
            # Suggested date
            if file.suggested_date:
                date_str = file.suggested_date.strftime("%Y-%m-%d %H:%M:%S")
                self.file_table.setItem(row, 4, QTableWidgetItem(date_str))
                
                # Source dropdown
                source_combo = NoScrollComboBox()
                source_combo.setToolTip("Select the date source to use for this file")
                
                # Add all available sources to the dropdown
                if hasattr(file, 'available_sources') and file.available_sources:
                    current_source_index = 0
                    for idx, (date, source_name) in enumerate(file.available_sources):
                        date_str_combo = date.strftime("%Y-%m-%d %H:%M:%S")
                        display_text = f"{source_name} ({date_str_combo})"
                        source_combo.addItem(display_text, (date, source_name))
                        
                        # Set current selection to the originally suggested source
                        if source_name == file.source:
                            current_source_index = idx
                    
                    source_combo.setCurrentIndex(current_source_index)
                    
                    # Connect the combo box change event
                    source_combo.currentIndexChanged.connect(
                        lambda index, r=row: self.on_source_changed(r, index)
                    )
                else:
                    # Fallback if no available_sources
                    source = getattr(file, 'source', 'Unknown')
                    source_combo.addItem(source, (file.suggested_date, source))
                
                self.file_table.setCellWidget(row, 5, source_combo)
            else:
                self.file_table.setItem(row, 4, QTableWidgetItem("No suggestion" if file.missing_dates else "Not needed"))
                
                # Empty source dropdown for files without suggestions
                source_combo = NoScrollComboBox()
                source_combo.setEnabled(False)
                source_combo.addItem("-")
                self.file_table.setCellWidget(row, 5, source_combo)
            
            # File size
            size_str = f"{file.size:,} bytes"
            self.file_table.setItem(row, 6, QTableWidgetItem(size_str))
    
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
    
    def select_all_files(self):
        """Select all files that can be updated."""
        for row in range(self.file_table.rowCount()):
            checkbox_widget = self.file_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isEnabled():
                    checkbox.setChecked(True)
        self.update_status_bar()
    
    def select_no_files(self):
        """Deselect all files."""
        for row in range(self.file_table.rowCount()):
            checkbox_widget = self.file_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        self.update_status_bar()
    
    def select_high_confidence(self):
        """Select all files with reliable date sources."""
        # Get the current files being displayed
        if self.show_all_files_cb.isChecked():
            files_to_show = self.media_files
        else:
            files_to_show = [f for f in self.media_files if f.missing_dates]
        
        reliable_sources = {'EXIF DateTimeOriginal', 'EXIF DateTime', 'EXIF DateTimeDigitized', 'Video Creation Date', 'Filename Date'}
        
        for row in range(self.file_table.rowCount()):
            checkbox_widget = self.file_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isEnabled() and row < len(files_to_show):
                    file = files_to_show[row]
                    # Only select files with reliable sources
                    if file.source and file.source in reliable_sources:
                        checkbox.setChecked(True)
                    else:
                        checkbox.setChecked(False)
        self.update_status_bar()
    
    def get_selected_files(self):
        """Get list of files selected for update."""
        selected_files = []
        
        # Get the current files being displayed
        if self.show_all_files_cb.isChecked():
            files_to_show = self.media_files
        else:
            files_to_show = [f for f in self.media_files if f.missing_dates]
        
        for row in range(self.file_table.rowCount()):
            if row < len(files_to_show):
                checkbox_widget = self.file_table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected_files.append(files_to_show[row])
        
        return selected_files
    
    def start_update(self, dry_run: bool = False):
        """Start update process in worker thread."""
        # Sync all dropdown selections to MediaFile objects
        self.sync_dropdown_selections()
        
        # Get only the selected files
        files_to_update = self.get_selected_files()
        
        # Filter to only files that have suggestions
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
        """Sync all dropdown selections back to MediaFile objects."""
        # Get the current files being displayed
        if self.show_all_files_cb.isChecked():
            files_to_show = self.media_files
        else:
            files_to_show = [f for f in self.media_files if f.missing_dates]
        
        # Update each file based on its dropdown selection
        for row in range(self.file_table.rowCount()):
            combo = self.file_table.cellWidget(row, 5)  # Source column is now index 5
            if isinstance(combo, (QComboBox, NoScrollComboBox)) and combo.currentIndex() >= 0 and row < len(files_to_show):
                # Get the selected source data
                date, source_name = combo.itemData(combo.currentIndex())
                
                # Update the MediaFile object
                file = files_to_show[row]
                file.suggested_date = date
                file.source = source_name
    
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
        self.select_missing_btn.setEnabled(enabled and bool(self.media_files))
    
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
    
    window = ExifDateUpdaterGUI()
    window.show()
    
    sys.exit(app.exec())
