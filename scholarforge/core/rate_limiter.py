import asyncio
import time
from typing import Dict

class AsyncTokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate  # tokens added per second
        self.capacity = capacity  # max burst
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                
                # Sleep until enough tokens are replenished
                needed = 1.0 - self.tokens
                wait_time = needed / self.rate
                await asyncio.sleep(wait_time)

class RateLimiterRegistry:
    def __init__(self):
        self.limiters: Dict[str, AsyncTokenBucket] = {
            "crossref": AsyncTokenBucket(rate=4.0, capacity=8.0),       # polite pool
            "pubmed": AsyncTokenBucket(rate=3.0, capacity=5.0),         # standard without api key
            "semanticscholar": AsyncTokenBucket(rate=1.0, capacity=2.0),# unauthenticated limit
            "openalex": AsyncTokenBucket(rate=5.0, capacity=10.0),      # openalex rate
            "unpaywall": AsyncTokenBucket(rate=5.0, capacity=10.0),
            "gemini": AsyncTokenBucket(rate=2.0, capacity=4.0)          # safe AI studio burst
        }

    async def acquire(self, service: str):
        limiter = self.limiters.get(service.lower())
        if limiter:
            await limiter.acquire()

rate_limiter = RateLimiterRegistry()

