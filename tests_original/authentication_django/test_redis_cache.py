import pytest
from unittest.mock import Mock, patch
from project.ah_authentication.redis_cache import RedisCache, PickleSerializer


class TestPickleSerializer:

    def test_pickle_serializer_dumps_loads(self):
        serializer = PickleSerializer()
        test_data = {"key": "value", "number": 123}

        serialized = serializer.dumps(test_data)
        deserialized = serializer.loads(serialized)

        assert deserialized == test_data

    def test_pickle_serializer_with_protocol(self):
        serializer = PickleSerializer(protocol=2)
        assert serializer.protocol == 2


class TestRedisCache:

    @patch("project.ah_authentication.redis_cache.redis.Redis")
    def test_singleton_pattern(self, mock_redis_class):
        mock_redis_instance = Mock()
        mock_redis_class.return_value = mock_redis_instance

        # Reset singleton before test
        RedisCache._instance = None

        cache1 = RedisCache()
        cache2 = RedisCache()

        assert cache1 is cache2
        assert mock_redis_class.call_count == 1

    @patch("project.ah_authentication.redis_cache.redis.Redis")
    def test_debug_mode_initialization(self, mock_redis_class, settings):
        mock_redis_instance = Mock()
        mock_redis_class.return_value = mock_redis_instance
        
        # Use Django settings override
        settings.DEBUG = True

        # Reset singleton
        RedisCache._instance = None
        cache = RedisCache()

        mock_redis_class.assert_called_with(host="localhost", port=6379)

    @patch("project.ah_authentication.redis_cache.redis.Redis")
    def test_production_mode_initialization(self, mock_redis_class, settings):
        mock_redis_instance = Mock()
        mock_redis_class.return_value = mock_redis_instance
        
        # Use Django settings override
        settings.DEBUG = False
        settings.HOST = "prod-host"
        settings.REDIS_PORT = "6380"
        settings.REDIS_PASSWORD = "secret"

        # Reset singleton
        RedisCache._instance = None
        cache = RedisCache()

        mock_redis_class.assert_called_with(
            host="prod-host", port="6380", password="secret"
        )

    def test_get_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis
        mock_redis.get.return_value = b"test_value"

        result = cache.get("test_key")

        mock_redis.get.assert_called_once_with("test_key")
        assert result == b"test_value"

    def test_set_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis

        cache.set("test_key", {"data": "value"})

        mock_redis.set.assert_called_once_with("test_key", '{"data": "value"}')

    def test_set_method_with_expiration(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis

        cache.set("test_key", {"data": "value"}, expiration=300)

        mock_redis.setex.assert_called_once_with("test_key", 300, '{"data": "value"}')

    def test_hset_method_regular_key(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis

        cache.hset("test_key", "field", {"data": "value"})

        mock_redis.hset.assert_called_once_with(
            "test_key", "field", '{"data": "value"}'
        )

    def test_hset_method_account_key(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis

        cache.hset("account.123", "field", {"data": "value"})

        # Should use pickle serializer for account keys
        mock_redis.hset.assert_called_once()
        args = mock_redis.hset.call_args[0]
        assert args[0] == "account.123"
        assert args[1] == "field"
        # The value should be pickled, not JSON
        assert isinstance(args[2], bytes)

    def test_hget_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis
        mock_redis.hget.return_value = b'{"data": "value"}'

        result = cache.hget("test_key", "field")

        mock_redis.hget.assert_called_once_with("test_key", "field")
        assert result == {"data": "value"}

    def test_hget_method_none_value(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis
        mock_redis.hget.return_value = None

        result = cache.hget("test_key", "field")

        assert result is None

    def test_delete_key_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis
        mock_redis.delete.return_value = 1

        result = cache.delete_key("test_key")

        mock_redis.delete.assert_called_once_with("test_key")
        assert result == 1

    def test_rpush_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis

        cache.rpush("test_list", {"data": "value"})

        mock_redis.rpush.assert_called_once_with("test_list", '{"data": "value"}')

    def test_lrange_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis
        mock_redis.lrange.return_value = [b'{"data": "value1"}', b'{"data": "value2"}']

        result = cache.lrange("test_list")

        mock_redis.lrange.assert_called_once_with("test_list", 0, -1)
        assert result == [{"data": "value1"}, {"data": "value2"}]

    def test_scan_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis
        mock_redis.scan.return_value = (0, [b"key1", b"key2"])

        cursor, keys = cache.scan(0, "pattern*", 100, "hash")

        mock_redis.scan.assert_called_once_with(0, "pattern*", 100, "hash")
        assert cursor == 0
        assert keys == [b"key1", b"key2"]

    def test_match_pattern_method(self, mock_redis):
        cache = RedisCache()
        cache._redis_client = mock_redis
        mock_redis.keys.return_value = [b"key1", b"key2"]

        result = cache.match_pattern("pattern*")

        mock_redis.keys.assert_called_once_with("pattern*")
        assert result == [b"key1", b"key2"]
