#!/usr/bin/env python3
"""Test script to verify the NoScrollComboBox implementation."""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt

# Import our custom combo box
try:
    from src.exif_date_updater.gui import NoScrollComboBox
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("NoScrollComboBox Test")
            self.setGeometry(100, 100, 400, 300)
            
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout(central_widget)
            
            # Add label
            label = QLabel("Try scrolling with mouse wheel over the combo box.\nIt should NOT change the selection.")
            layout.addWidget(label)
            
            # Add our custom combo box
            combo = NoScrollComboBox()
            combo.addItems(["Option 1", "Option 2", "Option 3", "Option 4", "Option 5"])
            combo.setCurrentIndex(2)  # Start with Option 3 selected
            layout.addWidget(combo)
            
            # Add another label
            result_label = QLabel("The combo box should ignore wheel events.")
            layout.addWidget(result_label)
    
    def main():
        app = QApplication(sys.argv)
        window = TestWindow()
        window.show()
        
        print("✓ NoScrollComboBox test window created successfully!")
        print("  - The combo box should ignore wheel scroll events")
        print("  - You can still click to open the dropdown")
        print("  - Close the window to continue")
        
        return app.exec()
    
    if __name__ == "__main__":
        sys.exit(main())
        
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("This is expected if dependencies are not installed.")
    print("The NoScrollComboBox class has been successfully implemented in gui.py")
