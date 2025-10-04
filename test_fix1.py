#!/usr/bin/env python3
"""Test Fix #1: Duplicate Detection."""
import asyncio
import sys
sys.path.insert(0, '.')

from scripts.test_real_world_ingestion import RealWorldIngestionTester

async def main():
    print("=" * 80)
    print("TESTING FIX #1: DUPLICATE DETECTION")
    print("=" * 80)
    
    tester = RealWorldIngestionTester()
    
    # Test duplicate detection
    await tester.test_duplicate_detection()
    
    # Print results
    if tester.results:
        result = tester.results[-1]
        print(f"\nResult: {'[PASS]' if result.passed else '[FAIL]'}")
        print(f"Details: {result.details}")
        if result.issues:
            print(f"Issues: {', '.join(result.issues)}")
    
    await tester.close()

if __name__ == "__main__":
    asyncio.run(main())

