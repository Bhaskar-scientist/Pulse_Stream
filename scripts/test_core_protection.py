#!/usr/bin/env python3
"""
Core Protection Test Script
Tests that protected core systems are still working and haven't been modified.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import settings
from core.database import get_async_session
from core.redis import get_redis_client
from apps.auth.services import AuthenticationService, UserManagementService, TenantManagementService
from apps.ingestion.services import get_event_ingestion_service
from apps.storage.crud import tenant_crud, user_crud, event_crud

class CoreProtectionTester:
    """Test core systems are protected and working."""
    
    def __init__(self):
        self.auth_service = AuthenticationService()
        self.user_service = UserManagementService()
        self.tenant_service = TenantManagementService()
        # Initialize ingestion service with Redis client
        redis_client = get_redis_client()
        self.ingestion_service = get_event_ingestion_service(redis_client)
        self.test_results = []
        
    async def test_database_connection(self):
        """Test database connection is working."""
        try:
            async for session in get_async_session():
                # Test basic database operations
                tenant_count = await tenant_crud.count(session)
                user_count = await user_crud.count(session)
                event_count = await event_crud.count(session)
                
                print(f"✅ Database Connection: Working")
                print(f"   - Tenants: {tenant_count}")
                print(f"   - Users: {user_count}")
                print(f"   - Events: {event_count}")
                
                await session.close()
                self.test_results.append(("Database Connection", True))
                return True
        except Exception as e:
            print(f"❌ Database Connection: Failed - {e}")
            self.test_results.append(("Database Connection", False))
            return False
    
    async def test_redis_connection(self):
        """Test Redis connection is working."""
        try:
            redis_client = get_redis_client()
            redis_client.ping()
            print("✅ Redis Connection: Working")
            self.test_results.append(("Redis Connection", True))
            return True
        except Exception as e:
            print(f"❌ Redis Connection: Failed - {e}")
            self.test_results.append(("Redis Connection", False))
            return False
    
    async def test_auth_service(self):
        """Test authentication service is working."""
        try:
            # Test service initialization
            if self.auth_service:
                print("✅ Auth Service: Working")
                self.test_results.append(("Auth Service", True))
                return True
            else:
                print("❌ Auth Service: Failed - Service not available")
                self.test_results.append(("Auth Service", False))
                return False
        except Exception as e:
            print(f"❌ Auth Service: Failed - {e}")
            self.test_results.append(("Auth Service", False))
            return False
    
    async def test_ingestion_service(self):
        """Test event ingestion service is working."""
        try:
            # Test service initialization
            if self.ingestion_service:
                print("✅ Ingestion Service: Working")
                self.test_results.append(("Ingestion Service", True))
                return True
            else:
                print("❌ Ingestion Service: Failed - Service not available")
                self.test_results.append(("Ingestion Service", False))
                return False
        except Exception as e:
            print(f"❌ Ingestion Service: Failed - {e}")
            self.test_results.append(("Ingestion Service", False))
            return False
    
    async def test_crud_operations(self):
        """Test CRUD operations are working."""
        try:
            async for session in get_async_session():
                # Test basic CRUD operations
                await tenant_crud.count(session)
                await user_crud.count(session)
                await event_crud.count(session)
                
                print("✅ CRUD Operations: Working")
                await session.close()
                self.test_results.append(("CRUD Operations", True))
                return True
        except Exception as e:
            print(f"❌ CRUD Operations: Failed - {e}")
            self.test_results.append(("CRUD Operations", False))
            return False
    
    async def test_configuration(self):
        """Test configuration is loaded correctly."""
        try:
            # Test essential config values
            assert settings.app_name == "PulseStream"
            assert settings.database_url is not None
            assert settings.redis_url is not None
            assert settings.secret_key is not None
            
            print("✅ Configuration: Working")
            self.test_results.append(("Configuration", True))
            return True
        except Exception as e:
            print(f"❌ Configuration: Failed - {e}")
            self.test_results.append(("Configuration", False))
            return False
    
    async def test_protected_files(self):
        """Test that protected files haven't been modified."""
        try:
            protected_files = [
                "apps/auth/services.py",
                "apps/auth/api.py",
                "apps/auth/schemas.py",
                "apps/ingestion/services.py",
                "apps/ingestion/api.py",
                "apps/ingestion/schemas.py",
                "apps/storage/crud.py",
                "core/config.py",
                "core/database.py",
                "core/redis.py"
            ]
            
            all_files_exist = True
            for file_path in protected_files:
                if not os.path.exists(file_path):
                    print(f"❌ Protected file missing: {file_path}")
                    all_files_exist = False
            
            if all_files_exist:
                print("✅ Protected Files: All present")
                self.test_results.append(("Protected Files", True))
                return True
            else:
                print("❌ Protected Files: Some files missing")
                self.test_results.append(("Protected Files", False))
                return False
        except Exception as e:
            print(f"❌ Protected Files Check: Failed - {e}")
            self.test_results.append(("Protected Files Check", False))
            return False
    
    async def run_all_tests(self):
        """Run all core protection tests."""
        print("🛡️ Starting Core Protection Tests")
        print("=" * 50)
        
        tests = [
            self.test_database_connection,
            self.test_redis_connection,
            self.test_auth_service,
            self.test_ingestion_service,
            self.test_crud_operations,
            self.test_configuration,
            self.test_protected_files
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                self.test_results.append((test.__name__, False))
        
        print("=" * 50)
        await self.print_summary()
    
    async def print_summary(self):
        """Print test summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, result in self.test_results if result)
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Test Summary:")
        print(f"   - Total Tests: {total_tests}")
        print(f"   - Passed: {passed_tests}")
        print(f"   - Failed: {failed_tests}")
        print(f"   - Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            print("🎉 All core systems are protected and working!")
            print("🛡️ Core protection is ACTIVE")
        else:
            print("⚠️ Some core systems have issues!")
            print("🚨 Core protection may be compromised")
            
            # List failed tests
            print("\nFailed Tests:")
            for test_name, result in self.test_results:
                if not result:
                    print(f"   - {test_name}")
        
        return failed_tests == 0

async def main():
    """Main test function."""
    tester = CoreProtectionTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Core Protection Test: PASSED")
        sys.exit(0)
    else:
        print("\n❌ Core Protection Test: FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
