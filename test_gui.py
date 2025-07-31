#!/usr/bin/env python3
"""Simple test script to debug GUI table population issues."""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.exif_date_updater.gui import run_gui
    print("GUI module imported successfully")
    
    # Try to run the GUI
    run_gui()
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Runtime error: {e}")
    import traceback
    traceback.print_exc()
