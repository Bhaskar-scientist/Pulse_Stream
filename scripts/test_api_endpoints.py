#!/usr/bin/env python3
"""Test script for PulseStream REST API endpoints."""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

import httpx
from core.logging import get_logger

logger = get_logger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-12345"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

class APITester:
    """Test class for PulseStream API endpoints."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
    
    async def test_health_endpoint(self) -> bool:
        """Test the main health endpoint."""
        try:
            response = await self.client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Health endpoint working: {data}")
                self.test_results.append(("Health Endpoint", True, data))
                return True
            else:
                logger.error(f"❌ Health endpoint failed: {response.status_code}")
                self.test_results.append(("Health Endpoint", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Health endpoint error: {e}")
            self.test_results.append(("Health Endpoint", False, str(e)))
            return False
    
    async def test_root_endpoint(self) -> bool:
        """Test the root endpoint."""
        try:
            response = await self.client.get(f"{BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Root endpoint working: {data}")
                self.test_results.append(("Root Endpoint", True, data))
                return True
            else:
                logger.error(f"❌ Root endpoint failed: {response.status_code}")
                self.test_results.append(("Root Endpoint", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Root endpoint error: {e}")
            self.test_results.append(("Root Endpoint", False, str(e)))
            return False
    
    async def test_event_ingestion(self) -> bool:
        """Test event ingestion endpoint."""
        try:
            test_event = {
                "event_id": f"api-test-{int(time.time())}",
                "event_type": "api_call",
                "title": "API Test Event",
                "message": "Testing the REST API endpoint",
                "severity": "info",
                "source": {
                    "service": "api-tester",
                    "endpoint": "/test",
                    "method": "POST",
                    "version": "v1"
                },
                "event_timestamp": datetime.utcnow().isoformat()
            }
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events",
                headers=HEADERS,
                json=test_event
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Event ingestion working: {data}")
                self.test_results.append(("Event Ingestion", True, data))
                return True
            else:
                logger.error(f"❌ Event ingestion failed: {response.status_code} - {response.text}")
                self.test_results.append(("Event Ingestion", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Event ingestion error: {e}")
            self.test_results.append(("Event Ingestion", False, str(e)))
            return False
    
    async def test_batch_ingestion(self) -> bool:
        """Test batch event ingestion endpoint."""
        try:
            test_events = [
                {
                    "event_id": f"batch-1-{int(time.time())}",
                    "event_type": "api_call",
                    "title": "Batch Event 1",
                    "message": "First batch event",
                    "severity": "info",
                    "source": {
                        "service": "batch-tester",
                        "endpoint": "/batch1",
                        "method": "POST",
                        "version": "v1"
                    },
                    "event_timestamp": datetime.utcnow().isoformat()
                },
                {
                    "event_id": f"batch-2-{int(time.time())}",
                    "event_type": "error_event",
                    "title": "Batch Event 2",
                    "message": "Second batch event",
                    "severity": "error",
                    "source": {
                        "service": "batch-tester",
                        "endpoint": "/batch2",
                        "method": "POST",
                        "version": "v1"
                    },
                    "event_timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            batch_data = {"events": test_events}
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events/batch",
                headers=HEADERS,
                json=batch_data
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Batch ingestion working: {data}")
                self.test_results.append(("Batch Ingestion", True, data))
                return True
            else:
                logger.error(f"❌ Batch ingestion failed: {response.status_code} - {response.text}")
                self.test_results.append(("Batch Ingestion", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Batch ingestion error: {e}")
            self.test_results.append(("Batch Ingestion", False, str(e)))
            return False
    
    async def test_event_search(self) -> bool:
        """Test event search endpoint."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/ingestion/events/search?service=test-service&limit=5",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Event search working: Found {data.get('total_count', 0)} events")
                self.test_results.append(("Event Search", True, f"Found {data.get('total_count', 0)} events"))
                return True
            else:
                logger.error(f"❌ Event search failed: {response.status_code} - {response.text}")
                self.test_results.append(("Event Search", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Event search error: {e}")
            self.test_results.append(("Event Search", False, str(e)))
            return False
    
    async def test_event_stats(self) -> bool:
        """Test event statistics endpoint."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/ingestion/stats",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Event stats working: {data.get('total_events', 0)} total events")
                self.test_results.append(("Event Stats", True, f"{data.get('total_events', 0)} total events"))
                return True
            else:
                logger.error(f"❌ Event stats failed: {response.status_code} - {response.text}")
                self.test_results.append(("Event Stats", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Event stats error: {e}")
            self.test_results.append(("Event Stats", False, str(e)))
            return False
    
    async def test_ingestion_health(self) -> bool:
        """Test ingestion health endpoint."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/ingestion/health",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Ingestion health working: Queue size {data.get('queue_size', 0)}")
                self.test_results.append(("Ingestion Health", True, f"Queue size: {data.get('queue_size', 0)}"))
                return True
            else:
                logger.error(f"❌ Ingestion health failed: {response.status_code} - {response.text}")
                self.test_results.append(("Ingestion Health", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Ingestion health error: {e}")
            self.test_results.append(("Ingestion Health", False, str(e)))
            return False
    
    async def test_rate_limit_info(self) -> bool:
        """Test rate limit info endpoint."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/ingestion/rate-limit",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Rate limit info working: {data.get('remaining', 0)} requests remaining")
                self.test_results.append(("Rate Limit Info", True, f"{data.get('remaining', 0)} remaining"))
                return True
            else:
                logger.error(f"❌ Rate limit info failed: {response.status_code} - {response.text}")
                self.test_results.append(("Rate Limit Info", False, f"Status: {response.status_code}"))
                return False
        except Exception as e:
            logger.error(f"❌ Rate limit info error: {e}")
            self.test_results.append(("Rate Limit Info", False, str(e)))
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all API tests."""
        logger.info("🚀 Starting PulseStream REST API Tests")
        
        tests = [
            self.test_health_endpoint,
            self.test_root_endpoint,
            self.test_event_ingestion,
            self.test_batch_ingestion,
            self.test_event_search,
            self.test_event_stats,
            self.test_ingestion_health,
            self.test_rate_limit_info
        ]
        
        results = []
        for test in tests:
            try:
                success = await test()
                results.append(success)
            except Exception as e:
                logger.error(f"❌ Test {test.__name__} failed with exception: {e}")
                results.append(False)
        
        # Calculate summary
        total_tests = len(results)
        passed_tests = sum(results)
        failed_tests = total_tests - passed_tests
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "test_results": self.test_results
        }
        
        logger.info(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed ({summary['success_rate']:.1f}%)")
        
        return summary
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def main():
    """Main test function."""
    tester = APITester()
    
    try:
        summary = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("📋 DETAILED TEST RESULTS")
        print("="*60)
        
        for test_name, success, details in summary["test_results"]:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}: {details}")
        
        print("\n" + "="*60)
        print("📊 FINAL SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if summary['success_rate'] >= 90:
            print("\n🎉 Excellent! REST API is working perfectly!")
        elif summary['success_rate'] >= 70:
            print("\n👍 Good! Most endpoints are working.")
        else:
            print("\n⚠️  Some endpoints need attention.")
        
        return summary['success_rate'] >= 90
        
    finally:
        await tester.close()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
