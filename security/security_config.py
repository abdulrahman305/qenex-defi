#!/usr/bin/env python3
"""
QENEX Security Configuration
Centralized security settings to fix critical vulnerabilities
"""

import os
import secrets
from typing import Dict, Any

# Security Configuration
SECURITY_CONFIG = {
    # Network Configuration - NO HARDCODED IPs
    "HOST": os.getenv("QENEX_HOST", "127.0.0.1"),  # Default to localhost only
    "PORT": int(os.getenv("QENEX_PORT", "8080")),
    "ALLOWED_HOSTS": os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(","),
    
    # API Security
    "API_RATE_LIMIT": 100,  # requests per minute
    "API_BURST_SIZE": 20,   # burst allowance
    "API_KEY_REQUIRED": True,
    "API_KEY": os.getenv("QENEX_API_KEY", secrets.token_urlsafe(32)),
    
    # Cryptography
    "HASH_ALGORITHM": "sha256",  # Never use MD5
    "SALT_LENGTH": 32,
    "KEY_DERIVATION_ITERATIONS": 100000,
    
    # Smart Contract Security
    "REENTRANCY_GUARD": True,
    "MAX_SLIPPAGE": 300,  # 3% max slippage
    "MULTISIG_THRESHOLD": 2,
    "TIMELOCK_DELAY": 48 * 3600,  # 48 hours
    
    # Access Control
    "REQUIRE_AUTH": True,
    "SESSION_TIMEOUT": 3600,  # 1 hour
    "MAX_LOGIN_ATTEMPTS": 5,
    "LOCKOUT_DURATION": 900,  # 15 minutes
    
    # Logging and Monitoring
    "AUDIT_LOG": True,
    "LOG_LEVEL": "INFO",
    "LOG_FILE": "/opt/qenex-os/logs/security.log",
    "ALERT_CRITICAL": True,
    
    # Input Validation
    "MAX_INPUT_LENGTH": 10000,
    "ALLOWED_CHARS": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
    "SANITIZE_HTML": True,
    
    # Resource Limits
    "MAX_MEMORY_MB": 512,
    "MAX_CPU_PERCENT": 50,
    "MAX_CONNECTIONS": 100,
    "CONNECTION_TIMEOUT": 30,
}

# Security Headers
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}

def get_secure_config() -> Dict[str, Any]:
    """Get secure configuration with environment overrides"""
    config = SECURITY_CONFIG.copy()
    
    # Override with environment variables if set
    for key in config:
        env_key = f"QENEX_{key}"
        if env_key in os.environ:
            config[key] = os.environ[env_key]
    
    return config

def validate_input(input_str: str, max_length: int = None) -> bool:
    """Validate and sanitize input"""
    if not input_str:
        return False
    
    max_length = max_length or SECURITY_CONFIG["MAX_INPUT_LENGTH"]
    
    if len(input_str) > max_length:
        return False
    
    # Check for common injection patterns
    dangerous_patterns = [
        "<script", "javascript:", "onclick", "onerror",
        "'; DROP TABLE", "1=1", "/*", "*/", "--",
        "../", "..\\", "%00", "\x00", "\r", "\n\r"
    ]
    
    input_lower = input_str.lower()
    for pattern in dangerous_patterns:
        if pattern in input_lower:
            return False
    
    return True

def sanitize_path(path: str) -> str:
    """Sanitize file paths to prevent traversal attacks"""
    # Remove any path traversal attempts
    path = path.replace("../", "").replace("..\\", "")
    path = os.path.normpath(path)
    
    # Ensure path doesn't escape base directory
    base_dir = "/opt/qenex-os"
    full_path = os.path.abspath(os.path.join(base_dir, path))
    
    if not full_path.startswith(base_dir):
        raise ValueError("Path traversal attempt detected")
    
    return full_path

def generate_secure_token() -> str:
    """Generate cryptographically secure token"""
    return secrets.token_urlsafe(32)

def hash_password(password: str, salt: bytes = None) -> tuple:
    """Securely hash password with salt"""
    import hashlib
    
    if salt is None:
        salt = secrets.token_bytes(SECURITY_CONFIG["SALT_LENGTH"])
    
    key = hashlib.pbkdf2_hmac(
        SECURITY_CONFIG["HASH_ALGORITHM"],
        password.encode(),
        salt,
        SECURITY_CONFIG["KEY_DERIVATION_ITERATIONS"]
    )
    
    return key, salt