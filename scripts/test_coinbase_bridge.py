"""
Test script for Coinbase WebSocket Bridge

This script tests the connectivity and functionality of the Coinbase bridge
by verifying:
1. PulseStream API is reachable
2. Authentication is working
3. Event ingestion endpoint is functional
4. Coinbase WebSocket is accessible
"""

import sys
import json
import requests
from datetime import datetime

# Configuration (same as in coinbase_bridge.py)
PULSESTREAM_API_URL = "http://localhost:8000/api/v1/ingestion/events"
PULSESTREAM_HEALTH_URL = "http://localhost:8000/api/v1/ingestion/health"
API_KEY = "YOUR_TENANT_API_KEY"  # Replace with actual tenant API key

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def test_pulsestream_health():
    """Test if PulseStream API is reachable and healthy."""
    print("\n1️⃣  Testing PulseStream API Health...")
    print(f"   URL: {PULSESTREAM_HEALTH_URL}")
    
    try:
        response = requests.get(PULSESTREAM_HEALTH_URL, timeout=5)
        
        if response.status_code == 200:
            print("   ✅ PulseStream API is healthy")
            data = response.json()
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Queue Size: {data.get('queue_size', 'N/A')}")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Cannot connect to PulseStream API")
        print(f"   Make sure PulseStream is running: docker-compose ps")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout - API is too slow to respond")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def test_authentication():
    """Test if API key authentication is working."""
    print("\n2️⃣  Testing API Authentication...")
    print(f"   API Key: {API_KEY[:20]}..." if len(API_KEY) > 20 else API_KEY)
    
    if API_KEY == "YOUR_TENANT_API_KEY":
        print("   ⚠️  Using placeholder API key - authentication will likely fail")
        print("   Please update API_KEY in this script and coinbase_bridge.py")
        return False
    
    # Test with rate limit endpoint (requires authentication)
    rate_limit_url = "http://localhost:8000/api/v1/ingestion/rate-limit"
    
    try:
        response = requests.get(rate_limit_url, headers=HEADERS, timeout=5)
        
        if response.status_code == 200:
            print("   ✅ Authentication successful")
            data = response.json()
            print(f"   Rate Limit: {data.get('limit', 'N/A')} events/min")
            print(f"   Remaining: {data.get('remaining', 'N/A')}")
            return True
        elif response.status_code == 401:
            print(f"   ❌ Authentication failed: Invalid API key")
            return False
        elif response.status_code == 403:
            print(f"   ❌ Authentication failed: Access forbidden")
            return False
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing authentication: {e}")
        return False


def test_event_ingestion():
    """Test if event ingestion endpoint is functional."""
    print("\n3️⃣  Testing Event Ingestion...")
    print(f"   URL: {PULSESTREAM_API_URL}")
    
    # Create a test event similar to what coinbase_bridge.py sends
    test_event = {
        "event_type": "api_request",
        "event_id": f"test-bridge-{datetime.utcnow().timestamp()}",
        "title": "Test Event: Coinbase Bridge Verification",
        "message": "This is a test event to verify the Coinbase bridge setup",
        "severity": "info",
        "source": {
            "service": "coinbase-bridge-test",
            "endpoint": "/test",
            "method": "POST",
            "version": "v1",
            "environment": "testing"
        },
        "context": {
            "request_id": "test-request-123",
            "tags": {
                "test": "true",
                "source": "bridge-test-script"
            }
        },
        "metrics": {
            "response_time_ms": 100.0,
            "status_code": 200
        },
        "payload": {
            "test": True,
            "message": "If you see this event in PulseStream, the bridge setup is working!"
        },
        "metadata": {
            "test_run": True
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        response = requests.post(
            PULSESTREAM_API_URL,
            json=test_event,
            headers=HEADERS,
            timeout=5
        )
        
        if response.status_code in (200, 201):
            print("   ✅ Event ingestion successful")
            data = response.json()
            print(f"   Event ID: {data.get('event_id', 'N/A')}")
            print(f"   Status: {data.get('processing_status', 'N/A')}")
            print(f"   Message: {data.get('message', 'N/A')}")
            return True
        else:
            print(f"   ❌ Event ingestion failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing event ingestion: {e}")
        return False


def test_coinbase_websocket():
    """Test if Coinbase WebSocket is accessible."""
    print("\n4️⃣  Testing Coinbase WebSocket Connectivity...")
    print("   URL: wss://ws-feed.exchange.coinbase.com")
    
    try:
        import websocket
        
        # Simple test to see if we can establish connection
        # We'll connect and immediately close
        ws = websocket.create_connection(
            "wss://ws-feed.exchange.coinbase.com",
            timeout=5
        )
        
        print("   ✅ Coinbase WebSocket is accessible")
        ws.close()
        return True
        
    except ImportError:
        print("   ❌ websocket-client library not installed")
        print("   Install with: pip install websocket-client")
        return False
    except Exception as e:
        print(f"   ❌ Cannot connect to Coinbase WebSocket: {e}")
        print("   Check your internet connection and firewall settings")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 Coinbase WebSocket Bridge - Setup Test")
    print("=" * 70)
    
    results = {
        "health": test_pulsestream_health(),
        "auth": test_authentication(),
        "ingestion": test_event_ingestion(),
        "websocket": test_coinbase_websocket()
    }
    
    print("\n" + "=" * 70)
    print("📊 Test Results Summary")
    print("=" * 70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name.capitalize()}")
    
    all_passed = all(results.values())
    
    print("=" * 70)
    if all_passed:
        print("🎉 All tests passed! The Coinbase bridge is ready to run.")
        print("\nNext steps:")
        print("1. Run the bridge: python coinbase_bridge.py")
        print("2. Monitor the output for ticker updates")
        print("3. Check PulseStream dashboard for ingested events")
    else:
        print("⚠️  Some tests failed. Please fix the issues before running the bridge.")
        print("\nTroubleshooting:")
        
        if not results["health"]:
            print("- Start PulseStream: docker-compose up -d")
            print("- Wait for services to be healthy: docker-compose ps")
        
        if not results["auth"]:
            print("- Update API_KEY in scripts/test_coinbase_bridge.py")
            print("- Update API_KEY in coinbase_bridge.py")
            print("- Verify the key is valid and has ingestion permissions")
        
        if not results["ingestion"]:
            print("- Check PulseStream logs: docker-compose logs api")
            print("- Verify the ingestion endpoint is enabled")
        
        if not results["websocket"]:
            print("- Install websocket-client: pip install websocket-client")
            print("- Check internet connection")
            print("- Verify no proxy/firewall blocking WebSocket connections")
    
    print("=" * 70)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

