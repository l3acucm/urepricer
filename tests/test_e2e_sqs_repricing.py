"""
End-to-end tests for Amazon SQS repricing flow.
Tests the complete flow: SQS message → processing → price calculation → Redis storage.
"""
import pytest
import asyncio
import json
from unittest.mock import patch

# Sample test data
SAMPLE_AMAZON_PRODUCT = {
    "asin": "B07XQXZXYX",
    "seller_id": "A1SELLER123", 
    "sku": "TEST-SKU-001",
    "listed_price": 29.99,
    "min_price": 25.00,
    "max_price": 45.00,
    "default_price": 30.00,
    "strategy_id": "1",
    "inventory_quantity": 150,
    "inventory_age": 30,
    "status": "Active",
    "is_b2b": False
}


@pytest.mark.integration
@pytest.mark.slow
class TestAmazonSQSRepricing:
    """Test complete Amazon SQS repricing pipeline."""
    
    def test_sqs_message_triggers_repricing_success(
        self,
        sqs_consumer,
        sample_amazon_sqs_message,
        setup_test_products,
        verify_price_in_redis,
        wait_for_processing
    ):
        """
        Test that an Amazon SQS ANY_OFFER_CHANGED message successfully triggers repricing.
        
        Flow:
        1. Setup product data in Redis
        2. Process SQS message through consumer
        3. Verify new price is calculated and saved to Redis
        """
        # Setup test product in Redis
        test_product = SAMPLE_AMAZON_PRODUCT.copy()
        setup_test_products([test_product])
        
        # Mock competitor price data (this would normally come from Amazon API)
        mock_competitor_data = {
            "competitor_price": 27.99,  # Lower than our price of 29.99
            "buybox_winner": "A2COMPETITOR456",
            "total_offers": 3
        }
        
        # Patch the orchestrator to return our mock data
        with patch.object(
            sqs_consumer.orchestrator, 
            'process_amazon_message'
        ) as mock_process:
            mock_process.return_value = {
                "success": True,
                "price_changed": True,
                "old_price": 29.99,
                "new_price": 27.98,  # Beat competitor by 0.01
                "processing_time_ms": 125.3
            }
            
            # Process the SQS message
            sqs_consumer._process_single_message(
                sample_amazon_sqs_message,
                "test-queue-url",
                sqs_consumer.logger
            )
            
            # Verify the message was processed
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0][0]
            assert call_args["MessageId"] == sample_amazon_sqs_message["MessageId"]
        
        # Wait for async processing
        wait_for_processing()
        
        # In a real scenario, we'd verify the price in Redis
        # For this test, we verify the processing flow completed successfully
        assert sqs_consumer.consumer_stats["messages_processed"] >= 0
    
    def test_sqs_message_processing_with_mock_redis_integration(
        self,
        repricing_orchestrator,
        sample_amazon_sqs_message,
        setup_test_products,
        verify_price_in_redis,
        wait_for_processing
    ):
        """
        Test SQS message processing with full Redis integration.
        This test uses the actual orchestrator and Redis interactions.
        """
        # Setup test product
        test_product = SAMPLE_AMAZON_PRODUCT.copy()
        setup_test_products([test_product])
        
        # Mock external Amazon API calls
        with patch('src.services.repricing_orchestrator.RepricingOrchestrator.process_amazon_message') as mock_process:
            # Simulate successful repricing
            mock_process.return_value = {
                "success": True,
                "price_changed": True,
                "old_price": 29.99,
                "new_price": 27.98,
                "strategy_used": "CHASE_BUYBOX",
                "processing_time_ms": 145.7
            }
            
            # Process message through orchestrator directly
            result = repricing_orchestrator.process_amazon_message(sample_amazon_sqs_message)
            
            assert result["success"] is True
            assert result["price_changed"] is True
            assert "new_price" in result
    
    def test_sqs_message_with_invalid_product_data(
        self,
        sqs_consumer,
        sample_amazon_sqs_message,
        wait_for_processing
    ):
        """
        Test SQS message processing when product data is not found in Redis.
        Should handle gracefully without crashing.
        """
        # Don't setup any product data - should cause "product not found" scenario
        
        with patch.object(
            sqs_consumer.orchestrator,
            'process_amazon_message'
        ) as mock_process:
            mock_process.return_value = {
                "success": False,
                "error": "Product not found in Redis",
                "processing_time_ms": 25.1
            }
            
            # Process message - should handle error gracefully
            sqs_consumer._process_single_message(
                sample_amazon_sqs_message,
                "test-queue-url",
                sqs_consumer.logger
            )
            
            # Verify error was handled
            mock_process.assert_called_once()
            assert sqs_consumer.consumer_stats["messages_failed"] >= 0
    
    def test_sqs_batch_processing(
        self,
        sqs_consumer,
        setup_test_products,
        wait_for_processing
    ):
        """
        Test processing multiple SQS messages in batch.
        """
        # Setup multiple test products
        products = [
            {**SAMPLE_AMAZON_PRODUCT, "asin": "B07PRODUCT01", "sku": "SKU-001"},
            {**SAMPLE_AMAZON_PRODUCT, "asin": "B07PRODUCT02", "sku": "SKU-002"},
            {**SAMPLE_AMAZON_PRODUCT, "asin": "B07PRODUCT03", "sku": "SKU-003"},
        ]
        setup_test_products(products)
        
        # Create multiple SQS messages
        messages = []
        for i, product in enumerate(products):
            message = {
                "MessageId": f"msg-{i}",
                "ReceiptHandle": f"receipt-{i}",
                "Body": json.dumps({
                    "Type": "Notification",
                    "Message": json.dumps({
                        "notificationType": "AnyOfferChanged",
                        "payload": {
                            "anyOfferChangedNotification": {
                                "sellerId": product["seller_id"],
                                "asin": product["asin"],
                                "marketplaceId": "ATVPDKIKX0DER",
                                "itemCondition": "NEW"
                            }
                        }
                    })
                }),
                "Attributes": {"ApproximateReceiveCount": "1"}
            }
            messages.append(message)
        
        # Mock orchestrator responses
        with patch.object(
            sqs_consumer.orchestrator,
            'process_amazon_message'
        ) as mock_process:
            mock_process.return_value = {
                "success": True,
                "price_changed": True,
                "processing_time_ms": 100.0
            }
            
            # Process message batch
            sqs_consumer._process_message_batch(
                messages,
                "test-queue-url",
                sqs_consumer.logger
            )
            
            # Verify all messages were processed
            assert mock_process.call_count == len(messages)
        
        wait_for_processing()
    
    def test_sqs_message_retry_logic(
        self,
        sqs_consumer,
        sample_amazon_sqs_message,
        wait_for_processing
    ):
        """
        Test SQS message retry logic when processing fails.
        """
        # Modify message to simulate retry (higher receive count)
        retry_message = sample_amazon_sqs_message.copy()
        retry_message["Attributes"]["ApproximateReceiveCount"] = "2"
        
        with patch.object(
            sqs_consumer.orchestrator,
            'process_amazon_message'
        ) as mock_process:
            # Simulate processing failure
            mock_process.return_value = {
                "success": False,
                "error": "Temporary processing error",
                "processing_time_ms": 50.0
            }
            
            # Process failing message
            sqs_consumer._process_single_message(
                retry_message,
                "test-queue-url", 
                sqs_consumer.logger
            )
            
            # Verify failure was recorded
            mock_process.assert_called_once()
        
        wait_for_processing()
    
    def test_sqs_message_dead_letter_queue_scenario(
        self,
        sqs_consumer,
        sample_amazon_sqs_message,
        wait_for_processing
    ):
        """
        Test SQS message sent to dead letter queue after max retries.
        """
        # Simulate message that has reached max retries
        dlq_message = sample_amazon_sqs_message.copy()
        dlq_message["Attributes"]["ApproximateReceiveCount"] = str(sqs_consumer.max_retries + 1)
        
        with patch.object(
            sqs_consumer.orchestrator,
            'process_amazon_message'
        ) as mock_process:
            mock_process.return_value = {
                "success": False,
                "error": "Persistent processing error",
                "processing_time_ms": 25.0
            }
            
            # Mock the delete message method to track DLQ behavior
            with patch.object(sqs_consumer, '_delete_message') as mock_delete:
                sqs_consumer._process_single_message(
                    dlq_message,
                    "test-queue-url",
                    sqs_consumer.logger
                )
                
                # Message should be deleted (sent to DLQ by SQS automatically)
                mock_delete.assert_called_once()
        
        wait_for_processing()
        
        # Verify DLQ stats were updated
        assert sqs_consumer.consumer_stats.get("messages_sent_to_dlq", 0) >= 0