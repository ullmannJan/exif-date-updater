"""Test runner for all EXIF Date Updater tests."""

import unittest
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def discover_and_run_tests():
    """Discover and run all tests."""
    
    # Discover tests
    loader = unittest.TestLoader()
    start_dir = str(Path(__file__).parent)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test(test_name):
    """Run a specific test module."""
    
    try:
        # Import the specific test module
        if test_name == "analyzer":
            from test_exif_analyzer import TestExifAnalyzer
            suite = unittest.TestLoader().loadTestsFromTestCase(TestExifAnalyzer)
        elif test_name == "updater":
            from test_exif_updater import TestExifUpdater
            suite = unittest.TestLoader().loadTestsFromTestCase(TestExifUpdater)
        elif test_name == "integration":
            from test_integration import TestIntegration
            suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegration)
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: analyzer, updater, integration")
            return False
        
        # Run the specific test
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
        
    except ImportError as e:
        print(f"Failed to import test module: {e}")
        return False


def main():
    """Main test runner function."""
    
    print("EXIF Date Updater - Test Suite")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        print(f"Running specific test: {test_name}")
        success = run_specific_test(test_name)
    else:
        # Run all tests
        print("Running all tests...")
        success = discover_and_run_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
