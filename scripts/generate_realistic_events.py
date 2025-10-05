#!/usr/bin/env python3
"""
Generate realistic API monitoring events for PulseStream testing.
Based on real-world API monitoring patterns from production systems.
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys

# Real-world service configurations based on common microservices architectures
SERVICES = {
    "auth-service": {
        "endpoints": [
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",
            "/api/v1/auth/verify",
            "/api/v1/auth/register",
            "/api/v1/auth/password/reset",
            "/api/v1/auth/password/change",
            "/api/v1/auth/mfa/enable",
            "/api/v1/auth/mfa/verify"
        ],
        "error_rate": 0.02,  # 2% error rate
        "avg_response_ms": 150,
        "version": "2.3.1"
    },
    "payment-service": {
        "endpoints": [
            "/api/v1/payments/create",
            "/api/v1/payments/capture",
            "/api/v1/payments/refund",
            "/api/v1/payments/status",
            "/api/v1/payments/webhook",
            "/api/v1/payments/methods",
            "/api/v1/payments/history"
        ],
        "error_rate": 0.05,  # 5% error rate (higher due to external dependencies)
        "avg_response_ms": 450,
        "version": "1.8.2"
    },
    "user-service": {
        "endpoints": [
            "/api/v1/users/profile",
            "/api/v1/users/update",
            "/api/v1/users/preferences",
            "/api/v1/users/avatar",
            "/api/v1/users/notifications",
            "/api/v1/users/search",
            "/api/v1/users/{id}",
            "/api/v1/users/delete"
        ],
        "error_rate": 0.01,
        "avg_response_ms": 85,
        "version": "3.1.0"
    },
    "product-service": {
        "endpoints": [
            "/api/v1/products/list",
            "/api/v1/products/{id}",
            "/api/v1/products/search",
            "/api/v1/products/categories",
            "/api/v1/products/recommendations",
            "/api/v1/products/reviews",
            "/api/v1/products/inventory",
            "/api/v1/products/pricing"
        ],
        "error_rate": 0.015,
        "avg_response_ms": 120,
        "version": "2.7.4"
    },
    "order-service": {
        "endpoints": [
            "/api/v1/orders/create",
            "/api/v1/orders/status",
            "/api/v1/orders/history",
            "/api/v1/orders/cancel",
            "/api/v1/orders/tracking",
            "/api/v1/orders/{id}",
            "/api/v1/orders/invoice"
        ],
        "error_rate": 0.03,
        "avg_response_ms": 280,
        "version": "1.9.1"
    },
    "notification-service": {
        "endpoints": [
            "/api/v1/notifications/send",
            "/api/v1/notifications/email",
            "/api/v1/notifications/sms",
            "/api/v1/notifications/push",
            "/api/v1/notifications/preferences",
            "/api/v1/notifications/history"
        ],
        "error_rate": 0.04,
        "avg_response_ms": 200,
        "version": "1.5.3"
    },
    "analytics-service": {
        "endpoints": [
            "/api/v1/analytics/events",
            "/api/v1/analytics/dashboard",
            "/api/v1/analytics/reports",
            "/api/v1/analytics/metrics",
            "/api/v1/analytics/export"
        ],
        "error_rate": 0.02,
        "avg_response_ms": 350,
        "version": "2.1.0"
    },
    "search-service": {
        "endpoints": [
            "/api/v1/search/query",
            "/api/v1/search/autocomplete",
            "/api/v1/search/filters",
            "/api/v1/search/suggestions"
        ],
        "error_rate": 0.025,
        "avg_response_ms": 95,
        "version": "1.6.8"
    }
}

# Real-world error messages from production systems
ERROR_MESSAGES = {
    400: [
        "Invalid request parameters",
        "Missing required field: email",
        "Invalid email format",
        "Password must be at least 8 characters",
        "Invalid date format",
        "Request body too large",
        "Invalid JSON syntax",
        "Missing Content-Type header"
    ],
    401: [
        "Authentication token expired",
        "Invalid API key",
        "Missing authorization header",
        "Token signature verification failed",
        "User credentials invalid"
    ],
    403: [
        "Insufficient permissions",
        "Access denied to resource",
        "Rate limit exceeded",
        "Account suspended",
        "IP address blocked"
    ],
    404: [
        "Resource not found",
        "User not found",
        "Product not found",
        "Endpoint does not exist",
        "Order ID not found"
    ],
    409: [
        "Resource already exists",
        "Duplicate email address",
        "Concurrent modification conflict",
        "Payment already processed"
    ],
    422: [
        "Validation failed",
        "Invalid input data",
        "Business rule violation",
        "Credit card validation failed"
    ],
    429: [
        "Too many requests",
        "Rate limit exceeded",
        "API quota exceeded",
        "Throttling active"
    ],
    500: [
        "Internal server error",
        "Database connection failed",
        "Unexpected error occurred",
        "Service temporarily unavailable"
    ],
    502: [
        "Bad gateway",
        "Upstream service unreachable",
        "Gateway timeout",
        "Service dependency failed"
    ],
    503: [
        "Service unavailable",
        "Database maintenance in progress",
        "System overload",
        "Circuit breaker open"
    ],
    504: [
        "Gateway timeout",
        "Upstream request timeout",
        "Database query timeout",
        "External API timeout"
    ]
}

# Real user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "PostmanRuntime/7.36.0",
    "axios/1.6.0",
    "okhttp/4.12.0",
    "Dart/3.2 (dart:io)",
    "Go-http-client/1.1"
]

# Geographic distribution
GEO_LOCATIONS = [
    {"country": "US", "city": "New York", "region": "NA"},
    {"country": "US", "city": "San Francisco", "region": "NA"},
    {"country": "US", "city": "Chicago", "region": "NA"},
    {"country": "GB", "city": "London", "region": "EU"},
    {"country": "DE", "city": "Berlin", "region": "EU"},
    {"country": "FR", "city": "Paris", "region": "EU"},
    {"country": "SG", "city": "Singapore", "region": "APAC"},
    {"country": "JP", "city": "Tokyo", "region": "APAC"},
    {"country": "IN", "city": "Mumbai", "region": "APAC"},
    {"country": "AU", "city": "Sydney", "region": "APAC"},
    {"country": "BR", "city": "São Paulo", "region": "LATAM"},
    {"country": "CA", "city": "Toronto", "region": "NA"}
]

# Device types
DEVICE_TYPES = ["desktop", "mobile", "tablet", "api_client", "bot"]

# HTTP methods distribution
HTTP_METHODS = {
    "GET": 0.60,    # 60% of requests
    "POST": 0.25,   # 25%
    "PUT": 0.08,    # 8%
    "DELETE": 0.04, # 4%
    "PATCH": 0.03   # 3%
}

# Environments
ENVIRONMENTS = ["production", "staging", "development"]


class RealisticEventGenerator:
    """Generate realistic API monitoring events."""
    
    def __init__(self, start_time: datetime = None):
        from datetime import timezone
        self.start_time = start_time or datetime.now(timezone.utc) - timedelta(hours=24)
        self.event_count = 0
        
    def generate_response_time(self, avg_ms: float, is_error: bool = False) -> float:
        """Generate realistic response time with variance."""
        if is_error:
            # Errors tend to be slower or timeout
            variance = random.uniform(0.5, 3.0)
        else:
            # Normal variance
            variance = random.gauss(1.0, 0.3)
        
        response_time = avg_ms * max(0.1, variance)
        
        # Add occasional spikes
        if random.random() < 0.05:  # 5% spike probability
            response_time *= random.uniform(2, 10)
        
        return round(response_time, 2)
    
    def generate_status_code(self, error_rate: float) -> int:
        """Generate realistic HTTP status code."""
        if random.random() < error_rate:
            # Error scenario
            error_type = random.choices(
                [400, 401, 403, 404, 409, 422, 429, 500, 502, 503, 504],
                weights=[15, 10, 8, 20, 5, 8, 7, 10, 5, 7, 5]
            )[0]
            return error_type
        else:
            # Success scenario
            return random.choices(
                [200, 201, 202, 204],
                weights=[85, 10, 3, 2]
            )[0]
    
    def select_http_method(self) -> str:
        """Select HTTP method based on realistic distribution."""
        methods = list(HTTP_METHODS.keys())
        weights = list(HTTP_METHODS.values())
        return random.choices(methods, weights=weights)[0]
    
    def generate_event(self, timestamp: datetime = None) -> Dict[str, Any]:
        """Generate a single realistic event."""
        self.event_count += 1
        
        # Select service and endpoint
        service_name = random.choice(list(SERVICES.keys()))
        service_config = SERVICES[service_name]
        endpoint = random.choice(service_config["endpoints"])
        
        # Generate realistic values
        status_code = self.generate_status_code(service_config["error_rate"])
        is_error = status_code >= 400
        response_time = self.generate_response_time(service_config["avg_response_ms"], is_error)
        http_method = self.select_http_method()
        
        # Timestamp
        if timestamp is None:
            timestamp = self.start_time + timedelta(
                seconds=random.uniform(0, 86400)  # Within 24 hours
            )
        
        # User context
        user_agent = random.choice(USER_AGENTS)
        geo = random.choice(GEO_LOCATIONS)
        device_type = random.choice(DEVICE_TYPES)
        
        # Generate event
        event = {
            "event_id": f"evt_{self.event_count}_{uuid.uuid4().hex[:12]}",
            "event_type": "api_call",
            "timestamp": timestamp.isoformat().replace('+00:00', 'Z') if '+00:00' in timestamp.isoformat() else timestamp.isoformat(),
            "title": f"{http_method} {endpoint}",
            "message": self._generate_message(status_code, service_name, endpoint),
            "severity": self._determine_severity(status_code),
            "source": {
                "service": service_name,
                "endpoint": endpoint,
                "method": http_method,
                "version": service_config["version"],
                "environment": random.choices(
                    ENVIRONMENTS,
                    weights=[70, 20, 10]  # 70% prod, 20% staging, 10% dev
                )[0]
            },
            "metrics": {
                "response_time_ms": response_time,
                "status_code": status_code,
                "request_size_bytes": random.randint(100, 5000),
                "response_size_bytes": random.randint(200, 50000) if status_code < 400 else random.randint(50, 500),
                "cache_hit": random.choice([True, False]) if status_code == 200 else False
            },
            "context": {
                "user_id": f"user_{random.randint(1000, 99999)}" if random.random() > 0.1 else None,
                "session_id": f"sess_{uuid.uuid4().hex[:16]}",
                "request_id": f"req_{uuid.uuid4().hex}",
                "ip_address": self._generate_ip(),
                "user_agent": user_agent,
                "tags": {
                    "country": geo["country"],
                    "city": geo["city"],
                    "region": geo["region"],
                    "device_type": device_type
                }
            }
        }
        
        # Add error details for failures
        if is_error:
            error_messages = ERROR_MESSAGES.get(status_code, ["Unknown error"])
            event["error_details"] = {
                "error_code": f"ERR_{status_code}_{random.randint(100, 999)}",
                "error_message": random.choice(error_messages),
                "error_type": self._get_error_type(status_code),
                "stack_trace": None  # Not included to keep data size manageable
            }
        
        # Add payload with realistic data
        event["payload"] = self._generate_payload(service_name, endpoint, http_method)
        
        return event
    
    def _generate_message(self, status_code: int, service: str, endpoint: str) -> str:
        """Generate realistic log message."""
        if status_code < 300:
            return f"Successfully processed request to {service}"
        elif status_code < 400:
            return f"Request redirected"
        elif status_code < 500:
            return f"Client error on {endpoint}"
        else:
            return f"Server error in {service}"
    
    def _determine_severity(self, status_code: int) -> str:
        """Determine event severity based on status code."""
        if status_code < 300:
            return "info"
        elif status_code < 400:
            return "warning"
        elif status_code < 500:
            return "warning"
        else:
            return "error"
    
    def _get_error_type(self, status_code: int) -> str:
        """Get error type category."""
        if status_code in [400, 422]:
            return "ValidationError"
        elif status_code in [401, 403]:
            return "AuthenticationError"
        elif status_code == 404:
            return "NotFoundError"
        elif status_code == 409:
            return "ConflictError"
        elif status_code == 429:
            return "RateLimitError"
        elif status_code >= 500:
            return "ServerError"
        else:
            return "UnknownError"
    
    def _generate_ip(self) -> str:
        """Generate realistic IP address."""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"
    
    def _generate_payload(self, service: str, endpoint: str, method: str) -> Dict[str, Any]:
        """Generate realistic request/response payload data."""
        payload = {
            "correlation_id": f"corr_{uuid.uuid4().hex[:16]}",
            "trace_id": f"trace_{uuid.uuid4().hex}",
        }
        
        # Add service-specific payload data
        if "auth" in service:
            if "login" in endpoint:
                payload["auth_method"] = random.choice(["password", "oauth", "sso", "mfa"])
            elif "register" in endpoint:
                payload["registration_source"] = random.choice(["web", "mobile", "api"])
        
        elif "payment" in service:
            if method == "POST":
                payload["payment_method"] = random.choice(["credit_card", "debit_card", "paypal", "stripe"])
                payload["amount"] = round(random.uniform(10.0, 5000.0), 2)
                payload["currency"] = random.choice(["USD", "EUR", "GBP", "JPY"])
        
        elif "order" in service:
            if "create" in endpoint:
                payload["items_count"] = random.randint(1, 10)
                payload["total_amount"] = round(random.uniform(20.0, 1000.0), 2)
        
        return payload
    
    def generate_batch(self, count: int, time_spread_hours: int = 24) -> List[Dict[str, Any]]:
        """Generate a batch of realistic events spread over time."""
        events = []
        
        for i in range(count):
            # Spread events over time with realistic distribution
            # More events during business hours
            hour_offset = random.uniform(0, time_spread_hours)
            timestamp = self.start_time + timedelta(hours=hour_offset)
            
            # Business hours have 2x traffic
            hour_of_day = timestamp.hour
            if 9 <= hour_of_day <= 17:  # Business hours
                if random.random() > 0.5:  # 50% chance to use this timestamp
                    events.append(self.generate_event(timestamp))
                else:
                    # Generate another event in business hours
                    timestamp = self.start_time + timedelta(hours=random.uniform(9, 17))
                    events.append(self.generate_event(timestamp))
            else:
                events.append(self.generate_event(timestamp))
            
            # Progress indicator
            if (i + 1) % 1000 == 0:
                print(f"Generated {i + 1}/{count} events...", file=sys.stderr)
        
        # Sort by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return events


def main():
    """Generate realistic events and save to file."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate realistic API monitoring events")
    parser.add_argument("--count", type=int, default=10000, help="Number of events to generate")
    parser.add_argument("--output", type=str, default="realistic_events.json", help="Output file path")
    parser.add_argument("--format", choices=["json", "jsonl"], default="jsonl", help="Output format")
    parser.add_argument("--hours", type=int, default=24, help="Time spread in hours")
    
    args = parser.parse_args()
    
    print(f"Generating {args.count} realistic events...", file=sys.stderr)
    print(f"Time spread: {args.hours} hours", file=sys.stderr)
    print(f"Output format: {args.format}", file=sys.stderr)
    print(f"Output file: {args.output}", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Generate events
    generator = RealisticEventGenerator()
    events = generator.generate_batch(args.count, args.hours)
    
    # Save to file
    with open(args.output, 'w') as f:
        if args.format == "json":
            json.dump(events, f, indent=2)
        else:  # jsonl
            for event in events:
                f.write(json.dumps(event) + '\n')
    
    print(f"\n✅ Successfully generated {len(events)} events!", file=sys.stderr)
    print(f"📁 Saved to: {args.output}", file=sys.stderr)
    
    # Print statistics
    print("\n📊 Statistics:", file=sys.stderr)
    status_codes = {}
    services = {}
    for event in events:
        status = event['metrics']['status_code']
        status_codes[status] = status_codes.get(status, 0) + 1
        service = event['source']['service']
        services[service] = services.get(service, 0) + 1
    
    print(f"  Total events: {len(events)}", file=sys.stderr)
    print(f"  Services: {len(services)}", file=sys.stderr)
    print(f"  Success rate: {sum(v for k, v in status_codes.items() if k < 400) / len(events) * 100:.1f}%", file=sys.stderr)
    print(f"  Error rate: {sum(v for k, v in status_codes.items() if k >= 400) / len(events) * 100:.1f}%", file=sys.stderr)


if __name__ == "__main__":
    main()
