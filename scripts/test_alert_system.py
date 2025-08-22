#!/usr/bin/env python3
"""Test script for PulseStream Alert Management System."""

import asyncio
import json
import time
from datetime import datetime, timedelta
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

class AlertSystemTester:
    """Test class for PulseStream Alert Management System."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        self.created_rule_id = None
        self.created_alert_id = None
    
    async def test_create_alert_rule(self) -> bool:
        """Test creating an alert rule."""
        try:
            # Create a count-based alert rule
            rule_data = {
                "name": "High Event Count Rule",
                "description": "Alert when more than 10 events occur in 5 minutes",
                "event_type": "api_call",
                "condition": {
                    "type": "count",
                    "min_count": 10,
                    "max_count": 1000
                },
                "severity": "medium",
                "time_window": "5m",
                "evaluation_interval": 60,
                "cooldown_minutes": 5,
                "max_alerts_per_hour": 10,
                "notification_channels": ["email", "webhook"],
                "notification_template": "High event count detected: {event_count} events in {time_window}"
            }
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/alerting/rules",
                headers=HEADERS,
                json=rule_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.created_rule_id = data.get("rule", {}).get("id")
                logger.info(f"✅ Alert rule created successfully: {self.created_rule_id}")
                self.test_results.append(("Create Alert Rule", True, f"Rule ID: {self.created_rule_id}"))
                return True
            else:
                logger.error(f"❌ Alert rule creation failed: {response.status_code} - {response.text}")
                self.test_results.append(("Create Alert Rule", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert rule creation error: {e}")
            self.test_results.append(("Create Alert Rule", False, str(e)))
            return False
    
    async def test_list_alert_rules(self) -> bool:
        """Test listing alert rules."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/alerting/rules",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                rules_count = len(data.get("rules", []))
                logger.info(f"✅ Alert rules listed successfully: {rules_count} rules found")
                self.test_results.append(("List Alert Rules", True, f"Found {rules_count} rules"))
                return True
            else:
                logger.error(f"❌ Alert rules listing failed: {response.status_code} - {response.text}")
                self.test_results.append(("List Alert Rules", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert rules listing error: {e}")
            self.test_results.append(("List Alert Rules", False, str(e)))
            return False
    
    async def test_get_alert_rule(self) -> bool:
        """Test getting a specific alert rule."""
        if not self.created_rule_id:
            logger.warning("No rule ID available, skipping test")
            self.test_results.append(("Get Alert Rule", False, "No rule ID available"))
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/alerting/rules/{self.created_rule_id}",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                rule_name = data.get("rule", {}).get("name")
                logger.info(f"✅ Alert rule retrieved successfully: {rule_name}")
                self.test_results.append(("Get Alert Rule", True, f"Rule: {rule_name}"))
                return True
            else:
                logger.error(f"❌ Alert rule retrieval failed: {response.status_code} - {response.text}")
                self.test_results.append(("Get Alert Rule", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert rule retrieval error: {e}")
            self.test_results.append(("Get Alert Rule", False, str(e)))
            return False
    
    async def test_test_alert_rule(self) -> bool:
        """Test testing an alert rule."""
        if not self.created_rule_id:
            logger.warning("No rule ID available, skipping test")
            self.test_results.append(("Test Alert Rule", False, "No rule ID available"))
            return False
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/alerting/rules/{self.created_rule_id}/test",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                triggered = data.get("alert_id") is not None
                logger.info(f"✅ Alert rule tested successfully: {'Triggered' if triggered else 'Not triggered'}")
                self.test_results.append(("Test Alert Rule", True, f"{'Triggered' if triggered else 'Not triggered'}"))
                return True
            else:
                logger.error(f"❌ Alert rule testing failed: {response.status_code} - {response.text}")
                self.test_results.append(("Test Alert Rule", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert rule testing error: {e}")
            self.test_results.append(("Test Alert Rule", False, str(e)))
            return False
    
    async def test_evaluate_all_rules(self) -> bool:
        """Test evaluating all alert rules."""
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/alerting/evaluate",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                rules_evaluated = data.get("total_rules_evaluated", 0)
                alerts_triggered = data.get("alerts_triggered", 0)
                logger.info(f"✅ All rules evaluated: {rules_evaluated} rules, {alerts_triggered} alerts triggered")
                self.test_results.append(("Evaluate All Rules", True, f"{rules_evaluated} rules, {alerts_triggered} alerts"))
                return True
            else:
                logger.error(f"❌ Rule evaluation failed: {response.status_code} - {response.text}")
                self.test_results.append(("Evaluate All Rules", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Rule evaluation error: {e}")
            self.test_results.append(("Evaluate All Rules", False, str(e)))
            return False
    
    async def test_list_alerts(self) -> bool:
        """Test listing alerts."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/alerting/alerts",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                alerts_count = len(data.get("alerts", []))
                logger.info(f"✅ Alerts listed successfully: {alerts_count} alerts found")
                self.test_results.append(("List Alerts", True, f"Found {alerts_count} alerts"))
                
                # Store first alert ID for resolution test
                if alerts_count > 0:
                    self.created_alert_id = data["alerts"][0]["id"]
                
                return True
            else:
                logger.error(f"❌ Alerts listing failed: {response.status_code} - {response.text}")
                self.test_results.append(("List Alerts", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alerts listing error: {e}")
            self.test_results.append(("List Alerts", False, str(e)))
            return False
    
    async def test_get_alert(self) -> bool:
        """Test getting a specific alert."""
        if not self.created_alert_id:
            logger.warning("No alert ID available, skipping test")
            self.test_results.append(("Get Alert", False, "No alert ID available"))
            return False
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/alerting/alerts/{self.created_alert_id}",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                alert_title = data.get("alert", {}).get("title")
                logger.info(f"✅ Alert retrieved successfully: {alert_title}")
                self.test_results.append(("Get Alert", True, f"Alert: {alert_title}"))
                return True
            else:
                logger.error(f"❌ Alert retrieval failed: {response.status_code} - {response.text}")
                self.test_results.append(("Get Alert", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert retrieval error: {e}")
            self.test_results.append(("Get Alert", False, str(e)))
            return False
    
    async def test_resolve_alert(self) -> bool:
        """Test resolving an alert."""
        if not self.created_alert_id:
            logger.warning("No alert ID available, skipping test")
            self.test_results.append(("Resolve Alert", False, "No alert ID available"))
            return False
        
        try:
            resolution_data = {
                "resolved_by": "test-user",
                "note": "Test resolution from automated test"
            }
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/alerting/alerts/{self.created_alert_id}/resolve",
                headers=HEADERS,
                json=resolution_data
            )
            
            if response.status_code == 200:
                data = response.json()
                resolved_by = data.get("resolved_by")
                logger.info(f"✅ Alert resolved successfully by {resolved_by}")
                self.test_results.append(("Resolve Alert", True, f"Resolved by {resolved_by}"))
                return True
            else:
                logger.error(f"❌ Alert resolution failed: {response.status_code} - {response.text}")
                self.test_results.append(("Resolve Alert", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert resolution error: {e}")
            self.test_results.append(("Resolve Alert", False, str(e)))
            return False
    
    async def test_alert_stats(self) -> bool:
        """Test getting alert statistics."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/alerting/stats",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get("stats", {})
                total_alerts = stats.get("total_alerts", 0)
                total_rules = stats.get("total_rules", 0)
                logger.info(f"✅ Alert stats retrieved: {total_alerts} alerts, {total_rules} rules")
                self.test_results.append(("Alert Stats", True, f"{total_alerts} alerts, {total_rules} rules"))
                return True
            else:
                logger.error(f"❌ Alert stats retrieval failed: {response.status_code} - {response.text}")
                self.test_results.append(("Alert Stats", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert stats retrieval error: {e}")
            self.test_results.append(("Alert Stats", False, str(e)))
            return False
    
    async def test_update_alert_rule(self) -> bool:
        """Test updating an alert rule."""
        if not self.created_rule_id:
            logger.warning("No rule ID available, skipping test")
            self.test_results.append(("Update Alert Rule", False, "No rule ID available"))
            return False
        
        try:
            update_data = {
                "description": "Updated description for testing",
                "severity": "high"
            }
            
            response = await self.client.put(
                f"{BASE_URL}/api/v1/alerting/rules/{self.created_rule_id}",
                headers=HEADERS,
                json=update_data
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Alert rule updated successfully")
                self.test_results.append(("Update Alert Rule", True, "Rule updated"))
                return True
            else:
                logger.error(f"❌ Alert rule update failed: {response.status_code} - {response.text}")
                self.test_results.append(("Update Alert Rule", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert rule update error: {e}")
            self.test_results.append(("Update Alert Rule", False, str(e)))
            return False
    
    async def test_delete_alert_rule(self) -> bool:
        """Test deleting an alert rule."""
        if not self.created_rule_id:
            logger.warning("No rule ID available, skipping test")
            self.test_results.append(("Delete Alert Rule", False, "No rule ID available"))
            return False
        
        try:
            response = await self.client.delete(
                f"{BASE_URL}/api/v1/alerting/rules/{self.created_rule_id}",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Alert rule deleted successfully")
                self.test_results.append(("Delete Alert Rule", True, "Rule deleted"))
                return True
            else:
                logger.error(f"❌ Alert rule deletion failed: {response.status_code} - {response.text}")
                self.test_results.append(("Delete Alert Rule", False, f"Status: {response.status_code}"))
                return False
                
        except Exception as e:
            logger.error(f"❌ Alert rule deletion error: {e}")
            self.test_results.append(("Delete Alert Rule", False, str(e)))
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all alert system tests."""
        logger.info("🚀 Starting PulseStream Alert Management System Tests")
        
        tests = [
            self.test_create_alert_rule,
            self.test_list_alert_rules,
            self.test_get_alert_rule,
            self.test_test_alert_rule,
            self.test_evaluate_all_rules,
            self.test_list_alerts,
            self.test_get_alert,
            self.test_resolve_alert,
            self.test_alert_stats,
            self.test_update_alert_rule,
            self.test_delete_alert_rule
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
    tester = AlertSystemTester()
    
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
            print("\n🎉 Excellent! Alert Management System is working perfectly!")
        elif summary['success_rate'] >= 70:
            print("\n👍 Good! Most alert features are working.")
        else:
            print("\n⚠️  Some alert features need attention.")
        
        return summary['success_rate'] >= 90
        
    finally:
        await tester.close()

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
