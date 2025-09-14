#!/bin/bash
redis-cli -h localhost -p 6379 FLUSHALL
python3 -m scripts.populate_test_data
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
sleep 90
redis-cli -h localhost -p 6379 KEYS CALCULATED_PRICES:*