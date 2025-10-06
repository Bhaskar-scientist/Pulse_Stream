#!/usr/bin/env python3
"""Test script for Alembic auto-generation when database is available."""

import subprocess
import sys
from pathlib import Path

from core.logging import configure_logging, get_logger

# Configure logging
configure_logging("DEBUG", "console")
logger = get_logger(__name__)


def test_database_connection():
    """Test if database is available."""
    try:
        import psycopg2
        from core.config import settings
        
        # Parse database URL
        db_url = str(settings.database_url)
        logger.info(f"Testing connection to: {db_url}")
        
        # Try to connect
        conn = psycopg2.connect(db_url)
        conn.close()
        logger.info("✅ Database connection successful")
        return True
        
    except Exception as e:
        logger.warning(f"❌ Database connection failed: {e}")
        return False


def backup_current_env():
    """Backup current alembic env.py."""
    env_path = Path("alembic/env.py")
    backup_path = Path("alembic/env_backup.py")
    
    if env_path.exists():
        env_path.rename(backup_path)
        logger.info("✅ Backed up current env.py")
        return True
    return False


def restore_env():
    """Restore original env.py."""
    backup_path = Path("alembic/env_backup.py")
    env_path = Path("alembic/env.py")
    
    if backup_path.exists():
        backup_path.rename(env_path)
        logger.info("✅ Restored original env.py")


def use_fixed_env():
    """Use the fixed env configuration."""
    fixed_path = Path("alembic/env_fixed.py")
    env_path = Path("alembic/env.py")
    
    if fixed_path.exists():
        # Copy fixed env to env.py
        with open(fixed_path, 'r') as f:
            content = f.read()
        
        with open(env_path, 'w') as f:
            f.write(content)
        
        logger.info("✅ Using fixed env.py configuration")
        return True
    return False


def test_alembic_autogenerate():
    """Test Alembic auto-generation."""
    logger.info("🧪 Testing Alembic auto-generation")
    
    try:
        # Try to generate a test migration
        result = subprocess.run([
            sys.executable, "-m", "alembic", "revision", 
            "--autogenerate", "-m", "test_autogenerate"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            logger.info("✅ Alembic auto-generation successful!")
            logger.info(f"Generated migration output:\n{result.stdout}")
            
            # Clean up test migration
            cleanup_test_migration()
            return True
        else:
            logger.error("❌ Alembic auto-generation failed:")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception during auto-generation: {e}")
        return False


def cleanup_test_migration():
    """Remove test migration file."""
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        for file in versions_dir.glob("*test_autogenerate*"):
            file.unlink()
            logger.info(f"🧹 Cleaned up test migration: {file.name}")


def main():
    """Main test function."""
    logger.info("🔍 Analyzing Alembic Auto-Generation Issues")
    
    # Check database availability
    if not test_database_connection():
        logger.warning("⚠️  Database not available - cannot test auto-generation")
        logger.info("💡 To test auto-generation:")
        logger.info("   1. Start database: docker-compose up postgres -d")
        logger.info("   2. Run this script again")
        return
    
    # Backup current configuration
    backup_current_env()
    
    try:
        # Use fixed configuration
        if use_fixed_env():
            # Test auto-generation
            success = test_alembic_autogenerate()
            
            if success:
                logger.info("🎉 Alembic auto-generation is now working!")
            else:
                logger.error("❌ Auto-generation still failing")
        
    finally:
        # Restore original configuration
        restore_env()
        logger.info("🔄 Restored original configuration")


if __name__ == "__main__":
    main()
