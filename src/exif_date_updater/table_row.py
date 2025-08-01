"""
Table row data structure for the EXIF Date Updater GUI.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from PySide6.QtWidgets import QCheckBox, QComboBox
from .exif_analyzer import MediaFile


@dataclass
class TableRow:
    """Represents a single row in the file table with all associated data and widgets."""
    
    # Core data
    media_file: MediaFile
    
    # UI widgets (created on demand)
    _source_combo: Optional[QComboBox] = None
    
    # Cached properties
    _is_selected: bool = False
    
    def __post_init__(self):
        """Initialize derived properties after dataclass creation."""
        # Initially select files that have missing dates and can be updated
        self._is_selected = bool(self.media_file.missing_dates and self.media_file.suggested_date)
    
    @property
    def checkbox(self) -> QCheckBox:
        """Create a new checkbox widget for this row."""
        # Always create a new checkbox to avoid Qt widget lifecycle issues
        checkbox = QCheckBox()
        checkbox.setChecked(self._is_selected)
        checkbox.setToolTip("Check to include this file in the update")
        checkbox.setProperty("table_row", self)
        # Note: Signal connection will be handled by the main GUI class
        return checkbox
    
    @property
    def source_combo(self) -> Optional[QComboBox]:
        """Get the source combo widget for this row (may be None if no sources available)."""
        return self._source_combo
    
    @source_combo.setter
    def source_combo(self, combo: QComboBox):
        """Set the source combo widget for this row."""
        self._source_combo = combo
        if combo:
            combo.setProperty("table_row", self)
    
    @property
    def is_selected(self) -> bool:
        """Check if this row is selected for update."""
        return self._is_selected
    
    @is_selected.setter
    def is_selected(self, selected: bool):
        """Set the selection state of this row."""
        self._is_selected = selected
        # Note: Checkbox state will be updated when the checkbox is created
    
    @property
    def filename(self) -> str:
        """Get the filename for display."""
        return self.media_file.name
    
    @property
    def file_type(self) -> str:
        """Get the file type/extension for display."""
        return self.media_file.extension.lstrip('.').upper()
    
    @property
    def file_size(self) -> int:
        """Get the file size in bytes."""
        return self.media_file.size
    
    @property
    def file_size_display(self) -> str:
        """Get the file size formatted for display."""
        return f"{self.media_file.size:,} bytes"
    
    @property
    def datetime_original_display(self) -> str:
        """Get the DateTimeOriginal value for display."""
        if self.media_file.datetime_original:
            return self.media_file.datetime_original.strftime("%Y-%m-%d %H:%M:%S")
        return ""
    
    @property
    def datetime_original_timestamp(self) -> float:
        """Get the DateTimeOriginal timestamp for sorting (0 if empty)."""
        if self.media_file.datetime_original:
            return self.media_file.datetime_original.timestamp()
        return 0.0
    
    @property
    def date_created_display(self) -> str:
        """Get the DateCreated value for display."""
        if self.media_file.date_created:
            return self.media_file.date_created.strftime("%Y-%m-%d %H:%M:%S")
        return ""
    
    @property
    def date_created_timestamp(self) -> float:
        """Get the DateCreated timestamp for sorting (0 if empty)."""
        if self.media_file.date_created:
            return self.media_file.date_created.timestamp()
        return 0.0
    
    @property
    def source_name(self) -> str:
        """Get the current source name for display and sorting."""
        return getattr(self.media_file, 'source', 'Unknown')
    
    @property
    def has_missing_dates(self) -> bool:
        """Check if this file has missing EXIF dates."""
        return bool(self.media_file.missing_dates)
    
    @property
    def has_suggested_date(self) -> bool:
        """Check if this file has a suggested date available."""
        return bool(self.media_file.suggested_date)
    
    @property
    def has_available_sources(self) -> bool:
        """Check if this file has available date sources."""
        return bool(hasattr(self.media_file, 'available_sources') and self.media_file.available_sources)
    
    @property
    def can_be_updated(self) -> bool:
        """Check if this file can be updated (has sources or suggested date)."""
        return self.has_suggested_date or self.has_available_sources
    
    @property
    def is_video_file(self) -> bool:
        """Check if this is a video file."""
        from .exif_analyzer import ExifAnalyzer
        return self.media_file.extension.lower() in ExifAnalyzer.VIDEO_EXTENSIONS
    
    def get_datetime_original_for_update(self, update_enabled: bool) -> str:
        """Get the DateTimeOriginal display value based on actual file data and selection state."""
        # If file is selected for update and we have a suggested date, show that (will be red if different)
        if self.is_selected and update_enabled and self.media_file.suggested_date:
            return self.media_file.suggested_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Otherwise show actual file data if it exists
        if self.media_file.datetime_original:
            return self.media_file.datetime_original.strftime("%Y-%m-%d %H:%M:%S")
        
        # Otherwise show nothing
        return ""
    
    def get_datetime_original_timestamp_for_update(self, update_enabled: bool) -> float:
        """Get the DateTimeOriginal timestamp for sorting."""
        # If file is selected for update and we have a suggested date, use that for sorting
        if self.is_selected and update_enabled and self.media_file.suggested_date:
            return self.media_file.suggested_date.timestamp()
        
        # Otherwise use actual file data if it exists
        if self.media_file.datetime_original:
            return self.media_file.datetime_original.timestamp()
        
        return 0.0
    
    def get_date_created_for_update(self, update_enabled: bool) -> str:
        """Get the DateCreated display value based on actual file data and selection state."""
        # If file is selected for update and we have a suggested date, show that (will be red if different)
        if self.is_selected and update_enabled and self.media_file.suggested_date:
            return self.media_file.suggested_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Otherwise show actual file data if it exists
        if self.media_file.date_created:
            return self.media_file.date_created.strftime("%Y-%m-%d %H:%M:%S")
        
        # Otherwise show nothing
        return ""
    
    def get_date_created_timestamp_for_update(self, update_enabled: bool) -> float:
        """Get the DateCreated timestamp for sorting."""
        # If file is selected for update and we have a suggested date, use that for sorting
        if self.is_selected and update_enabled and self.media_file.suggested_date:
            return self.media_file.suggested_date.timestamp()
        
        # Otherwise use actual file data if it exists
        if self.media_file.date_created:
            return self.media_file.date_created.timestamp()
        
        return 0.0
    
    def should_highlight_datetime_original(self, update_enabled: bool) -> bool:
        """Determine if DateTimeOriginal column should be highlighted in red."""
        # Only highlight if file is selected for update and we have a suggested date
        if not (self.is_selected and update_enabled and self.media_file.suggested_date):
            return False
        
        # Highlight if no existing data (will write new data)
        if not self.media_file.datetime_original:
            return True
        
        # Highlight if suggested date is different from existing data (will overwrite)
        existing_timestamp = self.media_file.datetime_original.timestamp()
        suggested_timestamp = self.media_file.suggested_date.timestamp()
        # Allow small tolerance for timestamp comparison (1 second)
        return abs(existing_timestamp - suggested_timestamp) > 1.0
    
    def should_highlight_date_created(self, update_enabled: bool) -> bool:
        """Determine if DateCreated column should be highlighted in red."""
        # Only highlight if file is selected for update and we have a suggested date
        if not (self.is_selected and update_enabled and self.media_file.suggested_date):
            return False
        
        # Highlight if no existing data (will write new data)
        if not self.media_file.date_created:
            return True
        
        # Highlight if suggested date is different from existing data (will overwrite)
        existing_timestamp = self.media_file.date_created.timestamp()
        suggested_timestamp = self.media_file.suggested_date.timestamp()
        # Allow small tolerance for timestamp comparison (1 second)
        return abs(existing_timestamp - suggested_timestamp) > 1.0
    
    def sync_from_combo_selection(self, combo_index: int):
        """Update the MediaFile based on the current combo box selection."""
        if self._source_combo and combo_index >= 0:
            date, source_name = self._source_combo.itemData(combo_index)
            if isinstance(date, datetime):
                self.media_file.suggested_date = date
                self.media_file.source = source_name
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"TableRow({self.filename}, selected={self.is_selected}, missing={self.has_missing_dates})"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"TableRow(file={self.media_file.name}, "
                f"selected={self.is_selected}, "
                f"missing_dates={self.has_missing_dates}, "
                f"suggested_date={bool(self.media_file.suggested_date)}, "
                f"source={self.source_name})")
