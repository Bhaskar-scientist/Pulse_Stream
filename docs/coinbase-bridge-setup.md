# Coinbase WebSocket Bridge Setup Guide

## Overview

The Coinbase WebSocket Bridge is a standalone Python script that connects to the Coinbase Exchange WebSocket API, listens for real-time market data, and forwards it to the PulseStream ingestion API for processing and analytics.

## Features

- ✅ Real-time WebSocket connection to Coinbase Exchange
- ✅ Subscribes to BTC-USD and ETH-USD ticker channels
- ✅ Transforms Coinbase ticker data to PulseStream event format
- ✅ Asynchronous HTTP POST to PulseStream API using threading
- ✅ Comprehensive error handling and logging
- ✅ Automatic reconnection on connection drops
- ✅ Keep-alive pings to maintain connection

## Prerequisites

1. **PulseStream Platform**: Ensure the PulseStream platform is running
2. **Python 3.8+**: The script requires Python 3.8 or higher
3. **Network Access**: Ability to connect to Coinbase WebSocket and PulseStream API
4. **API Key**: A valid PulseStream tenant API key

## Installation

### 1. Install Dependencies

```bash
pip install -r coinbase_bridge_requirements.txt
```

Or manually install:

```bash
pip install websocket-client>=1.6.0 requests>=2.31.0
```

### 2. Configure API Key

Open `coinbase_bridge.py` and update the API key:

```python
API_KEY = "YOUR_TENANT_API_KEY"  # Replace with actual tenant API key
```

To get your API key:
1. Log in to PulseStream platform
2. Navigate to Settings > API Keys
3. Create a new API key or copy existing one
4. Paste it into the `API_KEY` constant

### 3. Verify PulseStream API Endpoint

By default, the script connects to:
```
http://localhost:8000/api/v1/ingestion/events
```

If your PulseStream API is hosted elsewhere, update the `PULSESTREAM_API_URL` constant:

```python
PULSESTREAM_API_URL = "https://your-pulsestream-domain.com/api/v1/ingestion/events"
```

## Usage

### Start the Bridge

```bash
python coinbase_bridge.py
```

### Expected Output

```
======================================================================
🚀 Coinbase WebSocket Bridge for PulseStream
======================================================================
Target API: http://localhost:8000/api/v1/ingestion/events
WebSocket: wss://ws-feed.exchange.coinbase.com
Products: BTC-USD, ETH-USD
Channel: ticker
======================================================================

🔄 Starting WebSocket connection...
   Press Ctrl+C to stop

🔗 WebSocket connection established to wss://ws-feed.exchange.coinbase.com
📡 Subscribing to ticker channel for BTC-USD and ETH-USD...
✓ Subscription message sent successfully
✓ Subscription confirmed: [
  {
    "name": "ticker",
    "product_ids": ["BTC-USD", "ETH-USD"]
  }
]
📊 Received ticker update: BTC-USD @ $45234.56
✓ Event sent successfully: Coinbase Price Update: BTC-USD | Price: $45234.56 | Status: 200
📊 Received ticker update: ETH-USD @ $2891.23
✓ Event sent successfully: Coinbase Price Update: ETH-USD | Price: $2891.23 | Status: 200
```

### Stop the Bridge

Press `Ctrl+C` to gracefully stop the bridge:

```
⏹️  Shutting down Coinbase bridge (interrupted by user)...
👋 Coinbase WebSocket bridge stopped
```

## How It Works

### 1. WebSocket Connection

The script establishes a WebSocket connection to Coinbase Exchange:
- URL: `wss://ws-feed.exchange.coinbase.com`
- Subscribes to the `ticker` channel
- Monitors BTC-USD and ETH-USD product pairs

### 2. Data Transformation

Each incoming ticker message is transformed into PulseStream event format:

**Coinbase Ticker Data (Input):**
```json
{
  "type": "ticker",
  "product_id": "BTC-USD",
  "price": "45234.56",
  "volume_24h": "12345.67",
  "trade_id": 123456789,
  "best_bid": "45234.50",
  "best_ask": "45234.60",
  "time": "2025-10-06T12:34:56.789Z"
}
```

**PulseStream Event (Output):**
```json
{
  "event_type": "api_request",
  "event_id": "coinbase-BTC-USD-123456789",
  "title": "Coinbase Price Update: BTC-USD",
  "message": "Real-time price update for BTC-USD: $45234.56",
  "severity": "info",
  "source": {
    "service": "coinbase-exchange",
    "endpoint": "/ticker",
    "method": "WEBSOCKET",
    "version": "v1",
    "environment": "production"
  },
  "payload": {
    "product_id": "BTC-USD",
    "price": 45234.56,
    "volume_24h": 12345.67,
    "last_trade_id": 123456789,
    "best_bid": 45234.50,
    "best_ask": 45234.60,
    "spread": 0.10
  }
}
```

### 3. Asynchronous Ingestion

- Each event is sent to PulseStream API via HTTP POST
- Uses threading to prevent blocking the WebSocket listener
- Includes authentication via Bearer token
- Handles timeouts and connection errors gracefully

## Configuration Options

### Change Monitored Products

To monitor different cryptocurrency pairs, update the `SUBSCRIPTION_MESSAGE`:

```python
SUBSCRIPTION_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"],
    "channels": ["ticker"]
}
```

### Subscribe to Additional Channels

Coinbase supports multiple channels. To subscribe to more:

```python
SUBSCRIPTION_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ETH-USD"],
    "channels": ["ticker", "matches", "heartbeat"]
}
```

**Note:** You'll need to update the `on_message` handler to process additional channel types.

### Adjust Reconnection Settings

Modify the `run_forever()` parameters in the `main()` function:

```python
ws_app.run_forever(
    reconnect=10,      # Wait 10 seconds before reconnecting
    ping_interval=60,  # Send ping every 60 seconds
    ping_timeout=20    # Wait 20 seconds for pong
)
```

### Adjust HTTP Request Timeout

In the `send_to_pulsestream()` function:

```python
response = requests.post(
    PULSESTREAM_API_URL,
    json=event,
    headers=headers,
    timeout=10  # Increase to 10 seconds
)
```

## Troubleshooting

### Connection Errors

**Problem:** `Connection error: Unable to reach PulseStream API`

**Solutions:**
1. Verify PulseStream is running: `docker-compose ps`
2. Check the API URL is correct
3. Ensure no firewall is blocking the connection
4. Test the endpoint manually:
   ```bash
   curl -X GET http://localhost:8000/api/v1/health
   ```

### Authentication Errors

**Problem:** `Failed to send event: 401` or `403`

**Solutions:**
1. Verify the API key is correct
2. Ensure the API key has ingestion permissions
3. Check the key hasn't expired
4. Test authentication:
   ```bash
   curl -X GET http://localhost:8000/api/v1/ingestion/health \
        -H "Authorization: Bearer YOUR_API_KEY"
   ```

### WebSocket Connection Issues

**Problem:** `WebSocket error` or connection keeps dropping

**Solutions:**
1. Check internet connectivity
2. Verify Coinbase WebSocket URL is correct
3. Check if you're behind a proxy that blocks WebSockets
4. Review Coinbase API status: https://status.coinbase.com/

### No Ticker Messages

**Problem:** WebSocket connects but no ticker messages received

**Solutions:**
1. Verify subscription message was sent successfully
2. Check product IDs are valid (BTC-USD, ETH-USD)
3. Ensure the `ticker` channel is supported
4. Look for error messages from Coinbase

## Integration with PulseStream

### View Ingested Data

Once the bridge is running, you can view the ingested data in PulseStream:

1. **Dashboard:** Navigate to the real-time dashboard
2. **Event Search:** Use the event search API:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/ingestion/events/search?service=coinbase-exchange&limit=10" \
        -H "Authorization: Bearer YOUR_API_KEY"
   ```

### Set Up Alerts

Configure alerts in PulseStream for specific conditions:

- Price thresholds (e.g., BTC-USD > $50,000)
- Rapid price changes
- Volume spikes
- Spread anomalies

### Analytics Queries

Query the ingested data using PulseStream's analytics API:

```bash
# Get average BTC price over last hour
curl -X GET "http://localhost:8000/api/v1/dashboard/metrics?metric=avg_price&product=BTC-USD&timeframe=1h" \
     -H "Authorization: Bearer YOUR_API_KEY"
```

## Performance Considerations

### Throughput

- **Ticker Updates:** ~1-5 messages per second per product
- **Network Overhead:** ~1-2 KB per message
- **HTTP Requests:** Asynchronous, non-blocking
- **Memory Usage:** ~50-100 MB

### Scaling

To handle more products or higher throughput:

1. **Run Multiple Instances:** Deploy multiple bridge instances for different products
2. **Load Balancing:** Use a load balancer for PulseStream API
3. **Connection Pooling:** Use `requests.Session()` for connection reuse
4. **Batching:** Accumulate events and send in batches

## Production Deployment

### Running as a Service (Linux)

Create a systemd service file `/etc/systemd/system/coinbase-bridge.service`:

```ini
[Unit]
Description=Coinbase WebSocket Bridge for PulseStream
After=network.target

[Service]
Type=simple
User=pulsestream
WorkingDirectory=/opt/pulsestream
ExecStart=/usr/bin/python3 /opt/pulsestream/coinbase_bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable coinbase-bridge
sudo systemctl start coinbase-bridge
sudo systemctl status coinbase-bridge
```

### Using Docker

Create a `Dockerfile` for the bridge:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY coinbase_bridge_requirements.txt .
RUN pip install --no-cache-dir -r coinbase_bridge_requirements.txt

COPY coinbase_bridge.py .

CMD ["python", "coinbase_bridge.py"]
```

Build and run:
```bash
docker build -t coinbase-bridge .
docker run -d --name coinbase-bridge \
  --network pulsestream_default \
  coinbase-bridge
```

### Using Docker Compose (Recommended for Production)

The Coinbase bridge is already included in the `docker-compose.yml` file under the `integrations` profile.

1. **Set API key in `.env` file**:
   ```bash
   COINBASE_BRIDGE_API_KEY=your-pulsestream-tenant-api-key
   ```

2. **Start the bridge with PulseStream**:
   ```bash
   # Start PulseStream with Coinbase bridge
   docker-compose --profile integrations up -d
   
   # Or start just the bridge (if PulseStream is already running)
   docker-compose up -d coinbase-bridge
   ```

3. **View bridge logs**:
   ```bash
   docker-compose logs -f coinbase-bridge
   ```

4. **Stop the bridge**:
   ```bash
   docker-compose stop coinbase-bridge
   ```

## Monitoring

### Logs

Monitor the bridge logs for health and errors:

```bash
# If running directly
python coinbase_bridge.py | tee bridge.log

# If running as systemd service
sudo journalctl -u coinbase-bridge -f

# If running in Docker
docker logs -f coinbase-bridge
```

### Metrics to Monitor

1. **Connection Status:** WebSocket connected/disconnected
2. **Message Rate:** Ticker messages per second
3. **Success Rate:** Successful API posts vs failures
4. **Latency:** Time from ticker receive to API response
5. **Error Rate:** Network errors, API errors

## Security Best Practices

1. **API Key Protection:**
   - Never commit API keys to version control
   - Use environment variables: `os.getenv('PULSESTREAM_API_KEY')`
   - Rotate keys regularly

2. **Network Security:**
   - Use HTTPS for PulseStream API in production
   - Implement rate limiting on the API side
   - Monitor for unusual traffic patterns

3. **Input Validation:**
   - The script already validates ticker message structure
   - Additional validation can be added as needed

## Support

For issues or questions:
- Check PulseStream documentation
- Review Coinbase API documentation: https://docs.cloud.coinbase.com/exchange/docs
- Open an issue in the PulseStream repository

## License

This script is part of the PulseStream platform and follows the same license.

