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

### Test Amazon SQS Messages - 5 Strategy Examples

Each example below triggers a different repricing strategy with manipulatable prices. These align with the 5 strategies populated by `populate_test_data.py`:

#### 1. Strategy 1: LOWEST_PRICE Competition (Beat by $0.01)
**Expected Result**: Our price will be set to $49.99 (competitor's lowest price $50.00 - $0.01)

```bash
awslocal sqs send-message \
  --queue-url http://localhost:4566/000000000000/amazon-any-offer-changed-queue \
  --message-body '{
    "NotificationType": "ANY_OFFER_CHANGED",
    "NotificationVersion": "1.0",
    "PayloadVersion": "1.0",
    "EventTime": "2025-01-01T00:00:00.000Z",
    "Payload": {
      "OfferChangeTrigger": {
        "MarketplaceId": "ATVPDKIKX0DER",
        "ASIN": "B01234567890",
        "ItemCondition": "New",
        "TimeOfOfferChange": "2025-01-01T00:00:00.000Z",
        "OfferChangeType": "External"
      },
      "Summary": {
        "NumberOfOffers": [
          {"Condition": "New", "FulfillmentChannel": "Amazon", "OfferCount": 3}
        ],
        "LowestPrices": [
          {
            "Condition": "New",
            "FulfillmentChannel": "Amazon", 
            "ListingPrice": {"Amount": 50.00, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 50.00, "CurrencyCode": "USD"}
          }
        ],
        "BuyBoxPrices": [
          {
            "Condition": "New",
            "ListingPrice": {"Amount": 51.50, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 51.50, "CurrencyCode": "USD"}
          }
        ]
      },
      "Offers": [
        {
          "SellerId": "A2345678901234",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 50.00, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Amazon"
        },
        {
          "SellerId": "A3456789012345", 
          "SubCondition": "New",
          "ListingPrice": {"Amount": 51.50, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": true,
          "FulfillmentChannel": "Amazon"
        }
      ]
    }
  }'
```

#### 2. Strategy 2: MATCH_BUYBOX Competition (Beat by $0.01)
**Expected Result**: Our price will be set to $26.49 (buybox price $26.50 - $0.01)

```bash
awslocal sqs send-message \
  --queue-url http://localhost:4566/000000000000/amazon-any-offer-changed-queue \
  --message-body '{
    "NotificationType": "ANY_OFFER_CHANGED",
    "NotificationVersion": "1.0", 
    "PayloadVersion": "1.0",
    "EventTime": "2025-01-01T00:00:00.000Z",
    "Payload": {
      "OfferChangeTrigger": {
        "MarketplaceId": "ATVPDKIKX0DER",
        "ASIN": "B01234567891",
        "ItemCondition": "New",
        "TimeOfOfferChange": "2025-01-01T00:00:00.000Z"
      },
      "Summary": {
        "NumberOfOffers": [
          {"Condition": "New", "FulfillmentChannel": "Amazon", "OfferCount": 2}
        ],
        "LowestPrices": [
          {
            "Condition": "New",
            "FulfillmentChannel": "Amazon",
            "ListingPrice": {"Amount": 24.99, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 24.99, "CurrencyCode": "USD"}
          }
        ],
        "BuyBoxPrices": [
          {
            "Condition": "New", 
            "ListingPrice": {"Amount": 26.50, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 26.50, "CurrencyCode": "USD"}
          }
        ]
      },
      "Offers": [
        {
          "SellerId": "A2345678901234",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 24.99, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Merchant"
        },
        {
          "SellerId": "A3456789012345",
          "SubCondition": "New", 
          "ListingPrice": {"Amount": 26.50, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": true,
          "FulfillmentChannel": "Amazon"
        }
      ]
    }
  }'
```

#### 3. Strategy 3: FBA_LOWEST Competition (Beat by $0.05)
**Expected Result**: Our price will be set to $22.95 (lowest FBA price $23.00 - $0.05)

```bash
awslocal sqs send-message \
  --queue-url http://localhost:4566/000000000000/amazon-any-offer-changed-queue \
  --message-body '{
    "NotificationType": "ANY_OFFER_CHANGED",
    "NotificationVersion": "1.0",
    "PayloadVersion": "1.0", 
    "EventTime": "2025-01-01T00:00:00.000Z",
    "Payload": {
      "OfferChangeTrigger": {
        "MarketplaceId": "ATVPDKIKX0DER",
        "ASIN": "B01234567892",
        "ItemCondition": "New",
        "TimeOfOfferChange": "2025-01-01T00:00:00.000Z"
      },
      "Summary": {
        "NumberOfOffers": [
          {"Condition": "New", "FulfillmentChannel": "Amazon", "OfferCount": 2},
          {"Condition": "New", "FulfillmentChannel": "Merchant", "OfferCount": 1}
        ],
        "LowestPrices": [
          {
            "Condition": "New",
            "FulfillmentChannel": "Amazon",
            "ListingPrice": {"Amount": 23.00, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 23.00, "CurrencyCode": "USD"}
          },
          {
            "Condition": "New", 
            "FulfillmentChannel": "Merchant",
            "ListingPrice": {"Amount": 21.50, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 26.50, "CurrencyCode": "USD"}
          }
        ]
      },
      "Offers": [
        {
          "SellerId": "A2345678901234",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 23.00, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Amazon"
        },
        {
          "SellerId": "A3456789012345",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 24.00, "CurrencyCode": "USD"}, 
          "IsBuyBoxWinner": true,
          "FulfillmentChannel": "Amazon"
        },
        {
          "SellerId": "A4567890123456",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 21.50, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Merchant"
        }
      ]
    }
  }'
```

#### 4. Strategy 4: LOWEST_PRICE Match (No Beat-By)
**Expected Result**: Our price will be set to exactly $27.99 (match lowest price)

```bash
awslocal sqs send-message \
  --queue-url http://localhost:4566/000000000000/amazon-any-offer-changed-queue \
  --message-body '{
    "NotificationType": "ANY_OFFER_CHANGED",
    "NotificationVersion": "1.0",
    "PayloadVersion": "1.0",
    "EventTime": "2025-01-01T00:00:00.000Z",
    "Payload": {
      "OfferChangeTrigger": {
        "MarketplaceId": "ATVPDKIKX0DER", 
        "ASIN": "B01234567893",
        "ItemCondition": "New",
        "TimeOfOfferChange": "2025-01-01T00:00:00.000Z"
      },
      "Summary": {
        "NumberOfOffers": [
          {"Condition": "New", "FulfillmentChannel": "Amazon", "OfferCount": 3}
        ],
        "LowestPrices": [
          {
            "Condition": "New",
            "FulfillmentChannel": "Amazon",
            "ListingPrice": {"Amount": 27.99, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 27.99, "CurrencyCode": "USD"}
          }
        ],
        "BuyBoxPrices": [
          {
            "Condition": "New",
            "ListingPrice": {"Amount": 29.99, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 29.99, "CurrencyCode": "USD"}
          }
        ]
      },
      "Offers": [
        {
          "SellerId": "A2345678901234",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 27.99, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Amazon"
        },
        {
          "SellerId": "A3456789012345",
          "SubCondition": "New", 
          "ListingPrice": {"Amount": 29.99, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": true,
          "FulfillmentChannel": "Amazon"
        }
      ]
    }
  }'
```

#### 5. Strategy 5: MATCH_BUYBOX Aggressive (Beat by $0.10)
**Expected Result**: Our price will be set to $28.90 (buybox price $29.00 - $0.10)

```bash
awslocal sqs send-message \
  --queue-url http://localhost:4566/000000000000/amazon-any-offer-changed-queue \
  --message-body '{
    "NotificationType": "ANY_OFFER_CHANGED",
    "NotificationVersion": "1.0",
    "PayloadVersion": "1.0",
    "EventTime": "2025-01-01T00:00:00.000Z",
    "Payload": {
      "OfferChangeTrigger": {
        "MarketplaceId": "ATVPDKIKX0DER",
        "ASIN": "B01234567894", 
        "ItemCondition": "New",
        "TimeOfOfferChange": "2025-01-01T00:00:00.000Z"
      },
      "Summary": {
        "NumberOfOffers": [
          {"Condition": "New", "FulfillmentChannel": "Amazon", "OfferCount": 4}
        ],
        "LowestPrices": [
          {
            "Condition": "New",
            "FulfillmentChannel": "Amazon",
            "ListingPrice": {"Amount": 28.50, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 28.50, "CurrencyCode": "USD"}
          }
        ],
        "BuyBoxPrices": [
          {
            "Condition": "New",
            "ListingPrice": {"Amount": 29.00, "CurrencyCode": "USD"},
            "LandedPrice": {"Amount": 29.00, "CurrencyCode": "USD"}
          }
        ]
      },
      "Offers": [
        {
          "SellerId": "A2345678901234",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 28.50, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Amazon"
        },
        {
          "SellerId": "A3456789012345",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 29.00, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": true,
          "FulfillmentChannel": "Amazon"
        },
        {
          "SellerId": "A4567890123456",
          "SubCondition": "New",
          "ListingPrice": {"Amount": 31.99, "CurrencyCode": "USD"},
          "IsBuyBoxWinner": false,
          "FulfillmentChannel": "Amazon"
        }
      ]
    }
  }'
```

### 📊 Strategy Explanation

| Strategy ID | Compete With | Beat By | Expected Behavior |
|-------------|--------------|---------|-------------------|
| 1 | LOWEST_PRICE | -$0.01 | Beats lowest competitor price by 1 cent |
| 2 | MATCH_BUYBOX | -$0.01 | Beats current buybox price by 1 cent |
| 3 | FBA_LOWEST | -$0.05 | Beats lowest FBA price by 5 cents |
| 4 | LOWEST_PRICE | $0.00 | Matches lowest price exactly |
| 5 | MATCH_BUYBOX | -$0.10 | Beats buybox price by 10 cents |

**Note**: You can modify the `ListingPrice.Amount` values in any of the above examples to test different price scenarios and observe how each strategy responds.

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
# Calculated prices keys (will vary based on which examples you run)
127.0.0.1:6379> KEYS CALCULATED_PRICES:*
1) "CALCULATED_PRICES:A1234567890123"  # Strategy examples 1-5
2) "CALCULATED_PRICES:WM12345678"      # Walmart example

# Strategy 1 Example: LOWEST_PRICE Competition (-$0.01)
127.0.0.1:6379> HGETALL CALCULATED_PRICES:A1234567890123
1) "A12-QUICKSTART01"
2) "{\"new_price\": 24.99, \"old_price\": 28.50, \"strategy_used\": \"ChaseBuyBox\", \"strategy_id\": \"1\", \"competitor_price\": 25.00, \"asin\": \"B01234567890\", \"seller_id\": \"A1234567890123\", \"sku\": \"A12-QUICKSTART01\", \"calculated_at\": \"2025-01-01T12:00:00.000Z\"}"

# Strategy 2 Example: MATCH_BUYBOX Competition (-$0.01)  
127.0.0.1:6379> HGETALL CALCULATED_PRICES:A1234567890123
1) "A12-QUICKSTART02"
2) "{\"new_price\": 26.49, \"old_price\": 29.99, \"strategy_used\": \"ChaseBuyBox\", \"strategy_id\": \"2\", \"competitor_price\": 26.50, \"asin\": \"B01234567891\", \"seller_id\": \"A1234567890123\", \"sku\": \"A12-QUICKSTART02\", \"calculated_at\": \"2025-01-01T12:01:00.000Z\"}"

# Strategy 3 Example: FBA_LOWEST Competition (-$0.05)
127.0.0.1:6379> HGETALL CALCULATED_PRICES:A1234567890123  
1) "A12-QUICKSTART03"
2) "{\"new_price\": 22.95, \"old_price\": 26.00, \"strategy_used\": \"ChaseBuyBox\", \"strategy_id\": \"3\", \"competitor_price\": 23.00, \"asin\": \"B01234567892\", \"seller_id\": \"A1234567890123\", \"sku\": \"A12-QUICKSTART03\", \"calculated_at\": \"2025-01-01T12:02:00.000Z\"}"

# Strategy 4 Example: LOWEST_PRICE Match (No Beat-By)
127.0.0.1:6379> HGETALL CALCULATED_PRICES:A1234567890123
1) "A12-QUICKSTART04" 
2) "{\"new_price\": 27.99, \"old_price\": 32.00, \"strategy_used\": \"MaximiseProfit\", \"strategy_id\": \"4\", \"competitor_price\": 27.99, \"asin\": \"B01234567893\", \"seller_id\": \"A1234567890123\", \"sku\": \"A12-QUICKSTART04\", \"calculated_at\": \"2025-01-01T12:03:00.000Z\"}"

# Strategy 5 Example: MATCH_BUYBOX Aggressive (-$0.10)
127.0.0.1:6379> HGETALL CALCULATED_PRICES:A1234567890123
1) "A12-QUICKSTART05"
2) "{\"new_price\": 28.90, \"old_price\": 31.50, \"strategy_used\": \"ChaseBuyBox\", \"strategy_id\": \"5\", \"competitor_price\": 29.00, \"asin\": \"B01234567894\", \"seller_id\": \"A1234567890123\", \"sku\": \"A12-QUICKSTART05\", \"calculated_at\": \"2025-01-01T12:04:00.000Z\"}"

# Walmart calculated price (competitive response - beat competitor by $0.05)
127.0.0.1:6379> HGETALL CALCULATED_PRICES:WM12345678
1) "WM12-QUICKSTART01"
2) "{\"new_price\": 49.95, \"old_price\": 118.94, \"strategy_used\": \"ChaseBuyBox\", \"strategy_id\": \"3\", \"competitor_price\": 50.0, \"asin\": \"WM123456789\", \"seller_id\": \"WM12345678\", \"sku\": \"WM12-QUICKSTART01\", \"calculated_at\": \"2025-01-01T12:05:00.000Z\"}"
```

**Key Points About Price Changes:**

- **Amazon SP-API Examples**: Each example contains specific competitor pricing in `Summary.LowestPrices` and `Summary.BuyBoxPrices` that triggers different strategy behaviors
- **Walmart Example**: The webhook provides competitor price ($50.00), triggering the `ChaseBuyBox` strategy to calculate $49.95 (competitor - $0.05)  
- **All examples guarantee price changes** because they provide realistic competitive scenarios that force repricing calculations

**Why These Examples Guarantee Price Changes:**

1. **Amazon SQS Strategy Examples**: Each message contains carefully crafted pricing data in the SP-API compliant format:
   - Strategy 1: `LowestPrices` contains $25.00, triggers beat-by-$0.01 to $24.99
   - Strategy 2: `BuyBoxPrices` contains $26.50, triggers beat-by-$0.01 to $26.49  
   - Strategy 3: `LowestPrices` with FBA channel contains $23.00, triggers beat-by-$0.05 to $22.95
   - Strategy 4: `LowestPrices` contains $27.99, triggers exact match to $27.99
   - Strategy 5: `BuyBoxPrices` contains $29.00, triggers beat-by-$0.10 to $28.90

2. **Walmart Webhook**: Provides explicit competitor price ($50.00) that's significantly lower than typical test data prices, forcing competitive adjustment

3. **Manipulatable Pricing**: You can edit any `ListingPrice.Amount` or `LandedPrice.Amount` value in the examples to test different competitive scenarios

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