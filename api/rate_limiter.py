#!/usr/bin/env python3
"""
Rate Limiter for QENEX API
Implements token bucket algorithm for request throttling
"""

import time
import asyncio
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import json

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: int = 10
    burst_size: int = 20
    per_ip_limit: int = 100  # Per IP per minute
    global_limit: int = 1000  # Global per minute
    block_duration: int = 60  # Block duration in seconds

@dataclass 
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int
    refill_rate: float
    tokens: float = field(default_factory=lambda: 0)
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on refill rate
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

class RateLimiter:
    """Rate limiter with multiple strategies"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # Global token bucket
        self.global_bucket = TokenBucket(
            capacity=self.config.burst_size,
            refill_rate=self.config.requests_per_second,
            tokens=self.config.burst_size
        )
        
        # Per-IP token buckets
        self.ip_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=20,
                refill_rate=self.config.per_ip_limit / 60,
                tokens=20
            )
        )
        
        # Blocked IPs
        self.blocked_ips: Dict[str, float] = {}
        
        # Request history for monitoring
        self.request_history: Dict[str, list] = defaultdict(list)
    
    async def check_rate_limit(self, ip_address: str) -> Dict[str, any]:
        """Check if request should be allowed"""
        
        # Check if IP is blocked
        if ip_address in self.blocked_ips:
            if time.time() < self.blocked_ips[ip_address]:
                return {
                    "allowed": False,
                    "reason": "IP temporarily blocked",
                    "retry_after": int(self.blocked_ips[ip_address] - time.time())
                }
            else:
                # Unblock IP
                del self.blocked_ips[ip_address]
        
        # Check global rate limit
        if not self.global_bucket.consume():
            return {
                "allowed": False,
                "reason": "Global rate limit exceeded",
                "retry_after": 1
            }
        
        # Check per-IP rate limit
        ip_bucket = self.ip_buckets[ip_address]
        if not ip_bucket.consume():
            # Too many requests from this IP - temporary block
            self.blocked_ips[ip_address] = time.time() + self.config.block_duration
            return {
                "allowed": False,
                "reason": "Per-IP rate limit exceeded",
                "retry_after": self.config.block_duration
            }
        
        # Track request
        self.request_history[ip_address].append(time.time())
        
        # Clean old history
        cutoff = time.time() - 60
        self.request_history[ip_address] = [
            t for t in self.request_history[ip_address] if t > cutoff
        ]
        
        return {
            "allowed": True,
            "remaining_tokens": int(ip_bucket.tokens),
            "limit": self.config.per_ip_limit
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics"""
        return {
            "global_tokens": self.global_bucket.tokens,
            "active_ips": len(self.ip_buckets),
            "blocked_ips": len(self.blocked_ips),
            "total_requests": sum(len(h) for h in self.request_history.values()),
            "config": {
                "requests_per_second": self.config.requests_per_second,
                "burst_size": self.config.burst_size,
                "per_ip_limit": self.config.per_ip_limit
            }
        }

class APIWrapper:
    """API wrapper with rate limiting"""
    
    def __init__(self, handler: Callable, rate_limiter: Optional[RateLimiter] = None):
        self.handler = handler
        self.rate_limiter = rate_limiter or RateLimiter()
    
    async def handle_request(self, request: Dict) -> Dict:
        """Handle API request with rate limiting"""
        
        # Extract IP address
        ip_address = request.get("ip", "unknown")
        
        # Check rate limit
        rate_check = await self.rate_limiter.check_rate_limit(ip_address)
        
        if not rate_check["allowed"]:
            return {
                "error": "Rate limit exceeded",
                "message": rate_check["reason"],
                "retry_after": rate_check["retry_after"],
                "status": 429
            }
        
        # Add rate limit headers
        try:
            # Process request
            response = await self.handler(request)
            
            # Add rate limit info to response
            response["rate_limit"] = {
                "remaining": rate_check.get("remaining_tokens", 0),
                "limit": rate_check.get("limit", self.rate_limiter.config.per_ip_limit)
            }
            
            return response
            
        except Exception as e:
            return {
                "error": "Internal server error",
                "message": str(e),
                "status": 500
            }

# Example usage
async def example_handler(request: Dict) -> Dict:
    """Example API handler"""
    return {
        "status": 200,
        "data": {
            "message": "Request processed successfully",
            "timestamp": time.time()
        }
    }

async def main():
    """Demo rate limiter"""
    
    # Create rate limiter with custom config
    config = RateLimitConfig(
        requests_per_second=5,
        burst_size=10,
        per_ip_limit=50
    )
    
    # Create API wrapper
    api = APIWrapper(example_handler, RateLimiter(config))
    
    # Simulate requests
    print("🚦 Rate Limiter Demo")
    print("=" * 50)
    
    for i in range(15):
        request = {
            "ip": "192.168.1.1",
            "path": "/api/test",
            "method": "GET"
        }
        
        response = await api.handle_request(request)
        
        if response.get("status") == 429:
            print(f"Request {i+1}: ❌ BLOCKED - {response['message']}")
        else:
            print(f"Request {i+1}: ✅ ALLOWED - Remaining: {response['rate_limit']['remaining']}")
        
        await asyncio.sleep(0.1)
    
    # Show stats
    print("\n📊 Rate Limiter Stats:")
    stats = api.rate_limiter.get_stats()
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    asyncio.run(main())