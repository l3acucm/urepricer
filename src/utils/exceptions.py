"""Shared exceptions for the repricing system."""


class SkipProductRepricing(Exception):
    """Exception raised when a product should be skipped during repricing."""
    pass


class PriceBoundsError(Exception):
    """Exception raised when calculated price is outside product's min/max bounds."""
    
    def __init__(self, message: str, calculated_price: float, min_price: float, max_price: float):
        super().__init__(message)
        self.calculated_price = calculated_price
        self.min_price = min_price
        self.max_price = max_price


class StrategyNotFoundError(Exception):
    """Exception raised when a strategy is not found."""
    pass


class ProductNotFoundError(Exception):
    """Exception raised when a product is not found."""
    pass


class PriceValidationError(Exception):
    """Exception raised when price validation fails."""
    pass