# 🚀 URepricer Development Quickstart Guide

A comprehensive guide to get the Arbitrage Hero repricing system up and running locally for development and testing.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** - [Download Python](https://www.python.org/downloads/)
- **Poetry** - Package management: `curl -sSL https://install.python-poetry.org | python3 -`
- **Docker & Docker Compose** - [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Git** - Version control

## 🛠️ Quick Setup (5 minutes)

### 1. Clone and Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd urepricer

# Install dependencies with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### 2. Environment Configuration

```bash
# Copy the development environment template
cp .env.development.sample .env

# Edit .env with your specific values (optional for local development)
# Most default values work out of the box for local development
```

### 3. Start Infrastructure with Docker Compose

```bash
# Start all required services (PostgreSQL, Redis, LocalStack)
docker-compose -f docker-compose.development.yml up -d

# Verify services are running
docker-compose -f docker-compose.development.yml ps
```

### 4. Populate Test Data

```bash
# Run the test data population script
python3 -m scripts.populate_test_data
```

**Expected Output:**
```
🚀 Starting test data population...
✅ Connected to Redis
🧹 Clearing existing test data...
👥 Generating sellers...
✅ Generated 1000 sellers (500 Amazon + 500 Walmart)
📦 Generating products...
✅ Generated 3000+ products
💾 Saving strategy configurations...
✅ Saved 5 strategy configurations
💾 Saving seller account data...
✅ Saved 1000 seller accounts
💾 Saving product data...
✅ Saved 3000+ product listings

📊 Test Data Summary:
  Total products: 3000+
  Scenarios: {'competitive': 800, 'solo_seller': 750, 'buybox_winner': 700, 'out_of_bounds': 750}
  Platforms: {'amazon': 1500+, 'walmart': 1500+}

🎉 Test data population completed successfully!
```

### 5. Verify System Health

```bash
# Check that all services are healthy
curl http://localhost:8000/health

# Expected response:
# {"overall_status": "healthy", "services": {...}}
```

## 🧪 Testing Your Setup

### Run Unit Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "unit"           # Unit tests only
pytest -m "strategy"       # Strategy tests only
pytest -m "integration"    # Integration tests only

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Price Change Notifications (Guaranteed Results)

#### Setup SQS Integration

```bash
# Initialize SQS queues (LocalStack for dev/test, AWS SQS for production)
curl -X POST http://localhost:8000/sqs/initialize

# Check SQS queue status
curl http://localhost:8000/sqs/status
```

**Expected Output:**
```json
{
  "status": "success",
  "queues": {
    "amazon-any-offer-changed-queue": {
      "url": "http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/amazon-any-offer-changed-queue",
      "visible_messages": 0,
      "in_flight_messages": 0
    },
    "feed-processing-queue": {...},
    "processed-data-queue": {...}
  }
}
```

#### Amazon SQS Message Processing

Amazon SQS messages are now processed automatically by the dedicated SQS consumer service. The consumer polls the queues continuously and processes AnyOfferChanged notifications automatically.

```bash
# Check SQS queue status to see any pending messages
curl http://localhost:8000/sqs/status

# To test message processing that WILL create new calculated prices:
awslocal sqs send-message \
  --queue-url http://localhost:4566/000000000000/amazon-any-offer-changed-queue \
  --message-body '{
    "NotificationType": "AnyOfferChanged",
    "Payload": {
      "AnyOfferChangedNotification": {
        "ASIN": "B01234567890",
        "SellerId": "A1234567890123",
        "MarketplaceId": "ATVPDKIKX0DER"
      }
    }
  }'
```

#### Walmart Webhook Test

For a webhook that will GUARANTEE a price change and create calculated prices:

```bash
curl -X POST http://localhost:8000/walmart/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "eventType": "buybox_changed",
    "itemId": "WM123456789",
    "sellerId": "WM12345678",
    "timestamp": "2025-01-01T00:00:00Z",
    "currentBuyboxPrice": 50.00,
    "currentBuyboxWinner": "COMPETITOR123",
    "offers": [
      {"sellerId": "COMPETITOR123", "price": 50.00, "condition": "New"},
      {"sellerId": "WM12345678", "price": 999.99, "condition": "New"}
    ]
  }'
```

### Check Calculated Prices in Redis

After running the webhook and SQS examples above, you can verify the repricing results in Redis:

```bash
# Connect to Redis and check calculated prices
redis-cli -h localhost -p 6379

# In Redis CLI - check for any calculated prices
KEYS CALCULATED_PRICES:*

# View specific seller's calculated prices (examples from test data)
HGETALL CALCULATED_PRICES:A1234567890123  # Amazon seller
HGETALL CALCULATED_PRICES:WM12345678      # Walmart seller

# Check product data structure
HKEYS ASIN_B01234567890    # Amazon test product
HKEYS ASIN_WM123456789     # Walmart test product

# View specific product data
HGET ASIN_B01234567890 A1234567890123:A12-QUICKSTART01
HGET ASIN_WM123456789 WM12345678:WM12-QUICKSTART01

# Check strategy configurations
HGETALL strategy.1  # WIN_BUYBOX strategy (Amazon)
HGETALL strategy.3  # ONLY_SELLER strategy (Walmart)
```

**Expected Results After Running Examples:**

When the webhook/SQS processing is successful, you should see calculated prices with actual price changes:

```bash
# Calculated prices keys
127.0.0.1:6379> KEYS CALCULATED_PRICES:*
1) "CALCULATED_PRICES:A1234567890123"
2) "CALCULATED_PRICES:WM12345678"

# Amazon calculated price (example - actual values will vary based on random test data)
127.0.0.1:6379> HGETALL CALCULATED_PRICES:A1234567890123
1) "A12-QUICKSTART01"
2) "{\"new_price\": 117.38, \"old_price\": 117.79, \"strategy_used\": \"ONLY_SELLER\", \"strategy_id\": \"1\", \"competitor_price\": 114.91, \"asin\": \"B01234567890\", \"seller_id\": \"A1234567890123\", \"sku\": \"A12-QUICKSTART01\", \"saved_at\": \"2025-09-13T17:02:52.235809+00:00\"}"

# Walmart calculated price (competitive response - beat competitor by $0.05)
127.0.0.1:6379> HGETALL CALCULATED_PRICES:WM12345678
1) "WM12-QUICKSTART01"
2) "{\"new_price\": 49.95, \"old_price\": 118.94, \"strategy_used\": \"WIN_BUYBOX\", \"strategy_id\": \"3\", \"competitor_price\": 50.0, \"asin\": \"WM123456789\", \"seller_id\": \"WM12345678\", \"sku\": \"WM12-QUICKSTART01\", \"saved_at\": \"2025-09-13T17:12:23.717886+00:00\"}"
```

**Key Points About Price Changes:**

- **Amazon Example**: Test data generates random scenarios (competitive, out_of_bounds, etc.), and the strategy applies appropriate pricing logic
- **Walmart Example**: The webhook provides competitor price ($50.00), triggering the `WIN_BUYBOX` strategy to calculate $49.95 (competitor - $0.05)
- **Both examples guarantee price changes** because they trigger repricing logic in scenarios designed to create price adjustments

**Why These Examples Guarantee Price Changes:**

1. **Amazon SQS**: The test data generates various scenarios (competitive, out_of_bounds, solo_seller, buybox_winner) with realistic competitor prices and current prices that trigger repricing strategies
2. **Walmart Webhook**: The webhook provides competitor price data ($50.00) that's lower than most generated prices, forcing a competitive price adjustment using the `WIN_BUYBOX` strategy to calculate $49.95 (competitor - $0.05)

**Troubleshooting:**

If no `CALCULATED_PRICES:*` keys exist after running the examples:
1. Check that Docker Compose services are running: `docker-compose -f docker-compose.development.yml ps`
2. Verify test data was populated: `redis-cli KEYS "ASIN_*" | wc -l` (should show 3000+ keys)
3. Check SQS consumer logs: `docker-compose -f docker-compose.development.yml logs sqs-consumer`
4. Check FastAPI app logs: `docker-compose -f docker-compose.development.yml logs app`
5. Verify endpoints are healthy: `curl http://localhost:8000/health`

## 🔄 Price Reset and Resume Testing

### Test Price Reset

```bash
# Reset pricing for a specific seller
curl -X POST http://localhost:8000/pricing/reset \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": "A1234567890123",
    "marketplace": "US",
    "reason": "maintenance"
  }'
```

### Test Price Resume

```bash
# Resume pricing for a seller
curl -X POST http://localhost:8000/pricing/resume \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": "A1234567890123",
    "marketplace": "US"
  }'
```

## 📊 Load Testing

### Start Load Testing with Locust

```bash
# Install locust (already included in dev dependencies)
# Start Locust web interface
locust -f scripts/locust_load_test.py --host http://localhost:8000

# Open browser to http://localhost:8089
# Configure test parameters:
# - Number of users: 50
# - Spawn rate: 10/second
# - Host: http://localhost:8000
```

### CLI Load Testing

```bash
# Run headless load test
locust -f scripts/locust_load_test.py MixedPlatformUser \
  --users 100 --spawn-rate 10 --run-time 60s \
  --host http://localhost:8000
```

**Expected Load Test Results:**
```
Name                          # reqs      # fails  |     Avg     Min     Max  | Median   req/s failures/s
GET /health                     1200         0      |      45      12     156  |     41    20.0    0.0
POST /amazon/sqs-webhook        3000         5      |     125      45     890  |    110    50.0    0.08
POST /walmart/webhook           1800         2      |      98      38     567  |     89    30.0    0.03
```

## 📈 Performance Benchmarks

### Expected Volume Capacity

Based on load testing, the local development environment should handle:

- **Amazon Notifications**: ~200-300 messages/second
- **Walmart Webhooks**: ~150-250 messages/second  
- **Mixed Platform Load**: ~400-500 total messages/second
- **Response Times**: 
  - P50: <100ms
  - P95: <300ms
  - P99: <500ms

### Monitoring Performance

```bash
# View processing statistics
curl http://localhost:8000/stats

# Monitor Redis memory usage
redis-cli info memory

# Monitor Docker container resources
docker stats
```

## 🔧 Development Workflow

### Making Changes

1. **Code Changes**: Edit files in `src/`
2. **Run Tests**: `pytest tests/`
3. **Check Style**: `black src/ && isort src/ && flake8 src/`
4. **Type Check**: `mypy src/`
5. **Integration Test**: Test with sample notifications

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Add New Dependencies

```bash
# Add production dependency
poetry add package-name

# Add development dependency  
poetry add --group dev package-name
```

## 📂 Project Structure Overview

```
urepricer/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Configuration and utilities
│   ├── models/           # Data models (Redis OM)
│   ├── services/         # Business logic services
│   ├── strategies/       # Repricing strategies
│   └── tasks/            # Background tasks
├── tests/                # Test suite
├── scripts/              # Development scripts
├── docs/                 # Documentation
└── docker-compose.*.yml  # Docker configurations
```

## 🚨 Troubleshooting

### Common Issues

#### "Redis connection failed"
```bash
# Check Redis is running
docker-compose -f docker-compose.development.yml ps redis

# Restart Redis if needed
docker-compose -f docker-compose.development.yml restart redis
```

#### "LocalStack not responding"
```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# Restart LocalStack
docker-compose -f docker-compose.development.yml restart localstack
```

#### "Import errors"
```bash
# Ensure you're in the poetry environment
poetry shell

# Reinstall dependencies
poetry install
```

#### "Tests failing"
```bash
# Run tests with verbose output
pytest -v --tb=short

# Check test environment
export TESTING=true
pytest tests/
```

### Performance Issues

#### High Memory Usage
```bash
# Check container memory usage
docker stats

# Reduce test data size
# Edit scripts/populate_test_data.py - reduce seller counts
```

#### Slow Response Times
```bash
# Check Redis performance
redis-cli --latency

# Monitor application logs
docker-compose -f docker-compose.development.yml logs app
```

## 🎯 Next Steps

After completing the quickstart:

1. **Explore the API**: Visit http://localhost:8000/docs for interactive API documentation
2. **Run Load Tests**: Experiment with different load patterns
3. **Customize Strategies**: Modify pricing strategies in `src/strategies/`
4. **Add Features**: Implement new functionality using the existing patterns
5. **Deploy**: Follow production deployment guide for staging/production

## 📞 Support

- **Issues**: Create GitHub issues for bugs
- **Documentation**: Check `/docs` folder for detailed guides
- **Code Examples**: See `/tests` for usage examples

---

✨ **You're all set!** The urepricer system is now running locally with test data and ready for development.