"""Installation verification test."""

import unittest
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


class TestInstallation(unittest.TestCase):
    """Test that all modules can be imported correctly."""
    
    def test_import_analyzer(self):
        """Test importing ExifAnalyzer."""
        try:
            from exif_date_updater import ExifAnalyzer
            analyzer = ExifAnalyzer()
            self.assertIsNotNone(analyzer)
        except ImportError as e:
            self.fail(f"Failed to import ExifAnalyzer: {e}")
    
    def test_import_updater(self):
        """Test importing ExifUpdater."""
        try:
            from exif_date_updater import ExifUpdater
            updater = ExifUpdater()
            self.assertIsNotNone(updater)
        except ImportError as e:
            self.fail(f"Failed to import ExifUpdater: {e}")
    
    def test_import_cli(self):
        """Test importing CLI module."""
        try:
            from exif_date_updater.cli import main
            self.assertIsNotNone(main)
        except ImportError as e:
            self.fail(f"Failed to import CLI module: {e}")
    
    def test_import_gui(self):
        """Test importing GUI module."""
        try:
            from exif_date_updater.gui import run_gui
            self.assertIsNotNone(run_gui)
        except ImportError as e:
            # GUI might not be available in all environments
            print(f"Warning: GUI not available: {e}")
    
    def test_required_dependencies(self):
        """Test that required dependencies are available."""
        required_modules = [
            'PIL',      # Pillow
            'exifread', # exifread
            'piexif',   # piexif
        ]
        
        for module_name in required_modules:
            with self.subTest(module=module_name):
                try:
                    __import__(module_name)
                except ImportError as e:
                    self.fail(f"Required dependency {module_name} not available: {e}")
    
    def test_package_structure(self):
        """Test that the package structure is correct."""
        try:
            import exif_date_updater
            self.assertTrue(hasattr(exif_date_updater, 'ExifAnalyzer'))
            self.assertTrue(hasattr(exif_date_updater, 'ExifUpdater'))
            self.assertTrue(hasattr(exif_date_updater, '__version__'))
        except ImportError as e:
            self.fail(f"Package structure is incorrect: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
