# 🚀 URepricer Quick Start Guide - Local Development

Get started with URepricer's local development environment in minutes!

## 📋 Prerequisites

- **Python 3.11+** with Poetry installed
- **Redis server** running locally on port 6379
- **LocalStack** for AWS services emulation  
- **Virtual environment** activated

## 🛠 Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
poetry install

# Activate virtual environment
poetry shell

# Verify awslocal is available
awslocal --version
```

### 2. Start Required Services

#### Start Redis Server
```bash
# macOS with Homebrew
brew services start redis

# Ubuntu/Debian
sudo systemctl start redis-server

# Or run Redis in Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

#### Start LocalStack
```bash
# Install LocalStack
pip install localstack

# Start LocalStack in background
localstack start -d

# Verify LocalStack is running
curl http://localhost:4566/health
```

### 3. Configure Environment

Create your local environment file:
```bash
cp .env.development.sample .env.local
```

Edit `.env.local` with local settings:
```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# LocalStack Configuration  
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1

# Application Configuration
DEBUG=true
LOG_LEVEL=INFO
```

### 4. Initialize Services

#### Create SQS Queues
```bash
# Create required SQS queues
awslocal sqs create-queue --queue-name amazon-any-offer-changed-queue
awslocal sqs create-queue --queue-name feed-processing-queue
awslocal sqs create-queue --queue-name processed-data-queue

# Verify queues exist
awslocal sqs list-queues
```

## 🎯 Run the Application

### Start Core Services

#### 1. Start FastAPI Application
```bash
# Terminal 1: Start the main API server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Start SQS Consumer  
```bash
# Terminal 2: Start the SQS message consumer
python3 -m src.services.sqs_consumer
```

**Note**: The SQS consumer now runs as a separate standalone process instead of being embedded in the FastAPI application. This is a better practice for scalability and debugging.

### Verify Services are Running

```bash
# Check API health
curl http://localhost:8000/health

# Check Redis connection
redis-cli ping

# Check LocalStack health
curl http://localhost:4566/health
```

## 📊 Populate Test Data

```bash
# Clear any existing data and populate fresh test data
redis-cli FLUSHALL
python3 -m scripts.populate_test_data
```

## 🧪 Test Price Change Notifications (Guaranteed Results)

### Test Walmart Webhook

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

### Test Amazon SQS Message

```bash
# Send Amazon AnyOfferChanged notification
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
HGETALL ASIN_B01234567890  # Amazon product
HGETALL ASIN_WM123456789   # Walmart product

# View strategy configurations
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

## 🧪 Run End-to-End Tests

The provided e2e test script works with local development too:

```bash
# Run the complete end-to-end test
./e2e.sh
```

**Note**: The e2e.sh script will automatically:
1. Stop and start your local services
2. Clear and repopulate Redis data
3. Send test messages to both platforms
4. Validate that calculated prices are created
5. Show detailed pass/fail results with checkboxes

## 🔄 Development Workflow

### Making Code Changes

1. **API Changes**: The FastAPI server runs with `--reload`, so changes are picked up automatically
2. **SQS Consumer Changes**: Restart the SQS consumer process manually after changes
3. **Strategy Changes**: No restart needed, strategies are loaded dynamically

### Debugging

```bash
# View application logs
tail -f logs/app.log

# Check SQS consumer processing
# (Monitor Terminal 2 where SQS consumer is running)

# Monitor Redis operations
redis-cli monitor

# Check LocalStack SQS queues
awslocal sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/amazon-any-offer-changed-queue \
  --attribute-names ApproximateNumberOfMessages
```

## 🧹 Cleanup

```bash
# Stop Redis
brew services stop redis
# OR
sudo systemctl stop redis-server

# Stop LocalStack
localstack stop

# Clear Redis data if needed
redis-cli FLUSHALL

# Stop application processes (Ctrl+C in respective terminals)
```

## 🚨 Troubleshooting

If no `CALCULATED_PRICES:*` keys exist after running the examples:

1. **Check services are running**: 
   - Redis: `redis-cli ping`
   - LocalStack: `curl http://localhost:4566/health` 
   - FastAPI: `curl http://localhost:8000/health`

2. **Verify test data exists**: `redis-cli KEYS "ASIN_*" | wc -l` (should show 3000+ keys)

3. **Check SQS consumer logs**: Monitor Terminal 2 for processing messages

4. **Verify SQS queues exist**: `awslocal sqs list-queues`

5. **Check webhook processing**: Look for "accepted" response in webhook calls

## 🎯 Next Steps

- Explore the codebase in `src/` directory
- Add new repricing strategies in `src/strategies/`
- Modify test data generation in `scripts/populate_test_data.py`
- Check out `QUICKSTART_DOCKER.md` for Docker-based development
- Review API documentation at `http://localhost:8000/docs`

---

🎉 **You're all set!** The local URepricer environment is ready for development and testing.