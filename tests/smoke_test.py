"""Quick smoke tests to verify basic functionality."""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def test_imports():
    """Test that core modules can be imported."""
    print("Testing imports...")
    
    try:
        from exif_date_updater import ExifAnalyzer, ExifUpdater
        print("✅ Core modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import core modules: {e}")
        return False


def test_basic_functionality():
    """Test basic analyzer functionality with minimal setup."""
    print("Testing basic functionality...")
    
    try:
        from exif_date_updater import ExifAnalyzer
        analyzer = ExifAnalyzer()
        
        # Test that the analyzer has expected attributes
        assert hasattr(analyzer, 'IMAGE_EXTENSIONS')
        assert hasattr(analyzer, 'VIDEO_EXTENSIONS')
        assert hasattr(analyzer, 'DATE_PATTERNS')
        assert len(analyzer.IMAGE_EXTENSIONS) > 0
        assert len(analyzer.VIDEO_EXTENSIONS) > 0
        assert len(analyzer.DATE_PATTERNS) > 0
        
        print("✅ Basic functionality verified")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_date_pattern_matching():
    """Test date pattern recognition."""
    print("Testing date pattern recognition...")
    
    try:
        from exif_date_updater import ExifAnalyzer
        import re
        
        analyzer = ExifAnalyzer()
        
        # Test some basic patterns
        test_cases = [
            ("IMG_20231215_142030.jpg", True),
            ("photo_without_date.jpg", False),
            ("20231201_vacation.jpg", True),
        ]
        
        for filename, should_match in test_cases:
            found_match = False
            for pattern in analyzer.DATE_PATTERNS:
                if re.search(pattern, filename):
                    found_match = True
                    break
            
            if found_match != should_match:
                print(f"❌ Pattern matching failed for {filename}")
                return False
        
        print("✅ Date pattern recognition working")
        return True
        
    except Exception as e:
        print(f"❌ Date pattern test failed: {e}")
        return False


def main():
    """Run smoke tests."""
    print("EXIF Date Updater - Smoke Tests")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Date Pattern Matching", test_date_pattern_matching),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
        else:
            print(f"⚠️  Test '{test_name}' failed")
    
    print("\n" + "=" * 40)
    print(f"SMOKE TEST RESULTS: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All smoke tests passed! Basic functionality is working.")
        return True
    else:
        print("⚠️  Some smoke tests failed. Check the installation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
