import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from project.settings import strtobool
from any_offer_consumer import (
    get_sqs_client,
    consume_anyoffer_notification,
    produce_offer_notification_and_delete_message,
    send_message_to_kafka,
    delete_messages_from_sqs,
    receive_messages_from_sqs,
)


class TestStrtobool:
    def test_strtobool_true_values(self):
        true_values = ["y", "yes", "t", "true", "on", "1", "Y", "YES", "True", "ON"]
        for val in true_values:
            assert strtobool(val) == True

    def test_strtobool_false_values(self):
        false_values = ["n", "no", "f", "false", "off", "0", "N", "NO", "False", "OFF"]
        for val in false_values:
            assert strtobool(val) == False

    def test_strtobool_invalid_values(self):
        invalid_values = ["maybe", "unknown", "invalid", ""]
        for val in invalid_values:
            with pytest.raises(
                ValueError, match=f"invalid truth value {val.lower()!r}"
            ):
                strtobool(val)


class TestSQSClient:
    @patch("any_offer_consumer.boto3.client")
    @patch("any_offer_consumer.QUEUE_REGION", "us-east-1")
    def test_get_sqs_client(self, mock_boto_client, settings):
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Use Django settings override
        settings.AWS_ACCESS_KEY = "test_access_key"
        settings.AWS_SECRET_KEY = "test_secret_key"

        result = get_sqs_client()

        mock_boto_client.assert_called_once_with(
            "sqs",
            region_name="us-east-1",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
        )
        assert result == mock_client


class TestReceiveMessagesFromSQS:
    def test_receive_messages_from_sqs_with_messages(self):
        mock_sqs = Mock()
        mock_sqs.receive_message.return_value = {
            "Messages": [{"Body": "test", "ReceiptHandle": "handle1"}]
        }

        result = receive_messages_from_sqs(mock_sqs, 10, "test-queue-url")

        mock_sqs.receive_message.assert_called_once_with(
            QueueUrl="test-queue-url", MaxNumberOfMessages=10, VisibilityTimeout=100
        )
        assert result == [{"Body": "test", "ReceiptHandle": "handle1"}]

    def test_receive_messages_from_sqs_no_messages(self):
        mock_sqs = Mock()
        mock_sqs.receive_message.return_value = {}

        result = receive_messages_from_sqs(mock_sqs, 10, "test-queue-url")

        assert result == []


class TestDeleteMessagesFromSQS:
    def test_delete_messages_from_sqs(self):
        mock_sqs = Mock()
        receipt_handles = ["handle1", "handle2", "handle3"]

        delete_messages_from_sqs(mock_sqs, receipt_handles, "test-queue-url")

        assert mock_sqs.delete_message.call_count == 3
        expected_calls = [
            {"QueueUrl": "test-queue-url", "ReceiptHandle": "handle1"},
            {"QueueUrl": "test-queue-url", "ReceiptHandle": "handle2"},
            {"QueueUrl": "test-queue-url", "ReceiptHandle": "handle3"},
        ]

        for i, call in enumerate(mock_sqs.delete_message.call_args_list):
            assert call.kwargs == expected_calls[i]


class TestSendMessageToKafka:
    @patch("any_offer_consumer.Producer")
    @patch("any_offer_consumer.HOST", "localhost")
    @patch("any_offer_consumer.KAFKA_PORT", "9092")
    def test_send_message_to_kafka(self, mock_producer_class):
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        test_message = {"key": "value", "data": [1, 2, 3]}
        send_message_to_kafka("test-topic", test_message)

        mock_producer_class.assert_called_once_with(
            {"bootstrap.servers": "localhost:9092"}
        )
        mock_producer.produce.assert_called_once_with(
            "test-topic", value=json.dumps(test_message)
        )
        mock_producer.flush.assert_called_once()


class TestProduceOfferNotificationAndDeleteMessage:
    @patch("any_offer_consumer.send_message_to_kafka")
    @patch("any_offer_consumer.delete_messages_from_sqs")
    @patch("any_offer_consumer.AH_REPRICER_TOPIC", "repricer-topic")
    @patch("any_offer_consumer.ANY_OFFER_NOTIFICATOION_QUEUE_URL", "test-queue-url")
    def test_produce_offer_notification_with_payload(
        self, mock_delete_messages, mock_send_kafka
    ):
        mock_sqs = Mock()
        receipt_handles = ["handle1", "handle2"]
        any_offer_payload = [{"offer": "data1"}, {"offer": "data2"}]

        produce_offer_notification_and_delete_message(
            mock_sqs, receipt_handles, any_offer_payload
        )

        mock_send_kafka.assert_called_once_with(
            "repricer-topic", {"responses": any_offer_payload}
        )
        mock_delete_messages.assert_called_once_with(
            mock_sqs, receipt_handles, "test-queue-url"
        )

    @patch("any_offer_consumer.send_message_to_kafka")
    @patch("any_offer_consumer.delete_messages_from_sqs")
    def test_produce_offer_notification_empty_payload(
        self, mock_delete_messages, mock_send_kafka
    ):
        mock_sqs = Mock()
        receipt_handles = ["handle1"]
        any_offer_payload = []

        produce_offer_notification_and_delete_message(
            mock_sqs, receipt_handles, any_offer_payload
        )

        mock_send_kafka.assert_not_called()
        mock_delete_messages.assert_not_called()


class TestConsumeAnyofferNotification:
    @patch("any_offer_consumer.time.sleep", side_effect=KeyboardInterrupt)
    @patch("any_offer_consumer.print_log")
    @patch("any_offer_consumer.get_sqs_client")
    @patch("any_offer_consumer.receive_messages_from_sqs")
    @patch("any_offer_consumer.produce_offer_notification_and_delete_message")
    @patch("any_offer_consumer.ProcessAnyOfferChange")
    @patch("any_offer_consumer.ANY_OFFER_NOTIFICATOION_QUEUE_URL", "test-queue-url")
    @patch("any_offer_consumer.MAX_CONSUME_MESSAGES", 10)
    def test_consume_anyoffer_notification_with_messages(
        self,
        mock_process_class,
        mock_produce_and_delete,
        mock_receive_messages,
        mock_get_sqs,
        mock_print_log,
        mock_sleep,
    ):
        # Setup mocks
        mock_sqs = Mock()
        mock_get_sqs.return_value = mock_sqs

        # Mock messages with ANY_OFFER_CHANGED notification
        test_body = {
            "notificationType": "ANY_OFFER_CHANGED",
            "payload": {"data": "test"},
        }
        mock_messages = [
            {"ReceiptHandle": "handle1", "Body": json.dumps(test_body)},
            {"ReceiptHandle": "handle2", "Body": json.dumps(test_body)},
        ]

        # Configure receive_messages to return messages once, then empty to trigger sleep
        call_count = 0

        def side_effect_func(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_messages
            return []  # This will trigger sleep and then KeyboardInterrupt

        mock_receive_messages.side_effect = side_effect_func

        # Mock ProcessAnyOfferChange
        mock_processor = Mock()
        mock_processor.process_offer_notification.return_value = {"processed": "data"}
        mock_process_class.return_value = mock_processor

        with pytest.raises(KeyboardInterrupt):
            consume_anyoffer_notification()

        # Verify SQS client was created
        mock_get_sqs.assert_called_once()

        # Verify messages were received at least once
        assert mock_receive_messages.call_count >= 1
        mock_receive_messages.assert_any_call(mock_sqs, 10, "test-queue-url")

        # Verify ProcessAnyOfferChange was called for each message
        assert mock_process_class.call_count == 2

        # Verify produce_offer_notification_and_delete_message was called
        mock_produce_and_delete.assert_called_once()
        args = mock_produce_and_delete.call_args[0]
        assert args[0] == mock_sqs  # sqs client
        assert args[1] == ["handle1", "handle2"]  # receipt handles
        assert len(args[2]) == 2  # processed payloads

    @patch("any_offer_consumer.time.sleep", side_effect=KeyboardInterrupt)
    @patch("any_offer_consumer.print_log")
    @patch("any_offer_consumer.get_sqs_client")
    @patch("any_offer_consumer.receive_messages_from_sqs")
    def test_consume_anyoffer_notification_no_messages_triggers_sleep(
        self, mock_receive_messages, mock_get_sqs, mock_print_log, mock_sleep
    ):
        mock_sqs = Mock()
        mock_get_sqs.return_value = mock_sqs

        # Always return empty messages to trigger sleep immediately
        mock_receive_messages.return_value = []

        with pytest.raises(KeyboardInterrupt):
            consume_anyoffer_notification()

        # Verify sleep was called when no messages
        mock_sleep.assert_called_once_with(2)

    @patch("any_offer_consumer.time.sleep", side_effect=KeyboardInterrupt)
    @patch("any_offer_consumer.print_log")
    @patch("any_offer_consumer.get_sqs_client")
    @patch("any_offer_consumer.receive_messages_from_sqs")
    @patch("any_offer_consumer.ProcessAnyOfferChange")
    def test_consume_anyoffer_notification_ignores_other_notification_types(
        self,
        mock_process_class,
        mock_receive_messages,
        mock_get_sqs,
        mock_print_log,
        mock_sleep,
    ):
        mock_sqs = Mock()
        mock_get_sqs.return_value = mock_sqs

        # Mock message with different notification type
        test_body = {
            "notificationType": "DIFFERENT_NOTIFICATION",
            "payload": {"data": "test"},
        }
        mock_messages = [{"ReceiptHandle": "handle1", "Body": json.dumps(test_body)}]

        call_count = 0

        def side_effect_func(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_messages
            return []  # This will trigger sleep and then KeyboardInterrupt

        mock_receive_messages.side_effect = side_effect_func

        with pytest.raises(KeyboardInterrupt):
            consume_anyoffer_notification()

        # Verify ProcessAnyOfferChange was not called for different notification type
        mock_process_class.assert_not_called()

    @patch("any_offer_consumer.AH_REPRICER_TOPIC", "test-repricer-topic")
    @patch("any_offer_consumer.time.sleep", side_effect=KeyboardInterrupt)
    @patch("any_offer_consumer.print_log")
    @patch("any_offer_consumer.get_sqs_client")
    @patch("any_offer_consumer.receive_messages_from_sqs")
    @patch("any_offer_consumer.ProcessAnyOfferChange")
    @patch("any_offer_consumer.send_message_to_kafka")
    @patch("any_offer_consumer.delete_messages_from_sqs")
    def test_consume_anyoffer_notification_handles_NotificationType_key(
        self,
        mock_delete_messages,
        mock_send_kafka,
        mock_process_class,
        mock_receive_messages,
        mock_get_sqs,
        mock_print_log,
        mock_sleep,
    ):
        mock_sqs = Mock()
        mock_get_sqs.return_value = mock_sqs

        # Mock message with capital NotificationType key
        test_body = {
            "NotificationType": "ANY_OFFER_CHANGED",
            "payload": {"data": "test"},
        }
        mock_messages = [{"ReceiptHandle": "handle1", "Body": json.dumps(test_body)}]

        call_count = 0

        def side_effect_func(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_messages
            return []  # This will trigger sleep and then KeyboardInterrupt

        mock_receive_messages.side_effect = side_effect_func

        mock_processor = Mock()
        mock_processor.process_offer_notification.return_value = {"processed": "data"}
        mock_process_class.return_value = mock_processor

        with pytest.raises(KeyboardInterrupt):
            consume_anyoffer_notification()

        # Verify ProcessAnyOfferChange was called even with capital NotificationType
        mock_process_class.assert_called_once()
        # Verify Kafka message was sent
        mock_send_kafka.assert_called_once()
        # Verify SQS messages were deleted
        mock_delete_messages.assert_called_once()
