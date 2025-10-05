# 📊 Realistic Event Data Generation Guide for PulseStream

## Overview

This guide provides tools and pre-generated datasets for testing PulseStream with realistic API monitoring events based on real-world production patterns.

---

## 🎯 What's Included

### 1. **Event Generator Script** (`scripts/generate_realistic_events.py`)
Advanced Python script that generates realistic API monitoring events based on:
- **Real-world microservices architecture** (8 services)
- **Actual HTTP status code distributions**
- **Production-like error messages**
- **Geographic distribution** (12+ locations)
- **Realistic response times** with variance and spikes
- **Business hours traffic patterns**
- **Multiple device types and user agents**

### 2. **Bulk Ingestion Script** (`scripts/ingest_events_bulk.py`)
High-performance bulk ingestion tool with:
- **Concurrent or sequential ingestion modes**
- **Configurable concurrency levels**
- **Rate limiting awareness**
- **Real-time progress tracking**
- **Comprehensive statistics**
- **Error reporting**

### 3. **Pre-Generated Datasets**
- `sample_events_1k.jsonl` - 1,000 events over 24 hours
- `sample_events_10k.jsonl` - 10,000 events over 1 week

---

## 🏗️ Service Architecture (Based on Real Microservices)

The generator creates events from these realistic services:

| Service | Endpoints | Avg Response | Error Rate | Description |
|---------|-----------|--------------|------------|-------------|
| **auth-service** | 9 | 150ms | 2% | Authentication & authorization |
| **payment-service** | 7 | 450ms | 5% | Payment processing (high latency) |
| **user-service** | 8 | 85ms | 1% | User management |
| **product-service** | 8 | 120ms | 1.5% | Product catalog |
| **order-service** | 7 | 280ms | 3% | Order processing |
| **notification-service** | 6 | 200ms | 4% | Multi-channel notifications |
| **analytics-service** | 5 | 350ms | 2% | Analytics & reporting |
| **search-service** | 4 | 95ms | 2.5% | Search functionality |

---

## 📝 Event Structure

Each generated event follows PulseStream's schema:

```json
{
  "event_id": "evt_1_a1b2c3d4e5f6",
  "event_type": "api_call",
  "timestamp": "2025-10-04T10:30:15.123456Z",
  "title": "POST /api/v1/orders/create",
  "message": "Successfully processed request to order-service",
  "severity": "info",
  "source": {
    "service": "order-service",
    "endpoint": "/api/v1/orders/create",
    "method": "POST",
    "version": "1.9.1",
    "environment": "production"
  },
  "metrics": {
    "response_time_ms": 245.32,
    "status_code": 201,
    "request_size_bytes": 1250,
    "response_size_bytes": 850,
    "cache_hit": false
  },
  "context": {
    "user_id": "user_45678",
    "session_id": "sess_a1b2c3d4e5f6",
    "request_id": "req_9876543210abcdef",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "tags": {
      "country": "US",
      "city": "New York",
      "region": "NA",
      "device_type": "desktop"
    }
  },
  "error_details": {
    "error_code": "ERR_500_789",
    "error_message": "Database connection failed",
    "error_type": "ServerError"
  },
  "payload": {
    "correlation_id": "corr_abc123def456",
    "trace_id": "trace_xyz789abc123",
    "items_count": 3,
    "total_amount": 125.99
  }
}
```

---

## 🚀 Quick Start

### Generate Events

```bash
# Generate 1,000 events (good for initial testing)
python3 scripts/generate_realistic_events.py --count 1000 --output events_1k.jsonl

# Generate 10,000 events over 1 week (realistic load)
python3 scripts/generate_realistic_events.py --count 10000 --output events_10k.jsonl --hours 168

# Generate 50,000 events (stress testing)
python3 scripts/generate_realistic_events.py --count 50000 --output events_50k.jsonl --hours 720

# Generate 100,000 events (performance testing)
python3 scripts/generate_realistic_events.py --count 100000 --output events_100k.jsonl --hours 720
```

### Ingest Events into PulseStream

```bash
# Concurrent ingestion (fastest - default 10 concurrent)
python3 scripts/ingest_events_bulk.py sample_events_1k.jsonl

# High concurrency (for performance testing)
python3 scripts/ingest_events_bulk.py sample_events_10k.jsonl --concurrency 50

# Sequential ingestion (for rate limit testing)
python3 scripts/ingest_events_bulk.py sample_events_1k.jsonl --mode sequential

# With delay between requests
python3 scripts/ingest_events_bulk.py events_1k.jsonl --mode sequential --delay 100

# Limit number of events
python3 scripts/ingest_events_bulk.py events_10k.jsonl --limit 1000

# Custom PulseStream instance
python3 scripts/ingest_events_bulk.py events_1k.jsonl \
  --url https://pulsestream.example.com \
  --api-key your-api-key-here
```

---

## 📊 Realistic Data Characteristics

### HTTP Status Code Distribution
- **2xx Success**: 97-98% (realistic production success rate)
- **4xx Client Errors**: 1.5-2% (validation, auth, not found)
- **5xx Server Errors**: 0.5-1% (infrastructure issues)

### Status Code Breakdown
- **200 OK**: 85% of successes
- **201 Created**: 10% of successes
- **400 Bad Request**: 15% of errors
- **401 Unauthorized**: 10% of errors
- **404 Not Found**: 20% of errors
- **500 Internal Server**: 10% of errors
- **503 Service Unavailable**: 7% of errors
- **504 Gateway Timeout**: 5% of errors

### Geographic Distribution
- **North America**: 40% (US, Canada)
- **Europe**: 30% (UK, Germany, France)
- **Asia Pacific**: 25% (Singapore, Japan, India, Australia)
- **Latin America**: 5% (Brazil)

### Traffic Patterns
- **Business Hours (9 AM - 5 PM)**: 2x normal traffic
- **Off Hours**: Baseline traffic
- **Weekend**: 60% of weekday traffic

### Response Time Characteristics
- **Fast services** (user, search): 50-150ms
- **Medium services** (product, auth): 100-250ms
- **Slow services** (order, payment): 200-500ms
- **Analytics**: 300-600ms
- **5% spike probability**: 2-10x normal latency
- **Error responses**: Often slower or timeout

---

## 🎯 Use Cases & Testing Scenarios

### 1. **Performance Testing**
```bash
# Generate 100K events
python3 scripts/generate_realistic_events.py --count 100000 --output perf_test.jsonl

# Ingest with high concurrency
python3 scripts/ingest_events_bulk.py perf_test.jsonl --concurrency 50
```
**Expected Results:**
- Throughput: 20-50 events/sec
- Success rate: >95%
- P95 latency: <200ms

### 2. **Rate Limiting Validation**
```bash
# Generate many events
python3 scripts/generate_realistic_events.py --count 5000 --output rate_test.jsonl

# Sequential ingestion to hit rate limits
python3 scripts/ingest_events_bulk.py rate_test.jsonl --mode sequential
```
**Expected Results:**
- Rate limit triggers at configured threshold
- 429 status codes appear
- Graceful degradation

### 3. **Duplicate Detection Testing**
```bash
# Ingest same file twice
python3 scripts/ingest_events_bulk.py sample_events_1k.jsonl
python3 scripts/ingest_events_bulk.py sample_events_1k.jsonl
```
**Expected Results:**
- Second run shows 100% duplicates (409 or idempotent 200)
- No duplicate data in database

### 4. **Search & Filtering**
```bash
# Ingest diverse events
python3 scripts/ingest_events_bulk.py sample_events_10k.jsonl

# Test searches via API:
curl -X GET "http://localhost:8000/api/v1/ingestion/events/search?service=payment-service" \
  -H "X-API-Key: test-api-key-12345"

curl -X GET "http://localhost:8000/api/v1/ingestion/events/search?status_code=500" \
  -H "X-API-Key: test-api-key-12345"
```

### 5. **Dashboard & Analytics**
```bash
# Ingest week-long data
python3 scripts/ingest_events_bulk.py sample_events_10k.jsonl

# View in dashboard
# - Error rate trends
# - Service health metrics
# - Geographic distribution
# - Response time percentiles
```

### 6. **Stress Testing**
```bash
# Generate 1 million events
python3 scripts/generate_realistic_events.py --count 1000000 --output stress_test.jsonl --hours 720

# Ingest in batches
python3 scripts/ingest_events_bulk.py stress_test.jsonl --concurrency 100 --limit 10000
```

---

## 📈 Sample Statistics

### From 10,000 Event Dataset

```
📊 Event Distribution:
  Total events:          10,000
  Services:              8
  Unique endpoints:      62
  Time span:             7 days (168 hours)
  
🌍 Geographic Coverage:
  Countries:             12
  Regions:               4 (NA, EU, APAC, LATAM)
  Cities:                12
  
✅ Success Metrics:
  Success rate:          97.4%
  2xx responses:         9,740
  Average response:      185ms
  Cache hit rate:        ~25%
  
❌ Error Metrics:
  Error rate:            2.6%
  4xx errors:            1.8% (client errors)
  5xx errors:            0.8% (server errors)
  
📱 Device Distribution:
  Desktop:               45%
  Mobile:                30%
  API clients:           20%
  Tablet:                4%
  Bots:                  1%
  
⚡ Performance:
  P50 latency:           145ms
  P95 latency:           420ms
  P99 latency:           850ms
  Slowest endpoint:      /api/v1/payments/capture (avg 450ms)
  Fastest endpoint:      /api/v1/users/profile (avg 85ms)
```

---

## 🔍 Advanced Options

### Event Generator Options
```bash
python3 scripts/generate_realistic_events.py \
  --count 50000 \              # Number of events to generate
  --output my_events.jsonl \   # Output file path
  --format jsonl \             # json or jsonl
  --hours 168                  # Time spread (1 week)
```

### Ingestion Options
```bash
python3 scripts/ingest_events_bulk.py my_events.jsonl \
  --url http://localhost:8000 \        # PulseStream URL
  --api-key test-api-key-12345 \       # API key
  --mode concurrent \                  # concurrent or sequential
  --concurrency 20 \                   # Concurrent requests
  --delay 50 \                         # Delay in ms (sequential)
  --limit 5000                         # Limit events to ingest
```

---

## 📊 Expected Performance Benchmarks

### Ingestion Performance

| Event Count | Concurrency | Expected Time | Throughput |
|-------------|-------------|---------------|------------|
| 1,000 | 10 | 30-60 sec | 20-30 /sec |
| 10,000 | 10 | 5-8 min | 20-30 /sec |
| 10,000 | 50 | 2-4 min | 40-80 /sec |
| 50,000 | 50 | 10-20 min | 40-80 /sec |
| 100,000 | 100 | 20-40 min | 40-80 /sec |

*Performance depends on hardware, network, and database performance*

---

## 🎯 Demo & Presentation Tips

### For Project Submission

1. **Generate Comprehensive Dataset**
   ```bash
   python3 scripts/generate_realistic_events.py --count 50000 --output demo_events.jsonl --hours 720
   ```

2. **Ingest Events**
   ```bash
   python3 scripts/ingest_events_bulk.py demo_events.jsonl --concurrency 20
   ```

3. **Showcase Metrics**
   - Total events ingested
   - Success rate (should be >95%)
   - Throughput (events/sec)
   - Response time distribution
   - Error handling
   - Duplicate detection
   - Rate limiting

4. **Demonstrate Search**
   - Filter by service
   - Filter by status code
   - Filter by time range
   - Filter by geography

5. **Show Analytics**
   - Error rate trends
   - Service health
   - Response time percentiles
   - Geographic distribution
   - Peak traffic patterns

---

## 📂 File Formats

### JSONL (Recommended)
```
{"event_id": "evt_1_...", "event_type": "api_call", ...}
{"event_id": "evt_2_...", "event_type": "api_call", ...}
{"event_id": "evt_3_...", "event_type": "api_call", ...}
```
- One JSON object per line
- Efficient for streaming
- Easy to process line-by-line
- Smaller memory footprint

### JSON Array
```json
[
  {"event_id": "evt_1_...", "event_type": "api_call", ...},
  {"event_id": "evt_2_...", "event_type": "api_call", ...}
]
```
- Complete JSON array
- Must load entire file into memory
- Good for smaller datasets

---

## 🐛 Troubleshooting

### Issue: "Rate limit exceeded"
**Solution:** Use sequential mode with delay
```bash
python3 scripts/ingest_events_bulk.py events.jsonl --mode sequential --delay 100
```

### Issue: "Connection timeout"
**Solution:** Reduce concurrency
```bash
python3 scripts/ingest_events_bulk.py events.jsonl --concurrency 5
```

### Issue: "Database constraint error"
**Solution:** Ensure unique constraint is applied
```bash
sudo -u postgres psql -d pulsestream_dev -c "
ALTER TABLE events ADD CONSTRAINT uq_events_tenant_external_id UNIQUE (tenant_id, external_id);
"
```

### Issue: "Out of memory"
**Solution:** Use JSONL format and process in batches
```bash
python3 scripts/ingest_events_bulk.py events.jsonl --limit 1000
```

---

## 📚 Additional Resources

### Example Queries

**Get all payment errors:**
```bash
curl "http://localhost:8000/api/v1/ingestion/events/search?service=payment-service&status_code=500" \
  -H "X-API-Key: test-api-key-12345"
```

**Get events from last hour:**
```bash
START_TIME=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)
curl "http://localhost:8000/api/v1/ingestion/events/search?start_time=$START_TIME" \
  -H "X-API-Key: test-api-key-12345"
```

**Get high-latency events:**
```bash
# Query events with response_time > 1000ms using filters
curl "http://localhost:8000/api/v1/ingestion/events/search?limit=100" \
  -H "X-API-Key: test-api-key-12345" | \
  jq '.events[] | select(.metrics.response_time_ms > 1000)'
```

---

## ✅ Verification Checklist

After ingesting events, verify:

- [ ] Events appear in database
- [ ] Search returns correct results
- [ ] Metrics are calculated correctly
- [ ] No duplicate events created
- [ ] Rate limiting works as expected
- [ ] Error handling is proper
- [ ] Dashboard shows data
- [ ] Geographic data is present
- [ ] Timestamp ordering is correct
- [ ] All services represented

---

## 🎓 Best Practices

1. **Start Small**: Test with 1K events first
2. **Monitor Performance**: Watch throughput and error rates
3. **Use Appropriate Concurrency**: Don't overwhelm the system
4. **Check Database**: Verify data after ingestion
5. **Test Edge Cases**: Errors, duplicates, rate limits
6. **Document Results**: Save statistics for presentation
7. **Clean Up**: Remove test data between runs if needed

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review PulseStream logs
3. Verify database connectivity
4. Check API key validity
5. Review ingestion statistics

---

**Generated**: October 4, 2025  
**Version**: 1.0  
**Status**: Production Ready ✅
