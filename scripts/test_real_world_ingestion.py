#!/usr/bin/env python3
"""
Real-world event ingestion test for PulseStream.
Tests production scenarios including failures, retries, duplicates, and high load.
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any
import httpx
from dataclasses import dataclass
from collections import defaultdict

# Test configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-12345"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


@dataclass
class TestResult:
    """Test result tracking."""
    test_name: str
    passed: bool
    duration_ms: float
    details: str
    issues: List[str] = None


class RealWorldIngestionTester:
    """Real-world production scenario tester."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results: List[TestResult] = []
        self.events_sent = 0
        self.events_failed = 0
        self.duplicates_found = 0
        
    async def run_all_tests(self):
        """Run all real-world scenario tests."""
        print(">> Starting Real-World Event Ingestion Tests")
        print("=" * 80)
        
        tests = [
            self.test_basic_ingestion,
            self.test_duplicate_detection,
            self.test_idempotency,
            self.test_concurrent_requests,
            self.test_rate_limiting,
            self.test_large_payload,
            self.test_network_retry_simulation,
            self.test_partial_batch_failure,
            self.test_transaction_atomicity,
            self.test_high_throughput,
            self.test_error_handling,
            self.test_data_consistency
        ]
        
        for test in tests:
            print(f"\n{'='*80}")
            try:
                await test()
            except Exception as e:
                print(f"[FAIL] Test failed with exception: {e}")
                self.results.append(TestResult(
                    test_name=test.__name__,
                    passed=False,
                    duration_ms=0,
                    details=f"Exception: {str(e)}",
                    issues=[str(e)]
                ))
        
        await self.print_summary()
    
    async def test_basic_ingestion(self):
        """Test 1: Basic event ingestion - baseline functionality."""
        print("\n>> Test 1: Basic Event Ingestion")
        start_time = time.time()
        issues = []
        
        event = {
            "event_id": f"basic-test-{uuid.uuid4()}",
            "event_type": "api_call",
            "title": "Basic Ingestion Test",
            "message": "Testing basic event ingestion",
            "source": {
                "service": "test-service",
                "endpoint": "/api/test",
                "method": "POST",
                "version": "1.0.0",
                "environment": "test"
            },
            "metrics": {
                "response_time_ms": 150.0,
                "status_code": 200
            }
        }
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events",
                headers=HEADERS,
                json=event
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] Event ingested: {data.get('event_id')}")
                print(f"   Status: {data.get('processing_status')}")
                self.events_sent += 1
            else:
                issues.append(f"HTTP {response.status_code}: {response.text}")
                print(f"[FAIL] Failed: {response.status_code}")
                self.events_failed += 1
                
        except Exception as e:
            issues.append(f"Exception: {str(e)}")
            print(f"[FAIL] Exception: {e}")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Basic Ingestion",
            passed=len(issues) == 0,
            duration_ms=duration,
            details=f"Sent: {self.events_sent}, Failed: {self.events_failed}",
            issues=issues if issues else None
        ))
    
    async def test_duplicate_detection(self):
        """Test 2: Duplicate event detection (should prevent duplicates)."""
        print("\n>> Test 2: Duplicate Detection Test")
        start_time = time.time()
        issues = []
        
        # Same event_id sent twice
        event_id = f"duplicate-test-{uuid.uuid4()}"
        event = {
            "event_id": event_id,
            "event_type": "api_call",
            "title": "Duplicate Test Event",
            "message": "Testing duplicate detection",
            "source": {
                "service": "test-service",
                "endpoint": "/api/duplicate",
                "method": "POST",
                "version": "1.0.0"
            },
            "metrics": {
                "response_time_ms": 100.0,
                "status_code": 200
            }
        }
        
        # Send first time
        response1 = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events",
            headers=HEADERS,
            json=event
        )
        
        # Send duplicate
        response2 = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events",
            headers=HEADERS,
            json=event
        )
        
        if response1.status_code == 200 and response2.status_code == 200:
            # Both succeeded - CHECK IF THIS IS CORRECT BEHAVIOR
            print(f"[WARN] Both requests succeeded (potential duplicate)")
            print(f"   First:  {response1.json().get('event_id')}")
            print(f"   Second: {response2.json().get('event_id')}")
            issues.append("CRITICAL: No duplicate detection - both events accepted")
            self.duplicates_found += 1
        elif response1.status_code == 200 and response2.status_code == 409:
            print(f"[OK] Duplicate correctly rejected")
        else:
            issues.append(f"Unexpected: R1={response1.status_code}, R2={response2.status_code}")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Duplicate Detection",
            passed=len(issues) == 0,
            duration_ms=duration,
            details=f"Duplicates found: {self.duplicates_found}",
            issues=issues if issues else None
        ))
    
    async def test_idempotency(self):
        """Test 3: Idempotent requests with same idempotency key."""
        print("\n Test 3: Idempotency Test")
        start_time = time.time()
        issues = []
        
        idempotency_key = str(uuid.uuid4())
        event = {
            "event_id": f"idempotent-{uuid.uuid4()}",
            "event_type": "api_call",
            "title": "Idempotency Test",
            "source": {
                "service": "test-service",
                "endpoint": "/api/idempotent",
                "method": "POST",
                "version": "1.0.0"
            },
            "metrics": {
                "response_time_ms": 120.0,
                "status_code": 200
            }
        }
        
        headers_with_key = {**HEADERS, "Idempotency-Key": idempotency_key}
        
        # Send with same idempotency key twice
        response1 = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events",
            headers=headers_with_key,
            json=event
        )
        
        response2 = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events",
            headers=headers_with_key,
            json=event
        )
        
        if response1.json().get('event_id') == response2.json().get('event_id'):
            print(f" Idempotency maintained: same event returned")
        else:
            print(f"  Different events returned (no idempotency)")
            issues.append("CRITICAL: No idempotency support")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Idempotency",
            passed=len(issues) == 0,
            duration_ms=duration,
            details="Idempotency key test",
            issues=issues if issues else None
        ))
    
    async def test_concurrent_requests(self):
        """Test 4: Concurrent requests (race conditions)."""
        print("\n Test 4: Concurrent Requests Test")
        start_time = time.time()
        issues = []
        
        async def send_event(index: int):
            event = {
                "event_id": f"concurrent-{index}-{uuid.uuid4()}",
                "event_type": "api_call",
                "title": f"Concurrent Test {index}",
                "source": {
                    "service": "test-service",
                    "endpoint": f"/api/concurrent/{index}",
                    "method": "POST",
                    "version": "1.0.0"
                },
                "metrics": {
                    "response_time_ms": 100.0,
                    "status_code": 200
                }
            }
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events",
                headers=HEADERS,
                json=event
            )
            return response.status_code
        
        # Send 50 concurrent requests
        tasks = [send_event(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if r == 200)
        failed = sum(1 for r in results if isinstance(r, Exception) or r != 200)
        
        print(f"   Sent: 50 concurrent requests")
        print(f"    Successful: {successful}")
        print(f"    Failed: {failed}")
        
        if failed > 5:  # Allow some failures
            issues.append(f"High failure rate: {failed}/50 failed")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Concurrent Requests",
            passed=len(issues) == 0,
            duration_ms=duration,
            details=f"Success: {successful}/50",
            issues=issues if issues else None
        ))
    
    async def test_rate_limiting(self):
        """Test 5: Rate limiting enforcement."""
        print("\n Test 5: Rate Limiting Test")
        start_time = time.time()
        issues = []
        
        # Send events rapidly to trigger rate limit
        rate_limited = False
        events_before_limit = 0
        
        for i in range(150):  # Try to exceed limit
            event = {
                "event_id": f"rate-test-{i}",
                "event_type": "api_call",
                "title": f"Rate Limit Test {i}",
                "source": {
                    "service": "test-service",
                    "endpoint": "/api/rate",
                    "method": "POST",
                    "version": "1.0.0"
                },
                "metrics": {
                    "response_time_ms": 50.0,
                    "status_code": 200
                }
            }
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events",
                headers=HEADERS,
                json=event
            )
            
            if response.status_code == 429:
                rate_limited = True
                events_before_limit = i
                print(f" Rate limit triggered after {i} events")
                break
            elif response.status_code != 200:
                issues.append(f"Unexpected status: {response.status_code}")
                break
        
        if not rate_limited:
            print(f"  Rate limit NOT triggered after 150 events")
            issues.append("WARNING: Rate limit not enforced")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Rate Limiting",
            passed=rate_limited,
            duration_ms=duration,
            details=f"Limited after {events_before_limit} events" if rate_limited else "Not limited",
            issues=issues if issues else None
        ))
    
    async def test_large_payload(self):
        """Test 6: Large payload handling."""
        print("\n Test 6: Large Payload Test")
        start_time = time.time()
        issues = []
        
        # Create 5MB payload (within 10MB limit)
        large_data = "x" * (5 * 1024 * 1024)  # 5MB of data
        
        event = {
            "event_id": f"large-payload-{uuid.uuid4()}",
            "event_type": "api_call",
            "title": "Large Payload Test",
            "source": {
                "service": "test-service",
                "endpoint": "/api/large",
                "method": "POST",
                "version": "1.0.0"
            },
            "payload": {
                "large_data": large_data
            },
            "metrics": {
                "response_time_ms": 200.0,
                "status_code": 200
            }
        }
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events",
                headers=HEADERS,
                json=event
            )
            
            if response.status_code == 200:
                print(f" Large payload accepted (5MB)")
            else:
                print(f" Large payload rejected: {response.status_code}")
                issues.append(f"Failed with: {response.text[:200]}")
        except Exception as e:
            print(f" Exception: {e}")
            issues.append(f"Exception: {str(e)}")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Large Payload",
            passed=len(issues) == 0,
            duration_ms=duration,
            details="5MB payload test",
            issues=issues if issues else None
        ))
    
    async def test_network_retry_simulation(self):
        """Test 7: Simulate network failure and retry."""
        print("\n Test 7: Network Retry Simulation")
        start_time = time.time()
        issues = []
        
        event_id = f"retry-test-{uuid.uuid4()}"
        event = {
            "event_id": event_id,
            "event_type": "api_call",
            "title": "Retry Test Event",
            "source": {
                "service": "test-service",
                "endpoint": "/api/retry",
                "method": "POST",
                "version": "1.0.0"
            },
            "metrics": {
                "response_time_ms": 100.0,
                "status_code": 200
            }
        }
        
        # First attempt (simulate timeout by using very short timeout)
        try:
            await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events",
                headers=HEADERS,
                json=event,
                timeout=0.001  # 1ms timeout - will fail
            )
        except:
            print("   First attempt timed out (simulated)")
        
        # Retry with normal timeout
        response = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events",
            headers=HEADERS,
            json=event
        )
        
        if response.status_code == 200:
            # Check if this created duplicate
            print(f" Retry succeeded")
            print(f"     Need to verify no duplicate created")
            issues.append("INFO: Check for duplicate handling on retry")
        else:
            issues.append(f"Retry failed: {response.status_code}")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Network Retry",
            passed=response.status_code == 200,
            duration_ms=duration,
            details="Timeout + Retry scenario",
            issues=issues if issues else None
        ))
    
    async def test_partial_batch_failure(self):
        """Test 8: Batch processing with partial failures."""
        print("\n Test 8: Partial Batch Failure Test")
        start_time = time.time()
        issues = []
        
        # Create batch with valid and invalid events
        events = []
        for i in range(10):
            if i == 5:
                # Invalid event (missing required fields)
                events.append({
                    "event_id": f"batch-invalid-{i}",
                    "title": "Invalid Event"
                    # Missing source and other required fields
                })
            else:
                # Valid event
                events.append({
                    "event_id": f"batch-valid-{i}",
                    "event_type": "api_call",
                    "title": f"Batch Event {i}",
                    "source": {
                        "service": "test-service",
                        "endpoint": f"/api/batch/{i}",
                        "method": "POST",
                        "version": "1.0.0"
                    },
                    "metrics": {
                        "response_time_ms": 100.0,
                        "status_code": 200
                    }
                })
        
        batch = {"events": events}
        
        response = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events/batch",
            headers=HEADERS,
            json=batch
        )
        
        if response.status_code == 200:
            data = response.json()
            successful = data.get('successful_count', 0)
            failed = data.get('failed_count', 0)
            
            print(f"   Total: 10 events")
            print(f"    Successful: {successful}")
            print(f"    Failed: {failed}")
            
            if successful == 9 and failed == 1:
                print(f" Partial batch handled correctly")
            else:
                issues.append(f"Unexpected: success={successful}, failed={failed}")
        else:
            print(f" Batch request failed: {response.status_code}")
            issues.append(f"Batch failed: {response.text[:200]}")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Partial Batch Failure",
            passed=len(issues) == 0,
            duration_ms=duration,
            details="9 valid, 1 invalid event",
            issues=issues if issues else None
        ))
    
    async def test_transaction_atomicity(self):
        """Test 9: Database transaction atomicity."""
        print("\n Test 9: Transaction Atomicity Test")
        start_time = time.time()
        issues = []
        
        # This test requires checking database directly
        # We'll verify that events are either fully saved or not saved at all
        
        event = {
            "event_id": f"atomicity-{uuid.uuid4()}",
            "event_type": "api_call",
            "title": "Atomicity Test",
            "source": {
                "service": "test-service",
                "endpoint": "/api/atomicity",
                "method": "POST",
                "version": "1.0.0"
            },
            "metrics": {
                "response_time_ms": 100.0,
                "status_code": 200
            }
        }
        
        response = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events",
            headers=HEADERS,
            json=event
        )
        
        if response.status_code == 200:
            event_id = response.json().get('event_id')
            print(f" Event saved: {event_id}")
            print(f"     Manual verification needed:")
            print(f"      - Check if event exists in DB")
            print(f"      - Check if rate limit was incremented")
            print(f"      - Check if queued for processing")
            issues.append("INFO: Manual verification required for atomicity")
        else:
            issues.append(f"Request failed: {response.status_code}")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Transaction Atomicity",
            passed=response.status_code == 200,
            duration_ms=duration,
            details="Atomicity verification needed",
            issues=issues if issues else None
        ))
    
    async def test_high_throughput(self):
        """Test 10: High throughput stress test."""
        print("\n Test 10: High Throughput Test (100 events)")
        start_time = time.time()
        issues = []
        
        async def send_bulk_event(index: int):
            event = {
                "event_id": f"throughput-{index}-{uuid.uuid4()}",
                "event_type": "api_call",
                "title": f"Throughput Test {index}",
                "source": {
                    "service": "test-service",
                    "endpoint": f"/api/throughput/{index}",
                    "method": "POST",
                    "version": "1.0.0"
                },
                "metrics": {
                    "response_time_ms": 80.0,
                    "status_code": 200
                }
            }
            
            try:
                response = await self.client.post(
                    f"{BASE_URL}/api/v1/ingestion/events",
                    headers=HEADERS,
                    json=event
                )
                return response.status_code == 200
            except Exception as e:
                return False
        
        # Send 100 events as fast as possible
        tasks = [send_bulk_event(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        
        successful = sum(results)
        failed = len(results) - successful
        duration = (time.time() - start_time) * 1000
        throughput = (successful / duration) * 1000  # events per second
        
        print(f"   Total sent: 100 events")
        print(f"    Successful: {successful}")
        print(f"    Failed: {failed}")
        print(f"   [PERF] Throughput: {throughput:.2f} events/sec")
        print(f"     Total time: {duration:.2f}ms")
        
        if throughput < 50:
            issues.append(f"Low throughput: {throughput:.2f} events/sec")
        
        self.results.append(TestResult(
            test_name="High Throughput",
            passed=successful >= 90,
            duration_ms=duration,
            details=f"{throughput:.2f} events/sec",
            issues=issues if issues else None
        ))
    
    async def test_error_handling(self):
        """Test 11: Error handling with invalid data."""
        print("\n Test 11: Error Handling Test")
        start_time = time.time()
        issues = []
        
        # Test various error scenarios
        test_cases = [
            {
                "name": "Missing event_type",
                "data": {
                    "event_id": str(uuid.uuid4()),
                    "title": "Missing Type",
                    "source": {
                        "service": "test",
                        "endpoint": "/test",
                        "method": "POST",
                        "version": "1.0"
                    }
                },
                "expected_status": 422  # Validation error
            },
            {
                "name": "Invalid event_type",
                "data": {
                    "event_id": str(uuid.uuid4()),
                    "event_type": "INVALID_TYPE",
                    "title": "Invalid Type",
                    "source": {
                        "service": "test",
                        "endpoint": "/test",
                        "method": "POST",
                        "version": "1.0"
                    }
                },
                "expected_status": 422
            },
            {
                "name": "Empty payload",
                "data": {},
                "expected_status": 422
            }
        ]
        
        for test_case in test_cases:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/ingestion/events",
                headers=HEADERS,
                json=test_case["data"]
            )
            
            if response.status_code == test_case["expected_status"]:
                print(f"    {test_case['name']}: Correct error {response.status_code}")
            else:
                print(f"    {test_case['name']}: Got {response.status_code}, expected {test_case['expected_status']}")
                issues.append(f"{test_case['name']}: Wrong status code")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Error Handling",
            passed=len(issues) == 0,
            duration_ms=duration,
            details=f"Tested {len(test_cases)} error scenarios",
            issues=issues if issues else None
        ))
    
    async def test_data_consistency(self):
        """Test 12: Data consistency verification."""
        print("\n Test 12: Data Consistency Test")
        start_time = time.time()
        issues = []
        
        # Send event and verify it can be retrieved
        event_id = f"consistency-{uuid.uuid4()}"
        event = {
            "event_id": event_id,
            "event_type": "api_call",
            "title": "Consistency Test Event",
            "message": "Testing data consistency",
            "source": {
                "service": "consistency-service",
                "endpoint": "/api/consistency",
                "method": "POST",
                "version": "1.0.0",
                "environment": "test"
            },
            "metrics": {
                "response_time_ms": 125.5,
                "status_code": 201
            },
            "payload": {
                "test_data": "consistency_check",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Send event
        post_response = await self.client.post(
            f"{BASE_URL}/api/v1/ingestion/events",
            headers=HEADERS,
            json=event
        )
        
        if post_response.status_code == 200:
            saved_event_id = post_response.json().get('event_id')
            print(f"    Event saved: {saved_event_id}")
            
            # Try to retrieve it via search
            await asyncio.sleep(0.5)  # Small delay for indexing
            
            search_response = await self.client.get(
                f"{BASE_URL}/api/v1/ingestion/events/search?service=consistency-service",
                headers=HEADERS
            )
            
            if search_response.status_code == 200:
                events = search_response.json().get('events', [])
                found = any(e.get('id') == saved_event_id for e in events)
                
                if found:
                    print(f"    Event retrieved successfully")
                else:
                    print(f"     Event not found in search results")
                    issues.append("Event saved but not retrievable")
            else:
                issues.append(f"Search failed: {search_response.status_code}")
        else:
            issues.append(f"Event save failed: {post_response.status_code}")
        
        duration = (time.time() - start_time) * 1000
        self.results.append(TestResult(
            test_name="Data Consistency",
            passed=len(issues) == 0,
            duration_ms=duration,
            details="Save and retrieve verification",
            issues=issues if issues else None
        ))
    
    async def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 80)
        print(">> REAL-WORLD INGESTION TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        print(f"\n>> Overall Results:")
        print(f"   Total Tests: {len(self.results)}")
        print(f"   [PASS] Passed: {passed}")
        print(f"   [FAIL] Failed: {failed}")
        print(f"   Success Rate: {(passed/len(self.results)*100):.1f}%")
        
        print(f"\n>> Event Statistics:")
        print(f"   Events Sent: {self.events_sent}")
        print(f"   Events Failed: {self.events_failed}")
        print(f"   Duplicates Found: {self.duplicates_found}")
        
        print(f"\n[CRITICAL] CRITICAL ISSUES FOUND:")
        critical_issues = defaultdict(list)
        for result in self.results:
            if result.issues:
                for issue in result.issues:
                    if "CRITICAL" in issue:
                        critical_issues[result.test_name].append(issue)
        
        if critical_issues:
            for test_name, issues in critical_issues.items():
                print(f"\n   {test_name}:")
                for issue in issues:
                    print(f"      - {issue}")
        else:
            print("   None found (check warnings below)")
        
        print(f"\n[WARNING] WARNINGS:")
        warnings = defaultdict(list)
        for result in self.results:
            if result.issues:
                for issue in result.issues:
                    if "WARNING" in issue or "INFO" in issue:
                        warnings[result.test_name].append(issue)
        
        if warnings:
            for test_name, issues in warnings.items():
                print(f"\n   {test_name}:")
                for issue in issues:
                    print(f"      - {issue}")
        else:
            print("   None")
        
        print(f"\n>> Detailed Results:")
        for result in self.results:
            status = "[PASS]" if result.passed else "[FAIL]"
            print(f"\n   {status} {result.test_name}")
            print(f"      Duration: {result.duration_ms:.2f}ms")
            print(f"      Details: {result.details}")
            if result.issues and not any(x in str(result.issues) for x in ["CRITICAL", "WARNING", "INFO"]):
                print(f"      Issues: {', '.join(result.issues[:2])}")
        
        print("\n" + "=" * 80)
        print(">> PRODUCTION READINESS ASSESSMENT:")
        print("=" * 80)
        
        if passed >= 11:  # 11/12 tests passing
            print("[READY] System passed most tests with minor issues")
        elif passed >= 8:
            print("[CAUTION] System has significant issues, needs fixes")
        else:
            print("[NOT READY] Critical reliability issues found")
        
        print("\n>> Recommendations:")
        if self.duplicates_found > 0:
            print("   - URGENT: Implement duplicate detection/idempotency")
        print("   - Add transaction atomicity for DB + queue operations")
        print("   - Implement proper error handling with specific exceptions")
        print("   - Add circuit breaker for failure isolation")
        print("   - Implement retry logic with exponential backoff")
        print("   - Add comprehensive monitoring and metrics")
        
        print("\n" + "=" * 80)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def main():
    """Main test execution."""
    tester = RealWorldIngestionTester()
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n  Tests interrupted by user")
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())

