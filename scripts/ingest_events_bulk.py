#!/usr/bin/env python3
"""
Bulk ingest events into PulseStream with performance tracking.
"""

import json
import time
import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import sys


class BulkEventIngester:
    """Bulk event ingestion with performance tracking."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "duplicates": 0,
            "rate_limited": 0,
            "errors_by_code": defaultdict(int),
            "start_time": None,
            "end_time": None
        }
    
    async def ingest_single(self, client: httpx.AsyncClient, event: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest a single event."""
        try:
            response = await client.post(
                f"{self.base_url}/api/v1/ingestion/events",
                headers=self.headers,
                json=event,
                timeout=30.0
            )
            
            return {
                "status_code": response.status_code,
                "success": response.status_code in [200, 201],
                "response": response.json() if response.status_code in [200, 201] else None,
                "error": response.text if response.status_code not in [200, 201] else None
            }
        except Exception as e:
            return {
                "status_code": 0,
                "success": False,
                "error": str(e)
            }
    
    async def ingest_batch_concurrent(
        self, 
        events: List[Dict[str, Any]], 
        concurrency: int = 10
    ) -> None:
        """Ingest events with controlled concurrency."""
        async with httpx.AsyncClient() as client:
            semaphore = asyncio.Semaphore(concurrency)
            
            async def ingest_with_semaphore(event: Dict[str, Any], index: int):
                async with semaphore:
                    result = await self.ingest_single(client, event)
                    self._update_stats(result)
                    
                    # Progress reporting
                    if (index + 1) % 100 == 0:
                        elapsed = time.time() - self.stats["start_time"]
                        rate = (index + 1) / elapsed
                        print(f"\r  Progress: {index + 1}/{len(events)} events ({rate:.1f} events/sec)", 
                              end='', file=sys.stderr)
                    
                    return result
            
            # Start timer
            self.stats["start_time"] = time.time()
            
            # Create tasks
            tasks = [
                ingest_with_semaphore(event, i) 
                for i, event in enumerate(events)
            ]
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # End timer
            self.stats["end_time"] = time.time()
            print("\n", file=sys.stderr)
            
            return results
    
    async def ingest_batch_sequential(
        self, 
        events: List[Dict[str, Any]],
        delay_ms: int = 0
    ) -> None:
        """Ingest events sequentially with optional delay."""
        async with httpx.AsyncClient() as client:
            self.stats["start_time"] = time.time()
            
            for i, event in enumerate(events):
                result = await self.ingest_single(client, event)
                self._update_stats(result)
                
                # Progress reporting
                if (i + 1) % 100 == 0:
                    elapsed = time.time() - self.stats["start_time"]
                    rate = (i + 1) / elapsed
                    print(f"\r  Progress: {i + 1}/{len(events)} events ({rate:.1f} events/sec)", 
                          end='', file=sys.stderr)
                
                # Optional delay
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)
            
            self.stats["end_time"] = time.time()
            print("\n", file=sys.stderr)
    
    def _update_stats(self, result: Dict[str, Any]) -> None:
        """Update ingestion statistics."""
        self.stats["total"] += 1
        
        if result["success"]:
            self.stats["success"] += 1
        else:
            self.stats["failed"] += 1
            
            status_code = result.get("status_code", 0)
            self.stats["errors_by_code"][status_code] += 1
            
            if status_code == 429:
                self.stats["rate_limited"] += 1
            elif status_code == 409:
                self.stats["duplicates"] += 1
    
    def print_stats(self) -> None:
        """Print ingestion statistics."""
        duration = self.stats["end_time"] - self.stats["start_time"]
        throughput = self.stats["total"] / duration if duration > 0 else 0
        
        print("\n" + "=" * 70, file=sys.stderr)
        print("📊 INGESTION STATISTICS", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        
        print(f"\n⏱️  Performance:", file=sys.stderr)
        print(f"  Total time: {duration:.2f} seconds", file=sys.stderr)
        print(f"  Throughput: {throughput:.2f} events/sec", file=sys.stderr)
        print(f"  Avg latency: {(duration / self.stats['total'] * 1000):.2f} ms/event", file=sys.stderr)
        
        print(f"\n📈 Results:", file=sys.stderr)
        print(f"  Total events: {self.stats['total']}", file=sys.stderr)
        print(f"  ✅ Successful: {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.1f}%)", file=sys.stderr)
        print(f"  ❌ Failed: {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)", file=sys.stderr)
        
        if self.stats['duplicates'] > 0:
            print(f"  🔄 Duplicates: {self.stats['duplicates']}", file=sys.stderr)
        if self.stats['rate_limited'] > 0:
            print(f"  ⏸️  Rate limited: {self.stats['rate_limited']}", file=sys.stderr)
        
        if self.stats["errors_by_code"]:
            print(f"\n❌ Errors by status code:", file=sys.stderr)
            for code, count in sorted(self.stats["errors_by_code"].items()):
                print(f"  {code}: {count}", file=sys.stderr)
        
        print("\n" + "=" * 70, file=sys.stderr)


def load_events(file_path: str) -> List[Dict[str, Any]]:
    """Load events from file (JSON or JSONL)."""
    events = []
    
    with open(file_path, 'r') as f:
        # Try JSONL first
        try:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        except json.JSONDecodeError:
            # Try JSON array
            f.seek(0)
            events = json.load(f)
    
    return events


async def main():
    """Main ingestion function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bulk ingest events into PulseStream")
    parser.add_argument("file", help="Event file (JSON or JSONL)")
    parser.add_argument("--url", default="http://localhost:8000", help="PulseStream base URL")
    parser.add_argument("--api-key", default="test-api-key-12345", help="API key")
    parser.add_argument("--mode", choices=["concurrent", "sequential"], default="concurrent", help="Ingestion mode")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests (concurrent mode)")
    parser.add_argument("--delay", type=int, default=0, help="Delay between requests in ms (sequential mode)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of events to ingest")
    
    args = parser.parse_args()
    
    # Load events
    print(f"📁 Loading events from {args.file}...", file=sys.stderr)
    events = load_events(args.file)
    
    if args.limit:
        events = events[:args.limit]
    
    print(f"✅ Loaded {len(events)} events", file=sys.stderr)
    print(f"🎯 Target: {args.url}", file=sys.stderr)
    print(f"⚙️  Mode: {args.mode}", file=sys.stderr)
    if args.mode == "concurrent":
        print(f"🔀 Concurrency: {args.concurrency}", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Create ingester
    ingester = BulkEventIngester(args.url, args.api_key)
    
    # Ingest events
    print(f"🚀 Starting ingestion...", file=sys.stderr)
    
    if args.mode == "concurrent":
        await ingester.ingest_batch_concurrent(events, args.concurrency)
    else:
        await ingester.ingest_batch_sequential(events, args.delay)
    
    # Print statistics
    ingester.print_stats()


if __name__ == "__main__":
    asyncio.run(main())
