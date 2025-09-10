# urepricer Tests

This directory contains the modularized test suite for the urepricer project, split from the original large `test.py` file in the repricer module.

## Test Structure

The original 8000+ line test file containing 329 test methods has been organized into the following categories:

### Main Test Files

1. **test_basic_pricing.py** (2 tests)
   - Basic Amazon price update tests
   - Standard and B2B Amazon price updates

2. **test_lowest_price_min.py** (25 tests)
   - Tests for lowest price strategy with min rule applied
   - Covers various scenarios like jump_to_min, match_competitor, default_price

3. **test_lowest_price_max.py** (23 tests)  
   - Tests for lowest price strategy with max rule applied
   - Similar scenarios but with max price rules

4. **test_lowest_fba_price.py** (51 tests)
   - Tests for lowest FBA (Fulfillment by Amazon) price strategy
   - Covers both min and max rule scenarios

5. **test_match_buybox.py** (78 tests)
   - Tests for match buybox pricing strategy
   - Most complex category with various price matching scenarios

6. **test_b2b_pricing.py** (120 tests)
   - Business-to-business pricing tests
   - Largest category with tiered pricing scenarios

7. **test_special_cases.py** (18 tests)
   - Edge cases and special scenarios
   - Includes only_seller, maximise_profit, and market-specific tests

8. **test_uncategorized.py** (placeholder)
   - Placeholder for the 12 uncategorized tests that need manual categorization

### Strategy Test Files (Transferred from repricer/strategies/tests/)

- **test_maximise_profit.py** - Tests for maximize profit strategy
- **test_only_seller.py** - Tests for only seller strategy  
- **test_new_price_processor.py** - Tests for price processing logic

## Configuration

### conftest.py
Contains shared fixtures and setup for all tests:
- BaseFixture class with common test setup
- _Fixture class with helper methods from original test structure
- Import handling for both urepricer and original repricer modules
- Redis client setup for integration tests

## Running Tests

### Run All Tests
```bash
python run_tests.py
```

### Run Specific Categories
```bash
python run_tests.py basic      # Basic pricing tests
python run_tests.py lowest_min # Lowest price min rule tests
python run_tests.py lowest_max # Lowest price max rule tests
python run_tests.py fba        # FBA price tests
python run_tests.py buybox     # Match buybox tests
python run_tests.py b2b        # B2B pricing tests
python run_tests.py special    # Special cases tests
python run_tests.py strategy   # Strategy-specific tests
```

### Run Individual Test Files
```bash
python -m pytest tests/test_basic_pricing.py
python -m unittest tests.test_basic_pricing
```

## Import Strategy

The test files are designed to work with both the new urepricer structure and fall back to the original repricer imports:

1. **Primary imports**: Try to import from the new urepricer structure
2. **Fallback imports**: Fall back to original repricer module imports
3. **Test data**: Always imported from original repricer module (test_data.py, constants.py)

## Dependencies

Tests require access to:
- Original repricer module for test data and constants
- Redis for integration tests  
- urepricer src modules for new structure
- Python 3.7+ and unittest framework

## Notes

- Tests maintain the same structure and logic as the original large test file
- Import paths are flexible to work during the transition period
- Test data remains centralized in the original repricer module
- Some tests may require Redis to be running for full functionality
- The `bad/` directory contains any problematic test files that need attention

## Future Improvements

1. Migrate test data from original repricer to urepricer
2. Update imports to use only urepricer modules
3. Add pytest configuration for better test reporting
4. Implement the remaining 12 uncategorized tests
5. Add test coverage reporting
6. Create integration test suites