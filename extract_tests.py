#!/usr/bin/env python3
"""
Script to extract and categorize tests from the large test.py file.
"""
import re
import os

def extract_test_method(lines, start_line, end_line):
    """Extract a test method from the lines."""
    method_lines = []
    indent_level = None
    
    for i in range(start_line - 1, len(lines)):
        line = lines[i]
        
        # Determine the base indent level from the first line
        if indent_level is None and line.strip().startswith('def test_'):
            indent_level = len(line) - len(line.lstrip())
        
        # If we find another method at the same or less indentation level, stop
        if (line.strip().startswith('def ') and 
            len(line) - len(line.lstrip()) <= indent_level and 
            i > start_line - 1):
            break
            
        method_lines.append(line.rstrip())
    
    return method_lines

def categorize_tests():
    """Categorize tests from the original file."""
    # Read the original test file
    test_file_path = os.path.join('..', 'repricer', 'repricer', 'test.py')
    
    with open(test_file_path, 'r') as f:
        lines = f.readlines()
    
    # Categories with their patterns and target files
    categories = {
        'basic_pricing': {
            'pattern': r'def test_(amazon_price_update|b2b_amazon_price_update)',
            'file': 'test_basic_pricing.py',
            'methods': []
        },
        'lowest_price_min': {
            'pattern': r'def test_.*lowest_price.*min_rule.*applied',
            'file': 'test_lowest_price_min.py',
            'methods': []
        },
        'lowest_price_max': {
            'pattern': r'def test_.*lowest_price.*max_rule.*applied',
            'file': 'test_lowest_price_max.py',
            'methods': []
        },
        'lowest_fba_price': {
            'pattern': r'def test_.*lowest_fba_price.*',
            'file': 'test_lowest_fba_price.py',
            'methods': []
        },
        'match_buybox': {
            'pattern': r'def test_.*match_buybox.*',
            'file': 'test_match_buybox.py',
            'methods': []
        },
        'b2b_pricing': {
            'pattern': r'def test_.*b2b.*',
            'file': 'test_b2b_pricing.py',
            'methods': []
        },
        'special_cases': {
            'pattern': r'def test_.*(only_seller|maximise_profit|buybox_suppressed_case|uk_seller|us_seller|pick_competitor_price|item_condition_match_club|all_default_values)',
            'file': 'test_special_cases.py',
            'methods': []
        }
    }
    
    # Find all test methods and their line numbers
    test_methods = []
    for i, line in enumerate(lines):
        if line.strip().startswith('def test_'):
            match = re.search(r'def (test_\w+)', line.strip())
            if match:
                test_methods.append((match.group(1), i + 1, line.strip()))
    
    print(f"Found {len(test_methods)} test methods")
    
    # Categorize each test method
    uncategorized = []
    
    for method_name, line_num, method_def in test_methods:
        categorized = False
        
        for category_name, category_info in categories.items():
            if re.search(category_info['pattern'], method_def):
                # Extract the full method
                method_lines = extract_test_method(lines, line_num, None)
                category_info['methods'].append({
                    'name': method_name,
                    'line_num': line_num,
                    'content': method_lines
                })
                categorized = True
                break
        
        if not categorized:
            uncategorized.append((method_name, line_num, method_def))
    
    # Report categorization results
    for category_name, category_info in categories.items():
        print(f"{category_name}: {len(category_info['methods'])} methods")
    
    print(f"Uncategorized: {len(uncategorized)} methods")
    
    if uncategorized:
        print("\nUncategorized methods:")
        for method_name, line_num, method_def in uncategorized[:10]:  # Show first 10
            print(f"  {line_num}: {method_name}")
    
    return categories, uncategorized

def generate_test_file(category_name, category_info, base_imports, class_name):
    """Generate content for a test file."""
    content = f'''"""
{class_name.replace('Test', '').replace('Pricing', ' pricing').title()} tests.
"""
import unittest
from .conftest import BaseFixture


class {class_name}(BaseFixture):
    """Test {category_name.replace('_', ' ')} functionality."""
    
'''
    
    # Add each test method
    for method_info in category_info['methods']:
        method_lines = method_info['content']
        for line in method_lines:
            # Adjust indentation - remove class-level indentation and add method-level
            if line.strip():
                if line.strip().startswith('def test_'):
                    content += f"    {line.strip()}\n"
                else:
                    # Preserve relative indentation
                    stripped = line.lstrip()
                    if stripped:
                        content += f"        {stripped}\n"
                    else:
                        content += "\n"
            else:
                content += "\n"
        content += "\n"
    
    content += '''

if __name__ == '__main__':
    unittest.main()'''
    
    return content

if __name__ == '__main__':
    categories, uncategorized = categorize_tests()
    
    # Generate test files
    base_imports = '''import unittest
from .conftest import BaseFixture'''
    
    class_names = {
        'basic_pricing': 'TestBasicPricing',
        'lowest_price_min': 'TestLowestPriceMin',
        'lowest_price_max': 'TestLowestPriceMax', 
        'lowest_fba_price': 'TestLowestFbaPrice',
        'match_buybox': 'TestMatchBuybox',
        'b2b_pricing': 'TestB2bPricing',
        'special_cases': 'TestSpecialCases'
    }
    
    # Create tests directory if it doesn't exist
    tests_dir = 'tests'
    os.makedirs(tests_dir, exist_ok=True)
    
    for category_name, category_info in categories.items():
        if category_info['methods']:  # Only create files with methods
            class_name = class_names.get(category_name, f'Test{category_name.title()}')
            content = generate_test_file(category_name, category_info, base_imports, class_name)
            
            file_path = os.path.join(tests_dir, category_info['file'])
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"Generated {file_path} with {len(category_info['methods'])} methods")
    
    # Generate a file for uncategorized tests
    if uncategorized:
        print(f"\nUncategorized methods ({len(uncategorized)}):")
        for method_name, line_num, method_def in uncategorized:
            print(f"  {method_name}")