#!/usr/bin/env python3
"""
Input Validation and Sanitization Module
Prevents injection attacks and validates all user inputs
"""

import re
import html
import json
from typing import Any, Optional, Dict, List
from urllib.parse import quote, urlparse

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    def __init__(self):
        # Regex patterns for validation
        self.patterns = {
            "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            "phone": re.compile(r'^\+?[1-9]\d{1,14}$'),
            "alphanumeric": re.compile(r'^[a-zA-Z0-9]+$'),
            "numbers": re.compile(r'^\d+$'),
            "ethereum_address": re.compile(r'^0x[a-fA-F0-9]{40}$'),
            "url": re.compile(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            "safe_string": re.compile(r'^[a-zA-Z0-9\s\-_.]+$'),
        }
        
        # SQL injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|FROM|WHERE)\b)",
            r"(--|#|\/\*|\*\/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bAND\b\s+\d+\s*=\s*\d+)",
            r"('|\"|;|\\x00|\\n|\\r|\\x1a)",
        ]
        
        # Command injection patterns
        self.cmd_patterns = [
            r"(;|\||&|`|\$\(|\)|\{|\}|<|>|\\n)",
            r"(rm\s+-rf|sudo|chmod|chown|wget|curl|nc|bash)",
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe",
            r"<object",
            r"<embed",
        ]
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email or len(email) > 254:
            return False
        return bool(self.patterns["email"].match(email))
    
    def validate_ethereum_address(self, address: str) -> bool:
        """Validate Ethereum address format"""
        if not address:
            return False
        return bool(self.patterns["ethereum_address"].match(address))
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format and safety"""
        if not url or len(url) > 2048:
            return False
        
        # Basic format check
        if not self.patterns["url"].match(url):
            return False
        
        # Parse URL for additional validation
        try:
            parsed = urlparse(url)
            
            # Check for dangerous schemes
            if parsed.scheme not in ["http", "https"]:
                return False
            
            # Check for localhost/private IPs
            dangerous_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
            if parsed.hostname in dangerous_hosts:
                return False
            
            return True
        except:
            return False
    
    def sanitize_html(self, text: str) -> str:
        """Sanitize HTML to prevent XSS"""
        if not text:
            return ""
        
        # Escape HTML entities
        text = html.escape(text)
        
        # Remove any remaining dangerous patterns
        for pattern in self.xss_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
        return text
    
    def sanitize_sql(self, text: str) -> str:
        """Sanitize input to prevent SQL injection"""
        if not text:
            return ""
        
        # Remove SQL keywords and dangerous characters
        for pattern in self.sql_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
        # Escape single quotes
        text = text.replace("'", "''")
        
        return text
    
    def sanitize_command(self, text: str) -> str:
        """Sanitize input to prevent command injection"""
        if not text:
            return ""
        
        # Remove shell metacharacters and dangerous commands
        for pattern in self.cmd_patterns:
            text = re.sub(pattern, "", text)
        
        # Quote the string for shell safety
        return quote(text)
    
    def validate_json(self, json_str: str) -> Optional[Dict]:
        """Validate and parse JSON safely"""
        try:
            # Limit JSON size to prevent DoS
            if len(json_str) > 1000000:  # 1MB limit
                return None
            
            data = json.loads(json_str)
            
            # Validate it's a dict or list
            if not isinstance(data, (dict, list)):
                return None
            
            return data
        except:
            return None
    
    def validate_number(self, value: Any, min_val: float = None, max_val: float = None) -> Optional[float]:
        """Validate numeric input with bounds checking"""
        try:
            num = float(value)
            
            # Check for special values
            if not (-1e308 < num < 1e308):  # Prevent infinity
                return None
            
            if min_val is not None and num < min_val:
                return None
            
            if max_val is not None and num > max_val:
                return None
            
            return num
        except:
            return None
    
    def validate_file_path(self, path: str, base_dir: str = "/opt/qenex-os") -> Optional[str]:
        """Validate file path to prevent traversal attacks"""
        import os
        
        if not path:
            return None
        
        # Remove any null bytes
        path = path.replace("\x00", "")
        
        # Normalize the path
        path = os.path.normpath(path)
        
        # Make it absolute
        if not os.path.isabs(path):
            path = os.path.join(base_dir, path)
        
        # Resolve any symlinks
        try:
            path = os.path.realpath(path)
        except:
            return None
        
        # Ensure it's within the base directory
        if not path.startswith(base_dir):
            return None
        
        return path
    
    def validate_smart_contract_input(self, data: Dict) -> Dict:
        """Validate inputs for smart contract interactions"""
        validated = {}
        
        # Validate addresses
        if "address" in data:
            if not self.validate_ethereum_address(data["address"]):
                raise ValueError("Invalid Ethereum address")
            validated["address"] = data["address"]
        
        # Validate amounts (prevent overflow)
        if "amount" in data:
            amount = self.validate_number(data["amount"], min_val=0, max_val=10**27)
            if amount is None:
                raise ValueError("Invalid amount")
            validated["amount"] = amount
        
        # Validate gas parameters
        if "gasLimit" in data:
            gas = self.validate_number(data["gasLimit"], min_val=21000, max_val=10000000)
            if gas is None:
                raise ValueError("Invalid gas limit")
            validated["gasLimit"] = gas
        
        return validated
    
    def create_safe_filename(self, filename: str) -> str:
        """Create a safe filename from user input"""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 200:
            name = name[:200]
        
        return name + ext

# Global validator instance
validator = InputValidator()

def validate_api_request(request_data: Dict) -> Dict:
    """Validate API request data"""
    validated = {}
    
    # Validate common fields
    if "path" in request_data:
        path = validator.validate_file_path(request_data["path"])
        if not path:
            raise ValueError("Invalid path")
        validated["path"] = path
    
    if "email" in request_data:
        if not validator.validate_email(request_data["email"]):
            raise ValueError("Invalid email")
        validated["email"] = request_data["email"]
    
    if "url" in request_data:
        if not validator.validate_url(request_data["url"]):
            raise ValueError("Invalid URL")
        validated["url"] = request_data["url"]
    
    if "data" in request_data:
        validated["data"] = validator.sanitize_html(str(request_data["data"]))
    
    return validated

# Example usage and tests
if __name__ == "__main__":
    import os
    
    # Test email validation
    assert validator.validate_email("test@example.com") == True
    assert validator.validate_email("invalid.email") == False
    
    # Test Ethereum address
    assert validator.validate_ethereum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0") == True
    assert validator.validate_ethereum_address("invalid") == False
    
    # Test SQL sanitization
    dangerous_sql = "'; DROP TABLE users; --"
    safe_sql = validator.sanitize_sql(dangerous_sql)
    assert "DROP TABLE" not in safe_sql
    
    # Test XSS prevention
    xss_input = "<script>alert('XSS')</script>"
    safe_html = validator.sanitize_html(xss_input)
    assert "<script>" not in safe_html
    
    # Test path validation
    safe_path = validator.validate_file_path("data/config.json")
    assert safe_path and safe_path.startswith("/opt/qenex-os")
    
    dangerous_path = validator.validate_file_path("../../etc/passwd")
    assert dangerous_path is None
    
    print("✅ All validation tests passed!")