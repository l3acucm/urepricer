#!/usr/bin/env python3
"""Analyze test categories to create logical groupings."""

import re
from collections import defaultdict

def analyze_test_categories():
    """Analyze test method names to determine logical groupings."""
    
    with open("/Users/l3acucm/Projects/arbitrage-hero/urepricer/tests/strategies/test_all_331_original_tests.py", 'r') as f:
        content = f.read()
    
    # Extract all test method names
    test_methods = re.findall(r'def (test_[^(]+)', content)
    
    print(f"Found {len(test_methods)} test methods")
    
    # Categorize based on patterns
    categories = defaultdict(list)
    
    for method in test_methods:
        if 'lowest_price' in method:
            categories['lowest_price'].append(method)
        elif 'buybox' in method:
            categories['buybox'].append(method)
        elif 'b2b' in method:
            categories['b2b'].append(method)
        elif 'maximum_profit' in method:
            categories['maximum_profit'].append(method)
        elif 'tier' in method:
            categories['tiered_pricing'].append(method)
        elif 'amazon' in method and 'price_update' in method:
            categories['basic_pricing'].append(method)
        else:
            categories['miscellaneous'].append(method)
    
    # Show categories and counts
    print("\nTest Categories:")
    print("=" * 50)
    for category, tests in categories.items():
        print(f"{category}: {len(tests)} tests")
        # Show first few examples
        for i, test in enumerate(tests[:3]):
            print(f"  - {test}")
        if len(tests) > 3:
            print(f"  ... and {len(tests) - 3} more")
        print()
    
    return categories

if __name__ == "__main__":
    categories = analyze_test_categories()