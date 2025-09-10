import pytest
from datetime import time
from project.ah_authentication.models import UserAccount, PriceReset


@pytest.mark.django_db
class TestUserAccount:

    def test_create_user_account(self, sample_user_account_data):
        account = UserAccount.objects.create(**sample_user_account_data)

        assert account.user_id == sample_user_account_data["user_id"]
        assert account.seller_id == sample_user_account_data["seller_id"]
        assert account.enabled == sample_user_account_data["enabled"]
        assert account.repricer_enabled == sample_user_account_data["repricer_enabled"]
        assert account.marketplace_type == sample_user_account_data["marketplace_type"]
        assert account.status == "ACTIVE"  # default value
        assert account.is_notifications_active == False  # default value

    def test_user_account_str_method(self, sample_user_account_data):
        account = UserAccount.objects.create(**sample_user_account_data)
        assert str(account) == sample_user_account_data["seller_id"]

    def test_credentials_property(self, sample_user_account_data):
        from unittest.mock import patch

        with patch(
            "project.settings.CREDENTIALS",
            {"lwa_app_id": "test", "lwa_client_secret": "secret"},
        ):
            account = UserAccount.objects.create(**sample_user_account_data)
            credentials = account.credentials

            assert credentials["lwa_app_id"] == "test"
            assert credentials["lwa_client_secret"] == "secret"
            assert (
                credentials["refresh_token"]
                == sample_user_account_data["refresh_token"]
            )

    def test_unique_together_constraint(self, sample_user_account_data):
        UserAccount.objects.create(**sample_user_account_data)

        # Creating another account with same refresh_token and seller_id should fail
        with pytest.raises(Exception):
            UserAccount.objects.create(**sample_user_account_data)


@pytest.mark.django_db
class TestPriceReset:

    def test_create_price_reset(self, sample_price_reset_data):
        price_reset = PriceReset.objects.create(
            price_reset_id=sample_price_reset_data["price_reset_id"],
            price_reset_time=time.fromisoformat(
                sample_price_reset_data["price_reset_time"]
            ),
            price_resume_time=time.fromisoformat(
                sample_price_reset_data["price_resume_time"]
            ),
            price_reset_enabled=sample_price_reset_data["price_reset_enabled"],
            product_condition=sample_price_reset_data["product_condition"],
        )

        assert price_reset.price_reset_id == sample_price_reset_data["price_reset_id"]
        assert (
            price_reset.price_reset_enabled
            == sample_price_reset_data["price_reset_enabled"]
        )
        assert price_reset.price_reset_active == False  # default value
        assert (
            price_reset.product_condition
            == sample_price_reset_data["product_condition"]
        )

    def test_price_reset_with_user_account(
        self, sample_user_account_data, sample_price_reset_data
    ):
        price_reset = PriceReset.objects.create(
            price_reset_id=sample_price_reset_data["price_reset_id"],
            price_reset_time=time.fromisoformat(
                sample_price_reset_data["price_reset_time"]
            ),
            price_resume_time=time.fromisoformat(
                sample_price_reset_data["price_resume_time"]
            ),
            price_reset_enabled=sample_price_reset_data["price_reset_enabled"],
            product_condition=sample_price_reset_data["product_condition"],
        )

        sample_user_account_data["price_reset"] = price_reset
        account = UserAccount.objects.create(**sample_user_account_data)

        assert account.price_reset == price_reset
        assert (
            account.price_reset.price_reset_id
            == sample_price_reset_data["price_reset_id"]
        )