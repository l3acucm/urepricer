# Pricing Strategies

## Overview

The URepricer system implements multiple pricing strategies to optimize competitiveness and profitability across different market scenarios.

## Available Strategies

### 1. **MaximiseProfit Strategy**
- **Objective**: Maximize profit by pricing at competitor levels
- **Logic**: Sets price equal to competitor price when competitor is higher
- **Use Case**: When seller has competitive advantage or unique product features

### 2. **ChaseBuyBox Strategy** 
- **Objective**: Win the buybox by beating competitor prices
- **Logic**: Price = competitor_price + beat_by amount
- **Use Case**: High-volume, competitive products where buybox is critical

### 3. **OnlySeller Strategy**
- **Objective**: Maintain consistent pricing when no competition
- **Logic**: Uses default price or calculated mean of min/max bounds
- **Use Case**: Unique products or market segments with no direct competition

## Self-Competition Prevention

All strategies include robust self-competition prevention:
- Filters out seller's own offers when identifying competitors
- Raises `SkipProductRepricing` when no valid competitors exist
- Ensures pricing decisions are based only on external competition

## Price Bounds Validation

Every strategy enforces price bounds:
- **Minimum Price**: Prevents pricing below cost thresholds
- **Maximum Price**: Prevents pricing above brand guidelines
- **Bounds Violation**: Raises `PriceBoundsError` with detailed information

## B2B Pricing Support

Strategies automatically handle B2B tier pricing:
- Applies strategy logic to each quantity tier
- Independent price calculation per tier
- Graceful handling of tier-specific bounds violations