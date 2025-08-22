#!/usr/bin/env python3
"""Test database connectivity."""

import asyncio
from core.database import get_async_session

async def test_database_connection():
    """Test database connection."""
    try:
        async for session in get_async_session():
            print("✅ Database connection successful")
            await session.close()
            break
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_database_connection())
