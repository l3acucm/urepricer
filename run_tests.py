#!/usr/bin/env python3
"""
Test runner for urepricer tests.
"""
import sys
import os
import unittest

# Add src directory to Python path
current_dir = os.path.dirname(__file__)
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Add original repricer directory for test data
repricer_dir = os.path.join(current_dir, '..', 'repricer', 'repricer')
sys.path.insert(0, repricer_dir)

def run_tests():
    """Run all tests in the tests directory."""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(current_dir, 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_specific_category(category):
    """Run tests for a specific category."""
    category_files = {
        'basic': 'test_basic_pricing.py',
        'lowest_min': 'test_lowest_price_min.py', 
        'lowest_max': 'test_lowest_price_max.py',
        'fba': 'test_lowest_fba_price.py',
        'buybox': 'test_match_buybox.py',
        'b2b': 'test_b2b_pricing.py',
        'special': 'test_special_cases.py',
        'strategy': ['test_maximise_profit.py', 'test_only_seller.py', 'test_new_price_processor.py']
    }
    
    if category not in category_files:
        print(f"Unknown category: {category}")
        print(f"Available categories: {list(category_files.keys())}")
        return False
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    files = category_files[category]
    if isinstance(files, str):
        files = [files]
    
    for file in files:
        test_path = os.path.join(current_dir, 'tests', file)
        if os.path.exists(test_path):
            # Import and add tests
            module_name = file.replace('.py', '')
            spec = importlib.util.spec_from_file_location(module_name, test_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            suite.addTests(loader.loadTestsFromModule(module))
        else:
            print(f"Test file not found: {test_path}")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    import importlib.util
    
    if len(sys.argv) > 1:
        category = sys.argv[1]
        success = run_specific_category(category)
    else:
        print("Running all tests...")
        success = run_tests()
    
    sys.exit(0 if success else 1)