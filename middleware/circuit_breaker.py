#!/usr/bin/env python3
"""
Circuit Breaker and Rate Limiting Middleware for QENEX
Provides resilience patterns to prevent system overload
"""

import time
import threading
from collections import deque, defaultdict
from enum import Enum
from typing import Callable, Any, Optional, Dict
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit broken, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures
    """
    
    def __init__(
        self, 
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.RLock()
        
        # Metrics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.circuit_open_count = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self.lock:
            self.total_calls += 1
            
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker entering HALF_OPEN state for {func.__name__}")
                else:
                    self.circuit_open_count += 1
                    raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time and 
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            self.total_successes += 1
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
                    logger.info("Circuit breaker is now CLOSED")
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker is OPEN again after failure in HALF_OPEN")
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.circuit_open_count += 1
                logger.warning(f"Circuit breaker is now OPEN after {self.failure_count} failures")
    
    def get_state(self) -> str:
        """Get current circuit state"""
        return self.state.value
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        with self.lock:
            return {
                "state": self.state.value,
                "total_calls": self.total_calls,
                "total_successes": self.total_successes,
                "total_failures": self.total_failures,
                "failure_count": self.failure_count,
                "circuit_open_count": self.circuit_open_count,
                "success_rate": (self.total_successes / self.total_calls * 100) if self.total_calls > 0 else 0
            }
    
    def reset(self):
        """Manually reset the circuit breaker"""
        with self.lock:
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker manually reset")

class RateLimiter:
    """
    Token bucket rate limiter for API throttling
    """
    
    def __init__(self, rate: int = 100, per: int = 60):
        """
        Initialize rate limiter
        :param rate: Number of requests allowed
        :param per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self.lock = threading.RLock()
        
        # Metrics
        self.total_requests = 0
        self.rejected_requests = 0
    
    def is_allowed(self, identifier: str = "default") -> bool:
        """Check if request is allowed"""
        with self.lock:
            self.total_requests += 1
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current
            
            # Replenish tokens
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            
            if self.allowance < 1.0:
                self.rejected_requests += 1
                return False
            else:
                self.allowance -= 1.0
                return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        with self.lock:
            return {
                "rate_limit": f"{self.rate}/{self.per}s",
                "current_allowance": self.allowance,
                "total_requests": self.total_requests,
                "rejected_requests": self.rejected_requests,
                "rejection_rate": (self.rejected_requests / self.total_requests * 100) if self.total_requests > 0 else 0
            }

class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter for more accurate rate limiting
    """
    
    def __init__(self, rate: int = 100, window_size: int = 60):
        """
        Initialize sliding window rate limiter
        :param rate: Number of requests allowed in the window
        :param window_size: Window size in seconds
        """
        self.rate = rate
        self.window_size = window_size
        self.requests = defaultdict(deque)
        self.lock = threading.RLock()
        
        # Metrics
        self.total_requests = 0
        self.rejected_requests = 0
    
    def is_allowed(self, identifier: str = "default") -> bool:
        """Check if request is allowed for the given identifier"""
        with self.lock:
            self.total_requests += 1
            current_time = time.time()
            request_times = self.requests[identifier]
            
            # Remove old requests outside the window
            while request_times and request_times[0] < current_time - self.window_size:
                request_times.popleft()
            
            if len(request_times) < self.rate:
                request_times.append(current_time)
                return True
            else:
                self.rejected_requests += 1
                return False
    
    def get_metrics(self, identifier: str = "default") -> Dict[str, Any]:
        """Get rate limiter metrics for specific identifier"""
        with self.lock:
            return {
                "rate_limit": f"{self.rate}/{self.window_size}s",
                "current_requests": len(self.requests[identifier]),
                "total_requests": self.total_requests,
                "rejected_requests": self.rejected_requests,
                "rejection_rate": (self.rejected_requests / self.total_requests * 100) if self.total_requests > 0 else 0
            }

class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on system load
    """
    
    def __init__(
        self, 
        base_rate: int = 100,
        window_size: int = 60,
        min_rate: int = 10,
        max_rate: int = 1000
    ):
        self.base_rate = base_rate
        self.current_rate = base_rate
        self.window_size = window_size
        self.min_rate = min_rate
        self.max_rate = max_rate
        
        self.limiter = SlidingWindowRateLimiter(self.current_rate, window_size)
        self.lock = threading.RLock()
        
        # Load metrics
        self.cpu_threshold = 80  # CPU usage percentage
        self.memory_threshold = 85  # Memory usage percentage
        self.error_rate_threshold = 0.1  # 10% error rate
        
        # Metrics
        self.adjustments = []
    
    def is_allowed(self, identifier: str = "default") -> bool:
        """Check if request is allowed with adaptive limits"""
        return self.limiter.is_allowed(identifier)
    
    def adjust_rate(self, cpu_usage: float, memory_usage: float, error_rate: float):
        """Adjust rate based on system metrics"""
        with self.lock:
            old_rate = self.current_rate
            
            if cpu_usage > self.cpu_threshold or memory_usage > self.memory_threshold:
                # Decrease rate if system is under load
                self.current_rate = max(
                    self.min_rate,
                    int(self.current_rate * 0.8)
                )
            elif error_rate > self.error_rate_threshold:
                # Decrease rate if error rate is high
                self.current_rate = max(
                    self.min_rate,
                    int(self.current_rate * 0.9)
                )
            elif cpu_usage < 50 and memory_usage < 50 and error_rate < 0.01:
                # Increase rate if system has capacity
                self.current_rate = min(
                    self.max_rate,
                    int(self.current_rate * 1.1)
                )
            
            if self.current_rate != old_rate:
                self.limiter = SlidingWindowRateLimiter(self.current_rate, self.window_size)
                self.adjustments.append({
                    "timestamp": time.time(),
                    "old_rate": old_rate,
                    "new_rate": self.current_rate,
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "error_rate": error_rate
                })
                logger.info(f"Adjusted rate limit from {old_rate} to {self.current_rate}")

# Decorators for easy usage

def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """Decorator to apply circuit breaker to a function"""
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        wrapper.get_state = breaker.get_state
        wrapper.get_metrics = breaker.get_metrics
        wrapper.reset = breaker.reset
        return wrapper
    
    return decorator

def rate_limit(rate: int = 100, per: int = 60):
    """Decorator to apply rate limiting to a function"""
    limiter = RateLimiter(rate, per)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not limiter.is_allowed():
                raise Exception(f"Rate limit exceeded for {func.__name__}")
            return func(*args, **kwargs)
        
        wrapper.get_metrics = limiter.get_metrics
        return wrapper
    
    return decorator

# Global instances for shared use
default_circuit_breaker = CircuitBreaker()
default_rate_limiter = RateLimiter()
adaptive_limiter = AdaptiveRateLimiter()

# Example usage
if __name__ == "__main__":
    import random
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=5)
    @rate_limit(rate=10, per=60)
    def example_api_call():
        """Example function with circuit breaker and rate limiting"""
        if random.random() < 0.3:  # 30% chance of failure
            raise Exception("API call failed")
        return "Success"
    
    # Test the decorators
    for i in range(20):
        try:
            result = example_api_call()
            print(f"Call {i+1}: {result}")
        except Exception as e:
            print(f"Call {i+1}: {e}")
        
        time.sleep(0.5)
    
    # Print metrics
    print("\nCircuit Breaker Metrics:", example_api_call.get_metrics())
    print("Rate Limiter Metrics:", example_api_call.get_metrics())