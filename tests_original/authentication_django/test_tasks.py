import pytest
from unittest.mock import Mock, patch

from project.ah_authentication.models import UserAccount
from project.ah_authentication.tasks import (
    verify_user_credentials,
    get_active_user_accounts,
    subscribe_user_notification,
    unsubscribe_notification,
    process_user_account,
    trigger_feed_submission,
    get_current_hour_of_user_marketplace,
)


@pytest.mark.django_db
class TestTasks:

    @patch("project.ah_authentication.services.user_account_service.Reports")
    def test_verify_user_credentials_success(
        self, mock_reports_class, sample_user_account_data
    ):
        mock_reports_instance = Mock()
        mock_reports_class.return_value = mock_reports_instance
        mock_reports_instance.get_reports.return_value = {"reportId": "123"}

        account = UserAccount.objects.create(**sample_user_account_data)
        verify_user_credentials(accounts=[account])

        account.refresh_from_db()
        assert account.status == "ACTIVE"

    @patch("project.ah_authentication.services.user_account_service.Reports")
    def test_verify_user_credentials_failure(
        self, mock_reports_class, sample_user_account_data
    ):
        mock_reports_instance = Mock()
        mock_reports_class.return_value = mock_reports_instance
        mock_reports_instance.get_reports.side_effect = Exception("Invalid credentials")

        account = UserAccount.objects.create(**sample_user_account_data)
        verify_user_credentials(accounts=[account])

        account.refresh_from_db()
        assert account.status == "INACTIVE"

    def test_get_active_user_accounts(self, sample_user_account_data):
        account = UserAccount.objects.create(**sample_user_account_data)
        accounts = get_active_user_accounts()

        assert len(accounts) == 1
        assert accounts[0]["seller_id"] == sample_user_account_data["seller_id"]
        assert (
            accounts[0]["marketplace_type"]
            == sample_user_account_data["marketplace_type"]
        )
        assert accounts[0]["refresh_token"] == sample_user_account_data["refresh_token"]
        assert accounts[0]["user_id"] == sample_user_account_data["user_id"]

    def test_get_active_user_accounts_filtered(self, sample_user_account_data):
        # Create active account
        UserAccount.objects.create(**sample_user_account_data)

        # Create inactive account
        inactive_data = sample_user_account_data.copy()
        inactive_data["seller_id"] = "inactive_seller"
        inactive_data["enabled"] = False
        UserAccount.objects.create(**inactive_data)

        accounts = get_active_user_accounts()

        # Should only return active account
        assert len(accounts) == 1
        assert accounts[0]["seller_id"] == sample_user_account_data["seller_id"]

    @patch("project.ah_authentication.services.notification_service.Notifications")
    def test_subscribe_user_notification_success(
        self, mock_notifications_class, sample_user_account_data
    ):
        mock_notifications_instance = Mock()
        mock_notifications_class.return_value = mock_notifications_instance

        mock_subscription = Mock()
        mock_subscription.payload = {
            "subscriptionId": "sub_123",
            "destinationId": "dest_456",
        }
        mock_notifications_instance.create_subscription.return_value = mock_subscription

        account = UserAccount.objects.create(**sample_user_account_data)

        with patch(
            "helpers.constants.ANY_OFFER_CHANGED_DESTINATIONS",
            {"us-east-1": "dest_123"},
        ):
            with patch(
                "helpers.constants.FEED_PROCESSING_FINISHED_DESTINATIONS",
                {"us-east-1": "dest_456"},
            ):
                result = subscribe_user_notification(account)

        account.refresh_from_db()
        assert account.is_notifications_active == True
        assert result is not None

    @patch("project.ah_authentication.services.notification_service.NotificationService.get_developer_access_token")
    @patch("project.ah_authentication.services.notification_service.NotificationService.delete_subscription")
    def test_unsubscribe_notification(
        self, mock_delete_sub, mock_get_token, sample_user_account_data
    ):
        mock_get_token.return_value = "access_token_123"
        mock_delete_sub.return_value = True

        account_data = sample_user_account_data.copy()
        account_data.update(
            {
                "anyoffer_changed_subscription_id": "sub_123",
                "feed_ready_notication_subscription_id": "sub_456",
            }
        )

        account = UserAccount.objects.create(**account_data)
        unsubscribe_notification(account)

        account.refresh_from_db()
        assert account.is_notifications_active == False
        assert account.anyoffer_changed_subscription_id == ""
        assert account.feed_ready_notication_subscription_id == ""

    def test_trigger_feed_submission_single_task(self):
        with patch("project.ah_authentication.services.queue_service.QueueService.prepare_message_for_queue") as mock_prepare:
            with patch("project.ah_authentication.services.queue_service.QueueService.push_to_redis_queue") as mock_push:
                mock_prepare.return_value = {"task": "test_task"}

                trigger_feed_submission("single_task", {"data": "test"})

                mock_prepare.assert_called_once_with("single_task", {"data": "test"})
                mock_push.assert_called_once_with("feeds", {"task": "test_task"})

    @patch("project.ah_authentication.services.user_account_service.UserAccountService.get_active_user_accounts")
    def test_trigger_feed_submission_feed_task(self, mock_get_accounts):
        mock_get_accounts.return_value = [
            {"seller_id": "seller1"},
            {"seller_id": "seller2"},
        ]

        with patch("project.ah_authentication.services.queue_service.QueueService.prepare_message_for_queue") as mock_prepare:
            with patch("project.ah_authentication.services.queue_service.QueueService.push_to_redis_queue") as mock_push:
                mock_prepare.return_value = {"task": "feed_task"}

                trigger_feed_submission("feed_submission_task", {})

                assert mock_prepare.call_count == 2
                assert mock_push.call_count == 2

    def test_get_current_hour_of_user_marketplace(self):
        with patch("project.ah_authentication.services.price_reset_service.timezone.now") as mock_now:
            with patch("project.ah_authentication.services.price_reset_service.pytz.timezone") as mock_timezone:
                mock_datetime = Mock()
                mock_datetime.astimezone.return_value.hour = 15
                mock_now.return_value = mock_datetime

                mock_tz = Mock()
                mock_timezone.return_value = mock_tz

                hour = get_current_hour_of_user_marketplace("US")

                assert hour == 15

    @patch("project.ah_authentication.services.redis_service.RedisService.retrieve_seller_ids_against_asins")
    @patch("project.ah_authentication.services.user_account_service.UserAccountService.update_or_create_user_account")
    @patch("project.ah_authentication.services.user_account_service.UserAccountService.verify_user_credentials")
    def test_process_user_account(
        self, mock_verify, mock_update, mock_retrieve, sample_user_account_data
    ):
        mock_retrieve.return_value = ["seller1", "seller2"]
        mock_account = Mock()
        mock_account.status = "ACTIVE"
        mock_update.return_value = mock_account

        with patch(
            "project.ah_authentication.tasks._process_active_user_account"
        ) as mock_process:
            process_user_account([sample_user_account_data])

            mock_update.assert_called_once_with(sample_user_account_data)
            mock_verify.assert_called_once()
            # Check that process was called with correct account and that sellers list contains expected items
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            assert call_args[0] == mock_account
            assert set(call_args[1]) == {"seller1", "seller2"}