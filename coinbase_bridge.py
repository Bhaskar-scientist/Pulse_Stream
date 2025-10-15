"""
Coinbase WebSocket Bridge for PulseStream

This script connects to the Coinbase Exchange WebSocket API, listens for real-time
market data (ticker updates), and forwards the data to the PulseStream ingestion API
for processing and analytics.

AUTHENTICATION REQUIREMENTS:
- Coinbase WebSocket: NO authentication required for public market data
  (ticker, level2, candles, market_trades, heartbeats, status channels)
- PulseStream API: REQUIRES Bearer token authentication (API_KEY)

Features:
- Real-time WebSocket connection to Coinbase Exchange (public data)
- Subscribes to BTC-USD and ETH-USD ticker channels
- Transforms Coinbase ticker data to PulseStream event format
- Asynchronous HTTP POST to PulseStream API using threading
- Comprehensive error handling and logging
- Robust data type conversion with safe_float helper
"""

import json
import os
import time
import threading
import uuid
from datetime import datetime
from typing import Dict, Any

import websocket
import requests


# ============================================================================
# CONFIGURATION
# ============================================================================

# IMPORTANT: Coinbase Public Market Data API (NO AUTHENTICATION REQUIRED)
# The Coinbase WebSocket feed for public market data (ticker, level2, candles, etc.)
# does NOT require authentication. We connect directly without API keys.
# See: https://docs.cloud.coinbase.com/advanced-trade-api/docs/websocket-overview
#
# AUTHENTICATION ONLY REQUIRED FOR: PulseStream API (below)
# The API_KEY is used ONLY for authenticating with your PulseStream instance,
# not for Coinbase.

# PulseStream API Configuration (REQUIRES AUTHENTICATION)
# Can be overridden with environment variables
PULSESTREAM_API_URL = os.getenv(
    "PULSESTREAM_API_URL",
    "http://localhost:8000/api/v1/ingestion/events"
)
API_KEY = os.getenv(
    "PULSESTREAM_API_KEY",
    "jK8uQrmyzBJeT7l5cMfhBePlqu_uh4_jsIAP_YhNWaU"  # API key for 'Coinbase Data Stream' tenant
)

# Coinbase WebSocket Configuration (NO AUTHENTICATION - Public Feed)
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Subscription message for Coinbase WebSocket
# Subscribe to ticker channel for BTC-USD and ETH-USD
# NOTE: No authentication fields required for public channels
SUBSCRIPTION_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ETH-USD"],
    "channels": ["ticker"]
    # Public channels available: ticker, level2, candles, market_trades, heartbeats, status
}

# Request headers for PulseStream API (NOT sent to Coinbase)
# PulseStream uses X-API-Key header for tenant authentication
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


# ============================================================================
# PULSESTREAM API CLIENT
# ============================================================================

def send_to_pulsestream(event: Dict[str, Any], headers: Dict[str, str]) -> None:
    """
    Send a transformed event to the PulseStream ingestion API.
    
    This function runs in a separate thread to prevent blocking the WebSocket
    listener while waiting for the HTTP response.
    
    Args:
        event: The transformed event data in PulseStream format
        headers: HTTP headers including authentication token
    """
    try:
        # Send POST request to PulseStream ingestion API
        response = requests.post(
            PULSESTREAM_API_URL,
            json=event,
            headers=headers,
            timeout=5  # 5-second timeout to prevent hanging
        )
        
        # Limit response text for logging
        response_text = response.text[:100].replace('\n', ' ')
        
        # Check response status (200 OK, 201 Created, 202 Accepted)
        if response.status_code in (200, 201, 202):
            print(f"[SUCCESS] Event sent successfully ({response.status_code}) | "
                  f"{event['title']} | Price: ${event['payload']['price']:.2f}")
        else:
            print(f"[FAILURE] Failed to send event | "
                  f"HTTP {response.status_code} | Response: {response_text}")
            
    except requests.exceptions.Timeout:
        print(f"[ERROR] Request timeout when sending event: {event.get('title', 'Unknown')}")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Connection error: Unable to reach PulseStream API at {PULSESTREAM_API_URL}. "
              f"Is the service running?")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request error while sending event: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error in send_to_pulsestream: {e}")


# ============================================================================
# DATA TRANSFORMATION
# ============================================================================

def transform_ticker_to_event(ticker_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform Coinbase ticker data into PulseStream event format.
    
    Converts the raw Coinbase ticker message into a structured event that
    matches the PulseStream EventIngestionRequest schema.
    
    Handles missing/invalid numeric data gracefully with safe_float conversion.
    
    Args:
        ticker_data: Raw ticker data from Coinbase WebSocket
        
    Returns:
        Transformed event in PulseStream format
    """
    # Safely extract string fields
    product_id = ticker_data.get("product_id", "UNKNOWN")
    last_trade_id = ticker_data.get("trade_id")
    # Get timestamp and remove timezone info ("Z") to match PulseStream's timezone-naive format
    timestamp_raw = ticker_data.get("time", datetime.utcnow().isoformat())
    timestamp = timestamp_raw.rstrip("Z") if timestamp_raw.endswith("Z") else timestamp_raw
    
    # Safe float conversion helper
    def safe_float(key: str, default: float = 0.0) -> float:
        """Convert string to float, return default if missing or invalid."""
        try:
            value = ticker_data.get(key, default)
            if value is None or value == "":
                return default
            result = float(value)
            # Check for NaN and infinity
            if result != result or result == float('inf') or result == float('-inf'):
                return default
            return result
        except (ValueError, TypeError):
            return default
    
    # Extract and convert numeric fields with safe conversion
    price = safe_float("price")
    volume_24h = safe_float("volume_24h")
    best_bid = safe_float("best_bid")
    best_ask = safe_float("best_ask")
    
    # Calculate spread metric
    spread = best_ask - best_bid if best_ask and best_bid else 0.0
    
    # Generate unique event ID (use trade_id if available, otherwise UUID)
    if last_trade_id:
        event_id = f"coinbase-{product_id}-{last_trade_id}"
    else:
        event_id = f"coinbase-{product_id}-{uuid.uuid4()}"
    
    # Create PulseStream-compatible event
    event = {
        "event_type": "custom_event",  # Valid EventType from core.constants.EventType
        "event_id": event_id,
        "title": f"Coinbase Price Update: {product_id}",
        "message": f"Real-time price update for {product_id}: ${price:.2f}. "
                   f"Volume (24h): ${volume_24h:.2f}",
        "severity": "info",
        
        # Source information
        "source": {
            "service": "coinbase-exchange",
            "endpoint": "/ticker",
            "method": "WEBSOCKET",
            "version": "v1",
            "environment": "production"
        },
        
        # Context information
        "context": {
            "request_id": event_id,
            "tags": {
                "product_id": product_id,
                "source": "coinbase",
                "channel": "ticker"
            }
        },
        
        # Metrics (top-level for analytics)
        "metrics": {
            "response_time_ms": 0.0,  # WebSocket has no response time
            "status_code": 200,  # Simulated success status
            "price": price,
            "volume_24h": volume_24h,
            "spread": spread
        },
        
        # Payload with all Coinbase ticker data
        "payload": {
            "product_id": product_id,
            "price": price,
            "volume_24h": volume_24h,
            "last_trade_id": last_trade_id,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "low_24h": ticker_data.get("low_24h"),
            "high_24h": ticker_data.get("high_24h"),
            "open_24h": ticker_data.get("open_24h"),
            "last_size": ticker_data.get("last_size"),
            "raw_ticker": ticker_data  # Include full raw data for reference
        },
        
        # Metadata
        "metadata": {
            "source_system": "coinbase-websocket-bridge",
            "bridge_version": "1.0.0",
            "processed_at": datetime.utcnow().isoformat(),
            "no_coinbase_auth_required": True  # Documentation flag
        },
        
        # Timestamp
        "timestamp": timestamp
    }
    
    return event


# ============================================================================
# WEBSOCKET EVENT HANDLERS
# ============================================================================

def on_message(ws: websocket.WebSocketApp, message: str) -> None:
    """
    Handle incoming WebSocket messages from Coinbase.
    
    This callback is triggered whenever a message is received from the
    Coinbase WebSocket. It parses the message, filters for ticker events,
    transforms the data, and sends it to PulseStream asynchronously.
    
    Args:
        ws: The WebSocketApp instance
        message: Raw message string from Coinbase
    """
    try:
        # Parse JSON message
        data = json.loads(message)
        message_type = data.get("type")
        
        # Filter for ticker messages
        if message_type == "ticker":
            product_id = data.get("product_id", "UNKNOWN")
            price = data.get("price", "N/A")
            
            print(f"[TICKER] Received ticker update: {product_id} @ ${price}")
            
            # Transform ticker data to PulseStream event format
            event = transform_ticker_to_event(data)
            
            # Send to PulseStream asynchronously (non-blocking)
            # Using threading to prevent WebSocket listener from being blocked
            thread = threading.Thread(
                target=send_to_pulsestream,
                args=(event, HEADERS),
                daemon=True  # Thread dies when main program exits
            )
            thread.start()
            
        elif message_type == "subscriptions":
            # Confirmation message from Coinbase
            channels = data.get("channels", [])
            print(f"[OK] Subscription confirmed: {json.dumps(channels, indent=2)}")
            
        elif message_type == "error":
            # Error message from Coinbase
            error_msg = data.get("message", "Unknown error")
            print(f"[ALERT] Coinbase error: {error_msg}")
            
    except json.JSONDecodeError as e:
        print(f"[WARNING] Failed to parse WebSocket message: {e}")
        print(f"[WARNING] Message preview: {message[:50]}...")
    except Exception as e:
        print(f"[FATAL] Error processing WebSocket message: {e}")


def on_open(ws: websocket.WebSocketApp) -> None:
    """
    Handle WebSocket connection opened event.
    
    This callback is triggered when the WebSocket connection is successfully
    established. It sends the subscription message to Coinbase to start
    receiving ticker updates.
    
    NOTE: No authentication required for public market data channels.
    
    Args:
        ws: The WebSocketApp instance
    """
    print(f"[CONNECTED] WebSocket connection established to {COINBASE_WS_URL}")
    print(f"[SUBSCRIBING] Subscribing to ticker channel for BTC-USD and ETH-USD...")
    print(f"[INFO] Public channel - no authentication required")
    
    # Send subscription message (no auth fields needed)
    try:
        ws.send(json.dumps(SUBSCRIPTION_MESSAGE))
        print(f"[OK] Subscription message sent successfully")
    except Exception as e:
        print(f"[ERROR] Failed to send subscription message: {e}")


def on_error(ws: websocket.WebSocketApp, error: Exception) -> None:
    """
    Handle WebSocket errors.
    
    This callback is triggered when an error occurs in the WebSocket connection.
    
    Args:
        ws: The WebSocketApp instance
        error: The error that occurred
    """
    print(f"[WS ERROR] Coinbase WebSocket Error: {error}")


def on_close(ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
    """
    Handle WebSocket connection closed event.
    
    This callback is triggered when the WebSocket connection is closed.
    
    Args:
        ws: The WebSocketApp instance
        close_status_code: Status code for connection closure
        close_msg: Message describing the closure reason
    """
    print(f"[CLOSED] WebSocket connection closed")
    print(f"   Status Code: {close_status_code}")
    print(f"   Message: {close_msg}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main entry point for the Coinbase WebSocket bridge.
    
    Creates a WebSocket connection to Coinbase Exchange and starts listening
    for real-time market data. The connection runs indefinitely until manually
    stopped (Ctrl+C) or an error occurs.
    """
    print("=" * 80)
    print("Coinbase WebSocket Bridge for PulseStream")
    print("=" * 80)
    print(f"Target API: {PULSESTREAM_API_URL}")
    print(f"WebSocket: {COINBASE_WS_URL}")
    print(f"Products: BTC-USD, ETH-USD")
    print(f"Channel: ticker (public - no auth required)")
    print("=" * 80)
    print()
    print("AUTHENTICATION INFO:")
    print("   [OK] Coinbase: NO authentication required (public market data)")
    print("   [KEY] PulseStream: X-API-Key header authentication required")
    print("=" * 80)
    print()
    
    # Validate API key
    if API_KEY == "YOUR_TENANT_API_KEY":
        print("[WARNING] Using placeholder API key for PulseStream.")
        print("   Set PULSESTREAM_API_KEY environment variable or update API_KEY constant.")
        print()
    
    # Create WebSocketApp instance with callback functions
    ws_app = websocket.WebSocketApp(
        COINBASE_WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Start WebSocket connection
    # run_forever() blocks until the connection is closed
    try:
        print("[STARTING] Starting WebSocket connection...")
        print("   Press Ctrl+C to stop")
        print()
        
        # Run WebSocket connection with automatic reconnection
        ws_app.run_forever(
            reconnect=5,  # Automatically reconnect after 5 seconds if connection drops
            ping_interval=30,  # Send ping every 30 seconds to keep connection alive
            ping_timeout=10  # Wait 10 seconds for pong response
        )
        
    except KeyboardInterrupt:
        print()
        print("[STOP] Shutting down Coinbase bridge (interrupted by user)...")
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
    finally:
        print("[STOPPED] Coinbase WebSocket bridge stopped")


if __name__ == "__main__":
    main()
