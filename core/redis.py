"""Redis client configuration for PulseStream."""

import redis
from typing import Optional
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    global _redis_client
    
    if _redis_client is None:
        try:
            # Parse Redis URL
            redis_url = str(settings.redis_url)
            
            # Create Redis client
            _redis_client = redis.from_url(
                redis_url,
                decode_responses=True,  # Decode responses to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=20
            )
            
            # Test connection
            _redis_client.ping()
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    
    return _redis_client


def get_redis_client_sync() -> redis.Redis:
    """Get synchronous Redis client instance."""
    try:
        # Parse Redis URL
        redis_url = str(settings.redis_url)
        
        # Create Redis client
        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=20
        )
        
        # Test connection
        client.ping()
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize sync Redis client: {e}")
        raise


async def close_redis_client():
    """Close Redis client connection."""
    global _redis_client
    
    if _redis_client:
        try:
            _redis_client.close()
            _redis_client = None
            logger.info("Redis client connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")


def get_redis_health() -> dict:
    """Get Redis health status."""
    try:
        client = get_redis_client()
        
        # Test basic operations
        test_key = "health_check_test"
        test_value = "ok"
        
        # Set and get test value
        client.set(test_key, test_value, ex=10)
        retrieved_value = client.get(test_key)
        
        # Clean up
        client.delete(test_key)
        
        if retrieved_value == test_value:
            return {
                "status": "healthy",
                "message": "Redis is responding correctly",
                "timestamp": "now"
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Redis data integrity check failed",
                "timestamp": "now"
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Redis health check failed: {str(e)}",
            "timestamp": "now"
        }


class RedisManager:
    """Redis connection manager for the application."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.is_connected = False
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = get_redis_client()
            self.is_connected = True
            logger.info("Redis manager connected successfully")
        except Exception as e:
            logger.error(f"Redis manager connection failed: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            try:
                self.client.close()
                self.client = None
                self.is_connected = False
                logger.info("Redis manager disconnected")
            except Exception as e:
                logger.error(f"Redis manager disconnection error: {e}")
    
    def get_client(self) -> redis.Redis:
        """Get Redis client."""
        if not self.is_connected or not self.client:
            raise RuntimeError("Redis manager not connected")
        return self.client
    
    async def health_check(self) -> dict:
        """Perform Redis health check."""
        if not self.is_connected:
            return {
                "status": "disconnected",
                "message": "Redis manager not connected",
                "timestamp": "now"
            }
        
        try:
            return get_redis_health()
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "timestamp": "now"
            }


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis_manager() -> RedisManager:
    """Get Redis manager instance."""
    return redis_manager
