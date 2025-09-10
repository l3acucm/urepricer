#!/usr/bin/env python3
"""
Simple test runner that mocks missing dependencies and runs the strategy tests.
"""

import sys
import os
from unittest.mock import Mock

# Mock missing dependencies
class MockLogger:
    def bind(self, **kwargs):
        return self
    
    def info(self, msg, extra=None, **kwargs):
        pass
    
    def warning(self, msg, extra=None, **kwargs):
        pass
    
    def error(self, msg, extra=None, **kwargs):
        pass
    
    def debug(self, msg, extra=None, **kwargs):
        pass
    
    def critical(self, msg, extra=None, **kwargs):
        pass

# Mock modules
sys.modules['loguru'] = type('MockModule', (), {'logger': MockLogger()})()
sys.modules['python-dotenv'] = Mock()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run tests
if __name__ == "__main__":
    import subprocess
    
    print("Running strategy tests with mocked dependencies...")
    
    try:
        # Use python's unittest module instead of pytest
        result = subprocess.run([
            sys.executable, '-m', 'unittest', 
            'tests.test_strategies', 
            '-v'
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Exit code: {result.returncode}")
        
    except Exception as e:
        print(f"Failed to run tests: {e}")
        
        # Fallback: try to import and run basic validation
        print("\nFallback: Running basic validation...")
        
        try:
            from strategies import ChaseBuyBox, MaximiseProfit, OnlySeller, PriceBoundsError
            from strategies.base_strategy import BaseStrategy
            
            print("✅ Successfully imported all strategy classes")
            print(f"✅ ChaseBuyBox inherits from BaseStrategy: {issubclass(ChaseBuyBox, BaseStrategy)}")
            print(f"✅ MaximiseProfit inherits from BaseStrategy: {issubclass(MaximiseProfit, BaseStrategy)}")
            print(f"✅ OnlySeller inherits from BaseStrategy: {issubclass(OnlySeller, BaseStrategy)}")
            print(f"✅ PriceBoundsError is available: {PriceBoundsError}")
            
            # Try creating a strategy instance
            mock_product = Mock()
            mock_product.asin = "B07TEST123"
            mock_product.seller_id = "TEST_SELLER"
            mock_product.account = Mock()
            mock_product.account.seller_id = "TEST_SELLER"
            mock_product.strategy = Mock()
            mock_product.strategy.beat_by = 0.01
            mock_product.strategy_id = "1"
            mock_product.min_price = 10.0
            mock_product.max_price = 50.0
            mock_product.competitor_price = 30.0
            mock_product.listed_price = 25.0
            mock_product.is_b2b = False
            mock_product.tiers = {}
            
            strategy = ChaseBuyBox(mock_product)
            print(f"✅ ChaseBuyBox strategy created successfully")
            print(f"✅ Strategy name: {strategy.get_strategy_name()}")
            
        except Exception as e:
            print(f"❌ Import validation failed: {e}")
            import traceback
            traceback.print_exc()