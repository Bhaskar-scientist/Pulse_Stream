# Coinbase Integration - Quick Start Guide

Get real-time cryptocurrency market data flowing into PulseStream in under 5 minutes!

## Prerequisites

- PulseStream platform running (via Docker Compose)
- Python 3.8+ (for standalone mode) OR Docker (for containerized mode)
- A valid PulseStream tenant API key

## Option 1: Docker Compose (Recommended) 

### Step 1: Configure API Key

Add your PulseStream API key to `.env`:

```bash
echo "COINBASE_BRIDGE_API_KEY=your-api-key-here" >> .env
```

### Step 2: Start the Bridge

```bash
docker-compose --profile integrations up -d
```

### Step 3: Verify

```bash
# Check if bridge is running
docker-compose ps coinbase-bridge

# View real-time logs
docker-compose logs -f coinbase-bridge
```

You should see ticker updates like:
```
📊 Received ticker update: BTC-USD @ $45234.56
✓ Event sent successfully: Coinbase Price Update: BTC-USD | Price: $45234.56 | Status: 200
```

## Option 2: Standalone Python Script

### Step 1: Install Dependencies

```bash
pip install -r coinbase_bridge_requirements.txt
```

### Step 2: Configure API Key

Edit `coinbase_bridge.py`:
```python
API_KEY = "your-pulsestream-api-key"
```

Or set environment variable:
```bash
export API_KEY="your-pulsestream-api-key"
```

### Step 3: Test Setup

```bash
python scripts/test_coinbase_bridge.py
```

All tests should pass ✅

### Step 4: Run the Bridge

```bash
python coinbase_bridge.py
```

## View Ingested Data

### Via Dashboard
Navigate to your PulseStream dashboard and look for events from `coinbase-exchange` service.

### Via API
```bash
curl -X GET "http://localhost:8000/api/v1/ingestion/events/search?service=coinbase-exchange&limit=10" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Check Statistics
```bash
curl -X GET "http://localhost:8000/api/v1/ingestion/stats" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## What Data Is Captured?

The bridge captures real-time ticker data for:
- **BTC-USD** - Bitcoin price in US Dollars
- **ETH-USD** - Ethereum price in US Dollars

Each event includes:
- Current price
- 24-hour volume
- Best bid/ask prices
- Spread
- 24-hour high/low
- Last trade ID and size

## Customization

### Add More Cryptocurrency Pairs

Edit `coinbase_bridge.py`:
```python
SUBSCRIPTION_MESSAGE = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"],
    "channels": ["ticker"]
}
```

### Change Update Frequency

The bridge receives updates in real-time as they occur on Coinbase. Ticker updates typically arrive 1-5 times per second per product.

## Troubleshooting

### Bridge not connecting to PulseStream?

```bash
# Check if PulseStream is running
docker-compose ps

# Test API endpoint
curl http://localhost:8000/api/v1/ingestion/health
```

### Authentication errors?

```bash
# Verify your API key
echo $COINBASE_BRIDGE_API_KEY

# Test authentication
python scripts/test_coinbase_bridge.py
```

### No ticker messages?

- Check your internet connection
- Verify Coinbase API status: https://status.coinbase.com/
- Review bridge logs for errors

## Next Steps

1. **Set Up Alerts**: Configure price threshold alerts in PulseStream
2. **Create Dashboards**: Build custom visualizations for crypto prices
3. **Analyze Trends**: Use PulseStream analytics to identify patterns
4. **Add More Pairs**: Expand monitoring to additional cryptocurrencies

## Documentation

- Full Setup Guide: [docs/coinbase-bridge-setup.md](docs/coinbase-bridge-setup.md)
- PulseStream API Docs: [README.md](README.md)
- Coinbase WebSocket API: https://docs.cloud.coinbase.com/exchange/docs

## Support

Issues? Questions? Check the troubleshooting section in the full documentation or review the logs for detailed error messages.

---

**Happy Streaming!** 🚀📈

