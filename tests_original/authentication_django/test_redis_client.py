import pytest
from unittest.mock import Mock, patch
from project.ah_authentication.redis_client import (
    RedisClient,
    RedisCacheFactory,
    PickleSerializer,
    CacheInterface,
)


class TestRedisClient:

    def test_implements_cache_interface(self):
        """Test that RedisClient implements CacheInterface."""
        mock_redis = Mock()
        client = RedisClient(mock_redis)
        assert isinstance(client, CacheInterface)

    def test_initialization_with_dependencies(self):
        """Test RedisClient initialization with injected dependencies."""
        mock_redis = Mock()
        mock_serializer = Mock()

        client = RedisClient(mock_redis, mock_serializer)

        assert client._redis_client == mock_redis
        assert client._serializer == mock_serializer



    def test_get_method(self):
        """Test get method delegates to Redis client."""
        mock_redis = Mock()
        mock_redis.get.return_value = b"test_value"

        client = RedisClient(mock_redis)
        result = client.get("test_key")

        mock_redis.get.assert_called_once_with("test_key")
        assert result == b"test_value"

    def test_set_method(self):
        """Test set method with JSON serialization."""
        mock_redis = Mock()
        client = RedisClient(mock_redis)

        client.set("test_key", {"data": "value"})

        mock_redis.set.assert_called_once_with("test_key", '{"data": "value"}')

    def test_set_method_with_expiration(self):
        """Test set method with expiration."""
        mock_redis = Mock()
        client = RedisClient(mock_redis)

        client.set("test_key", {"data": "value"}, expiration=300)

        mock_redis.setex.assert_called_once_with("test_key", 300, '{"data": "value"}')

    def test_hset_regular_key(self):
        """Test hset method with regular key uses JSON serialization."""
        mock_redis = Mock()
        client = RedisClient(mock_redis)

        client.hset("test_key", "field", {"data": "value"})

        mock_redis.hset.assert_called_once_with(
            "test_key", "field", '{"data": "value"}'
        )

    def test_hset_account_key(self):
        """Test hset method with account key uses pickle serialization."""
        mock_redis = Mock()
        mock_serializer = Mock()
        mock_serializer.dumps.return_value = b"pickled_data"

        client = RedisClient(mock_redis, mock_serializer)

        client.hset("account.123", "field", {"data": "value"})

        mock_serializer.dumps.assert_called_once_with({"data": "value"})
        mock_redis.hset.assert_called_once_with("account.123", "field", b"pickled_data")

    def test_hget_method(self):
        """Test hget method with JSON deserialization."""
        mock_redis = Mock()
        mock_redis.hget.return_value = b'{"data": "value"}'

        client = RedisClient(mock_redis)
        result = client.hget("test_key", "field")

        mock_redis.hget.assert_called_once_with("test_key", "field")
        assert result == {"data": "value"}

    def test_hget_method_none_value(self):
        """Test hget method returns None for missing values."""
        mock_redis = Mock()
        mock_redis.hget.return_value = None

        client = RedisClient(mock_redis)
        result = client.hget("test_key", "field")

        assert result is None

    def test_delete_key_method(self):
        """Test delete_key method."""
        mock_redis = Mock()
        mock_redis.delete.return_value = 1

        client = RedisClient(mock_redis)
        result = client.delete_key("test_key")

        mock_redis.delete.assert_called_once_with("test_key")
        assert result == 1

    def test_rpush_method(self):
        """Test rpush method with JSON serialization."""
        mock_redis = Mock()
        client = RedisClient(mock_redis)

        client.rpush("test_list", {"data": "value"})

        mock_redis.rpush.assert_called_once_with("test_list", '{"data": "value"}')

    def test_lrange_method(self):
        """Test lrange method with JSON deserialization."""
        mock_redis = Mock()
        mock_redis.lrange.return_value = [b'{"data": "value1"}', b'{"data": "value2"}']

        client = RedisClient(mock_redis)
        result = client.lrange("test_list")

        mock_redis.lrange.assert_called_once_with("test_list", 0, -1)
        assert result == [{"data": "value1"}, {"data": "value2"}]

    def test_hgetall_account_method(self):
        """Test hgetall_account method with pickle deserialization."""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {
            b"field1": b"pickled_data1",
            b"field2": b"pickled_data2",
        }

        client = RedisClient(mock_redis)

        # Mock pickle.loads directly since we're testing the method behavior
        with patch("pickle.loads") as mock_pickle_loads:
            mock_pickle_loads.side_effect = lambda x: f"unpickled_{x.decode()}"

            result = client.hgetall_account("account.123")

            assert result == {
                "field1": "unpickled_pickled_data1",
                "field2": "unpickled_pickled_data2",
            }

    def test_pipeline_method(self):
        """Test pipeline method."""
        mock_redis = Mock()
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline

        client = RedisClient(mock_redis)
        result = client.pipeline()

        mock_redis.pipeline.assert_called_once()
        assert result == mock_pipeline


class TestRedisCacheFactory:


    def test_create_cache_with_client(self):
        """Test factory creates cache with provided Redis client."""
        mock_redis = Mock()

        cache = RedisCacheFactory.create_cache(mock_redis)

        assert isinstance(cache, RedisClient)
        assert cache._redis_client == mock_redis

    def test_create_test_cache(self):
        """Test factory creates test cache with mock client."""
        mock_redis = Mock()

        cache = RedisCacheFactory.create_test_cache(mock_redis)

        assert isinstance(cache, RedisClient)
        assert cache._redis_client == mock_redis
