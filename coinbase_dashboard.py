#!/usr/bin/env python3
"""
🚀 COINBASE LIVE CRYPTOCURRENCY DASHBOARD 🚀
Real-time prices from Coinbase Exchange via PulseStream
"""

import requests
import json
from datetime import datetime

# Configuration
API_KEY = "jK8uQrmyzBJeT7l5cMfhBePlqu_uh4_jsIAP_YhNWaU"
HEADERS = {"X-API-Key": API_KEY}
API_URL = "http://localhost:8000"

def fetch_latest_events(limit=50):
    """Fetch latest Coinbase events"""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/ingestion/events/search",
            headers=HEADERS,
            params={
                "event_type": "custom_event",
                "service": "coinbase-exchange",
                "limit": limit
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("events", [])
        return []
    except Exception as e:
        print(f"[ERROR] {e}")
        return []

def display_dashboard():
    """Display the crypto dashboard"""
    events = fetch_latest_events(50)
    
    print("\n" + "=" * 110)
    print(" " * 35 + "COINBASE LIVE CRYPTOCURRENCY DASHBOARD")
    print("=" * 110)
    print(f"\n[TIME] Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[DATA] Total Events: {len(events)}")
    
    if not events:
        print("\n[WARNING] No events found! Make sure the Coinbase bridge is running.")
        print("          Run: python coinbase_bridge.py")
        return
    
    # Extract latest prices per cryptocurrency
    latest_prices = {}
    for event in events:
        try:
            payload = event.get("payload", {})
            custom_data = payload.get("custom_data", {})
            
            product_id = custom_data.get("product_id", "UNKNOWN")
            price = custom_data.get("price", 0.0)
            volume_24h = custom_data.get("volume_24h", 0.0)
            spread = custom_data.get("spread", 0.0)
            best_bid = custom_data.get("best_bid", 0.0)
            best_ask = custom_data.get("best_ask", 0.0)
            low_24h = float(custom_data.get("low_24h", 0))
            high_24h = float(custom_data.get("high_24h", 0))
            timestamp = event.get("timestamp", "")
            
            if product_id != "UNKNOWN" and product_id not in latest_prices:
                latest_prices[product_id] = {
                    "price": price,
                    "volume": volume_24h,
                    "spread": spread,
                    "bid": best_bid,
                    "ask": best_ask,
                    "low": low_24h,
                    "high": high_24h,
                    "timestamp": timestamp
                }
        except Exception as e:
            continue
    
    # Display live prices
    print("\n" + "-" * 110)
    print(f"{'CRYPTOCURRENCY':<15} {'CURRENT PRICE':<18} {'24H LOW':<15} {'24H HIGH':<15} {'24H VOLUME':<18} {'SPREAD':<12}")
    print("-" * 110)
    
    for product_id in sorted(latest_prices.keys()):
        data = latest_prices[product_id]
        
        # Format with prefix
        if "BTC" in product_id:
            prefix = "[B]"
        elif "ETH" in product_id:
            prefix = "[E]"
        else:
            prefix = "   "
        
        price_str = f"${data['price']:,.2f}"
        low_str = f"${data['low']:,.2f}"
        high_str = f"${data['high']:,.2f}"
        volume_str = f"${data['volume']:,.0f}"
        spread_str = f"${data['spread']:.2f}"
        
        print(f"{prefix} {product_id:<11} {price_str:<18} {low_str:<15} {high_str:<15} {volume_str:<18} {spread_str:<12}")
    
    print("-" * 110)
    
    # Display market statistics
    print("\n[STATS] MARKET STATISTICS:")
    print("-" * 110)
    for product_id, data in sorted(latest_prices.items()):
        low = data['low']
        high = data['high']
        current = data['price']
        
        if high > low and low > 0:
            range_pct = ((high - low) / low) * 100
            position = ((current - low) / (high - low)) * 100 if high != low else 50
            
            print(f"  {product_id:<12} | Current: ${current:>10,.2f}  |  ", end="")
            print(f"24h Range: ${low:>8,.2f} - ${high:>10,.2f}  ({range_pct:>5.2f}% range)  |  ", end="")
            print(f"Position: {position:>5.1f}% of range")
    
    print("-" * 110)
    
    # Display recent updates
    print("\n[UPDATES] RECENT PRICE UPDATES (Last 15):")
    print("-" * 110)
    print(f"{'#':<4} {'TIME':<20} {'PRODUCT':<12} {'PRICE':<15} {'MESSAGE':<47}")
    print("-" * 110)
    
    count = 0
    for event in events:
        if count >= 15:
            break
        try:
            payload = event.get("payload", {})
            custom_data = payload.get("custom_data", {})
            
            product_id = custom_data.get("product_id")
            price = custom_data.get("price")
            message = payload.get("message", "")
            timestamp = event.get("timestamp", "")[:19].replace("T", " ")
            
            if product_id and price:
                count += 1
                print(f"{count:<4} {timestamp:<20} {product_id:<12} ${price:>12,.2f}  {message[:45]:<47}")
        except:
            continue
    
    print("-" * 110)
    print("\n[TIPS]")
    print("   * This data is streaming live from Coinbase Exchange")
    print("   * No authentication required for Coinbase (public market data)")
    print("   * Data updates automatically in PulseStream")
    print("   * View in browser: http://localhost:8000")
    print("\n" + "=" * 110 + "\n")

if __name__ == "__main__":
    try:
        display_dashboard()
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Dashboard closed by user.\n")
    except Exception as e:
        print(f"\n[ERROR] {e}\n")

