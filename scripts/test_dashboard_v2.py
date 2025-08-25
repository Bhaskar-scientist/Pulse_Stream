#!/usr/bin/env python3
"""
Test script for Dashboard v2 service - Built alongside existing dashboard.
Tests that new service works without modifying existing functionality.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.dashboard_v2.services import DashboardServiceV2
from apps.dashboard_v2.schemas import AlertSummaryResponse, RealTimeMetricsResponse, DashboardOverviewResponse

class DashboardV2Tester:
    """Test dashboard v2 service functionality."""
    
    def __init__(self):
        self.test_results = []
        self.base_url = "http://localhost:8000"
        # Use a test API key (you'll need to get a real one from your system)
        self.test_api_key = "test-api-key"
        self.test_tenant_id = "test-tenant"
    
    async def test_service_initialization(self):
        """Test that the service can be initialized."""
        try:
            service = DashboardServiceV2(self.base_url)
            print("✅ Service Initialization: Working")
            self.test_results.append(("Service Initialization", True))
            return True
        except Exception as e:
            print(f"❌ Service Initialization: Failed - {e}")
            self.test_results.append(("Service Initialization", False))
            return False
    
    async def test_alert_summary(self):
        """Test alert summary functionality."""
        try:
            async with DashboardServiceV2(self.base_url) as service:
                summary = await service.get_alert_summary(self.test_tenant_id, self.test_api_key)
                
                # Validate response structure
                assert isinstance(summary, AlertSummaryResponse)
                assert hasattr(summary, 'total_alerts')
                assert hasattr(summary, 'critical_count')
                assert hasattr(summary, 'warning_count')
                assert hasattr(summary, 'info_count')
                assert hasattr(summary, 'recent_alerts')
                assert hasattr(summary, 'alert_trends')
                assert hasattr(summary, 'last_updated')
                
                print("✅ Alert Summary: Working")
                print(f"   - Total Alerts: {summary.total_alerts}")
                print(f"   - Critical: {summary.critical_count}")
                print(f"   - Warning: {summary.warning_count}")
                print(f"   - Info: {summary.info_count}")
                
                self.test_results.append(("Alert Summary", True))
                return True
        except Exception as e:
            print(f"❌ Alert Summary: Failed - {e}")
            self.test_results.append(("Alert Summary", False))
            return False
    
    async def test_real_time_metrics(self):
        """Test real-time metrics functionality."""
        try:
            async with DashboardServiceV2(self.base_url) as service:
                metrics = await service.get_real_time_metrics(self.test_tenant_id, self.test_api_key)
                
                # Validate response structure
                assert isinstance(metrics, RealTimeMetricsResponse)
                assert hasattr(metrics, 'event_volume')
                assert hasattr(metrics, 'response_times')
                assert hasattr(metrics, 'error_rates')
                assert hasattr(metrics, 'throughput')
                assert hasattr(metrics, 'last_updated')
                
                print("✅ Real-time Metrics: Working")
                print(f"   - Event Volume: {metrics.event_volume}")
                print(f"   - Response Times: {len(metrics.response_times)} endpoints")
                print(f"   - Error Rates: {len(metrics.error_rates)} services")
                
                self.test_results.append(("Real-time Metrics", True))
                return True
        except Exception as e:
            print(f"❌ Real-time Metrics: Failed - {e}")
            self.test_results.append(("Real-time Metrics", False))
            return False
    
    async def test_dashboard_overview(self):
        """Test dashboard overview functionality."""
        try:
            async with DashboardServiceV2(self.base_url) as service:
                overview = await service.get_dashboard_overview(self.test_tenant_id, self.test_api_key)
                
                # Validate response structure
                assert isinstance(overview, DashboardOverviewResponse)
                assert hasattr(overview, 'system_health')
                assert hasattr(overview, 'alert_summary')
                assert hasattr(overview, 'performance_summary')
                assert hasattr(overview, 'last_updated')
                
                print("✅ Dashboard Overview: Working")
                print(f"   - System Health: {overview.system_health.overall_status}")
                print(f"   - Performance Summary: {overview.performance_summary}")
                
                self.test_results.append(("Dashboard Overview", True))
                return True
        except Exception as e:
            print(f"❌ Dashboard Overview: Failed - {e}")
            self.test_results.append(("Dashboard Overview", False))
            return False
    
    async def test_system_health(self):
        """Test system health functionality."""
        try:
            async with DashboardServiceV2(self.base_url) as service:
                health = await service._get_system_health(self.test_tenant_id, self.test_api_key)
                
                # Validate response structure
                assert hasattr(health, 'overall_status')
                assert hasattr(health, 'services')
                assert hasattr(health, 'performance_metrics')
                assert hasattr(health, 'last_check')
                assert hasattr(health, 'uptime_seconds')
                
                print("✅ System Health: Working")
                print(f"   - Overall Status: {health.overall_status}")
                print(f"   - Services: {len(health.services)}")
                
                self.test_results.append(("System Health", True))
                return True
        except Exception as e:
            print(f"❌ System Health: Failed - {e}")
            self.test_results.append(("System Health", False))
            return False
    
    async def test_error_handling(self):
        """Test error handling and fallback mechanisms."""
        try:
            async with DashboardServiceV2(self.base_url) as service:
                # Test with invalid API key
                summary = await service.get_alert_summary(self.test_tenant_id, "invalid-key")
                
                # Should return empty summary instead of failing
                assert isinstance(summary, AlertSummaryResponse)
                assert summary.total_alerts == 0
                assert summary.critical_count == 0
                assert summary.warning_count == 0
                assert summary.info_count == 0
                
                print("✅ Error Handling: Working")
                print("   - Graceful fallback on API errors")
                print("   - Empty responses instead of crashes")
                
                self.test_results.append(("Error Handling", True))
                return True
        except Exception as e:
            print(f"❌ Error Handling: Failed - {e}")
            self.test_results.append(("Error Handling", False))
            return False
    
    async def test_data_transformation(self):
        """Test data transformation from existing APIs to new format."""
        try:
            async with DashboardServiceV2(self.base_url) as service:
                # Test the transformation methods
                test_events = [
                    {"status_code": 500, "source": "api-service", "duration_ms": 150, "timestamp": "2025-08-22T21:53:00Z"},
                    {"status_code": 200, "source": "web-service", "duration_ms": 50, "timestamp": "2025-08-22T21:53:00Z"},
                    {"status_code": 404, "source": "api-service", "duration_ms": 100, "timestamp": "2025-08-22T21:53:00Z"}
                ]
                
                # Test alert analysis
                alert_summary = await service._analyze_events_for_alerts(test_events)
                assert alert_summary.total_alerts == 2  # 500 and 404
                assert alert_summary.critical_count == 1  # 500
                assert alert_summary.warning_count == 1  # 404
                
                print("✅ Data Transformation: Working")
                print("   - Event analysis for alerts")
                print("   - Status code classification")
                print("   - Severity determination")
                
                self.test_results.append(("Data Transformation", True))
                return True
        except Exception as e:
            print(f"❌ Data Transformation: Failed - {e}")
            self.test_results.append(("Data Transformation", False))
            return False
    
    async def run_all_tests(self):
        """Run all dashboard v2 tests."""
        print("🚀 Starting Dashboard v2 Service Tests")
        print("=" * 60)
        print("Testing new service built alongside existing dashboard...")
        print()
        
        tests = [
            self.test_service_initialization,
            self.test_alert_summary,
            self.test_real_time_metrics,
            self.test_dashboard_overview,
            self.test_system_health,
            self.test_error_handling,
            self.test_data_transformation
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                self.test_results.append((test.__name__, False))
        
        print("=" * 60)
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
            print("🎉 All Dashboard v2 tests passed!")
            print("✅ New service is working correctly alongside existing dashboard")
            print("🛡️ Core protection maintained - no existing code modified")
        else:
            print("⚠️ Some Dashboard v2 tests failed!")
            print("🔍 Review failed tests for issues")
            
            # List failed tests
            print("\nFailed Tests:")
            for test_name, result in self.test_results:
                if not result:
                    print(f"   - {test_name}")
        
        return failed_tests == 0

async def main():
    """Main test function."""
    tester = DashboardV2Tester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ Dashboard v2 Test: PASSED")
        sys.exit(0)
    else:
        print("\n❌ Dashboard v2 Test: FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
