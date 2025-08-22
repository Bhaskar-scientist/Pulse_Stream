#!/usr/bin/env python3
"""Test Redis connectivity."""

from core.redis import get_redis_client

def test_redis_connection():
    """Test Redis connection."""
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

if __name__ == "__main__":
    test_redis_connection()
