#!/usr/bin/env python3
"""
Comprehensive Error Handler for QENEX OS
Provides robust error handling, logging, and recovery mechanisms
"""

import sys
import traceback
import logging
import json
import time
from typing import Any, Callable, Optional, Dict, Type
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/qenex-os/logs/error.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('QENEX')

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorContext:
    """Context for error handling"""
    error_type: Type[Exception]
    severity: ErrorSeverity
    retry_count: int = 3
    retry_delay: float = 1.0
    fallback_value: Any = None
    should_log: bool = True
    should_alert: bool = False

class QenexError(Exception):
    """Base exception for QENEX system"""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, details: Optional[Dict] = None):
        self.message = message
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict:
        """Convert error to dictionary"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp
        }

class ValidationError(QenexError):
    """Validation error"""
    pass

class ResourceError(QenexError):
    """Resource limitation error"""
    pass

class NetworkError(QenexError):
    """Network-related error"""
    pass

class ContractError(QenexError):
    """Smart contract error"""
    pass

def with_retry(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for automatic retry with exponential backoff"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {retries} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {retries} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def safe_execute(func: Callable, fallback: Any = None, log_errors: bool = True):
    """Safely execute a function with fallback"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_errors:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return fallback
    
    return wrapper

class ErrorHandler:
    """Comprehensive error handler"""
    
    def __init__(self):
        self.error_count: Dict[str, int] = {}
        self.error_history: list = []
        self.max_history = 1000
        
    def handle(self, error: Exception, context: Optional[ErrorContext] = None) -> Any:
        """Handle an error with context"""
        
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "timestamp": time.time(),
            "traceback": traceback.format_exc()
        }
        
        # Log error
        if context and context.should_log:
            self._log_error(error, context)
        
        # Track error
        self._track_error(error_info)
        
        # Alert if needed
        if context and context.should_alert:
            self._send_alert(error, context)
        
        # Return fallback value if provided
        if context and context.fallback_value is not None:
            return context.fallback_value
        
        # Re-raise if critical
        if context and context.severity == ErrorSeverity.CRITICAL:
            raise error
        
        return None
    
    def _log_error(self, error: Exception, context: ErrorContext):
        """Log error based on severity"""
        
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {error}", exc_info=True)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {error}", exc_info=True)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {error}")
        else:
            logger.info(f"Low severity error: {error}")
    
    def _track_error(self, error_info: Dict):
        """Track error for analytics"""
        
        error_type = error_info["type"]
        
        # Count errors by type
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1
        
        # Add to history
        self.error_history.append(error_info)
        
        # Limit history size
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def _send_alert(self, error: Exception, context: ErrorContext):
        """Send alert for critical errors"""
        
        alert = {
            "severity": context.severity.value,
            "error": str(error),
            "timestamp": time.time(),
            "details": {
                "error_type": type(error).__name__,
                "traceback": traceback.format_exc()
            }
        }
        
        # Write alert to file
        try:
            with open('/opt/qenex-os/logs/alerts.json', 'a') as f:
                json.dump(alert, f)
                f.write('\n')
        except:
            pass
    
    def get_statistics(self) -> Dict:
        """Get error statistics"""
        
        return {
            "total_errors": sum(self.error_count.values()),
            "errors_by_type": self.error_count,
            "recent_errors": len(self.error_history),
            "most_common": max(self.error_count.items(), key=lambda x: x[1])[0] if self.error_count else None
        }

# Global error handler instance
error_handler = ErrorHandler()

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    
    # Handle with global error handler
    context = ErrorContext(
        error_type=exc_type,
        severity=ErrorSeverity.CRITICAL,
        should_log=True,
        should_alert=True
    )
    
    error_handler.handle(exc_value, context)

# Install global exception handler
sys.excepthook = handle_exception

# Example usage
if __name__ == "__main__":
    
    # Example 1: Function with retry
    @with_retry(retries=3, delay=0.5)
    def unreliable_function():
        """Function that might fail"""
        import random
        if random.random() < 0.7:
            raise NetworkError("Connection failed", ErrorSeverity.MEDIUM)
        return "Success!"
    
    # Example 2: Safe execution with fallback
    @safe_execute
    def risky_operation(x, y):
        """Operation that might fail"""
        return x / y
    
    safe_divide = safe_execute(lambda x, y: x / y, fallback=0)
    
    # Example 3: Error context
    try:
        raise ValidationError(
            "Invalid input",
            ErrorSeverity.HIGH,
            {"field": "amount", "value": -100}
        )
    except ValidationError as e:
        context = ErrorContext(
            error_type=ValidationError,
            severity=e.severity,
            fallback_value={"status": "error", "message": str(e)}
        )
        result = error_handler.handle(e, context)
        print(f"Handled error, result: {result}")
    
    # Show statistics
    print("\n📊 Error Statistics:")
    print(json.dumps(error_handler.get_statistics(), indent=2))