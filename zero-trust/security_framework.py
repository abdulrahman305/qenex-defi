#!/usr/bin/env python3
"""
QENEX Zero-Trust Security Framework
Comprehensive security architecture with identity verification, encryption, and access control
"""

import asyncio
import json
import time
import jwt
import hashlib
import secrets
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bcrypt
import pyotp
import qrcode
from io import BytesIO
import base64
import ssl
import aiohttp
from aiohttp import web, ClientSession

@dataclass
class User:
    """User identity information"""
    user_id: str
    username: str
    email: str
    password_hash: str
    mfa_secret: Optional[str] = None
    roles: List[str] = None
    permissions: List[str] = None
    created_at: float = 0
    last_login: float = 0
    failed_attempts: int = 0
    locked_until: float = 0
    
@dataclass
class Device:
    """Device registration information"""
    device_id: str
    user_id: str
    device_name: str
    device_type: str
    fingerprint: str
    trusted: bool = False
    last_seen: float = 0
    ip_address: str = ""
    user_agent: str = ""
    
@dataclass
class AccessRequest:
    """Access request for resource"""
    request_id: str
    user_id: str
    resource: str
    action: str
    context: Dict[str, Any]
    timestamp: float
    ip_address: str
    user_agent: str
    
@dataclass
class SecurityEvent:
    """Security event for monitoring"""
    event_id: str
    event_type: str
    user_id: Optional[str]
    resource: str
    action: str
    result: str  # allow, deny, error
    risk_score: int  # 1-100
    timestamp: float
    details: Dict[str, Any]

class QenexZeroTrustSecurity:
    """Zero-trust security framework"""
    
    def __init__(self, config_path: str = "/opt/qenex-os/config/security.json"):
        self.config_path = config_path
        self.users: Dict[str, User] = {}
        self.devices: Dict[str, Device] = {}
        self.active_sessions: Dict[str, Dict] = {}
        self.security_events: List[SecurityEvent] = []
        self.blocked_ips: Set[str] = set()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/qenex-os/logs/security.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QenexZeroTrustSecurity')
        
        # Load configuration and initialize
        self.load_config()
        self.init_crypto()
        self.load_user_data()
        
    def load_config(self):
        """Load security configuration"""
        default_config = {
            "enabled": True,
            "authentication": {
                "password_policy": {
                    "min_length": 12,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_digits": True,
                    "require_special": True,
                    "max_age_days": 90
                },
                "mfa_required": True,
                "session_timeout": 3600,
                "max_failed_attempts": 5,
                "lockout_duration": 1800
            },
            "authorization": {
                "default_deny": True,
                "rbac_enabled": True,
                "attribute_based": True,
                "policy_engine": "opa"  # Open Policy Agent
            },
            "encryption": {
                "algorithm": "AES-256-GCM",
                "key_rotation_days": 30,
                "tls_version": "1.3",
                "certificate_validation": True
            },
            "monitoring": {
                "audit_all_access": True,
                "anomaly_detection": True,
                "real_time_alerts": True,
                "retention_days": 365
            },
            "network": {
                "microsegmentation": True,
                "firewall_rules": [],
                "allowed_origins": ["https://qenex.ai"],
                "rate_limiting": {
                    "requests_per_minute": 100,
                    "burst_limit": 20
                }
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            self.config = default_config
            
    def save_config(self):
        """Save current configuration"""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def init_crypto(self):
        """Initialize cryptographic components"""
        try:
            # Generate or load RSA keys for JWT signing
            key_path = Path("/opt/qenex-os/config/jwt_private_key.pem")
            
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    self.private_key = serialization.load_pem_private_key(
                        f.read(), password=None
                    )
            else:
                self.private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                
                # Save private key
                key_path.parent.mkdir(parents=True, exist_ok=True)
                with open(key_path, 'wb') as f:
                    f.write(self.private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                    
            self.public_key = self.private_key.public_key()
            
            # Generate master encryption key
            self.master_key = secrets.token_bytes(32)  # 256-bit key
            
        except Exception as e:
            self.logger.error(f"Failed to initialize crypto: {e}")
            
    def load_user_data(self):
        """Load user and device data"""
        try:
            users_file = Path("/opt/qenex-os/data/users.json")
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
                    
                for user_data in users_data:
                    user = User(**user_data)
                    self.users[user.user_id] = user
                    
            devices_file = Path("/opt/qenex-os/data/devices.json")
            if devices_file.exists():
                with open(devices_file, 'r') as f:
                    devices_data = json.load(f)
                    
                for device_data in devices_data:
                    device = Device(**device_data)
                    self.devices[device.device_id] = device
                    
        except Exception as e:
            self.logger.warning(f"Failed to load user data: {e}")
            
    def save_user_data(self):
        """Save user and device data"""
        try:
            Path("/opt/qenex-os/data").mkdir(parents=True, exist_ok=True)
            
            # Save users
            users_data = [asdict(user) for user in self.users.values()]
            with open("/opt/qenex-os/data/users.json", 'w') as f:
                json.dump(users_data, f, indent=2)
                
            # Save devices
            devices_data = [asdict(device) for device in self.devices.values()]
            with open("/opt/qenex-os/data/devices.json", 'w') as f:
                json.dump(devices_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save user data: {e}")
            
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
        
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        
    def validate_password_policy(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password against policy"""
        policy = self.config["authentication"]["password_policy"]
        errors = []
        
        if len(password) < policy["min_length"]:
            errors.append(f"Password must be at least {policy['min_length']} characters")
            
        if policy["require_uppercase"] and not any(c.isupper() for c in password):
            errors.append("Password must contain uppercase letters")
            
        if policy["require_lowercase"] and not any(c.islower() for c in password):
            errors.append("Password must contain lowercase letters")
            
        if policy["require_digits"] and not any(c.isdigit() for c in password):
            errors.append("Password must contain digits")
            
        if policy["require_special"] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain special characters")
            
        return len(errors) == 0, errors
        
    def generate_device_fingerprint(self, request_info: Dict) -> str:
        """Generate device fingerprint"""
        fingerprint_data = {
            'user_agent': request_info.get('user_agent', ''),
            'accept_language': request_info.get('accept_language', ''),
            'screen_resolution': request_info.get('screen_resolution', ''),
            'timezone': request_info.get('timezone', ''),
            'plugins': request_info.get('plugins', [])
        }
        
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
        
    def setup_mfa(self, user_id: str) -> Tuple[str, str]:
        """Setup multi-factor authentication for user"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
            
        # Generate secret
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        
        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="QENEX AI OS"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Convert QR code to base64
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        self.save_user_data()
        return secret, qr_code_base64
        
    def verify_mfa(self, user_id: str, token: str) -> bool:
        """Verify MFA token"""
        user = self.users.get(user_id)
        if not user or not user.mfa_secret:
            return False
            
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window tolerance
        
    async def authenticate_user(self, username: str, password: str, mfa_token: Optional[str] = None, 
                               request_info: Dict = None) -> Tuple[bool, Optional[str], List[str]]:
        """Authenticate user with credentials"""
        errors = []
        
        # Find user
        user = None
        for u in self.users.values():
            if u.username == username or u.email == username:
                user = u
                break
                
        if not user:
            self.log_security_event("auth_failed", None, "login", "deny", 
                                   {"reason": "user_not_found", "username": username})
            return False, None, ["Invalid credentials"]
            
        # Check if account is locked
        if user.locked_until > time.time():
            remaining = int(user.locked_until - time.time())
            self.log_security_event("auth_failed", user.user_id, "login", "deny",
                                   {"reason": "account_locked", "remaining_seconds": remaining})
            return False, None, [f"Account locked for {remaining} seconds"]
            
        # Verify password
        if not self.verify_password(password, user.password_hash):
            user.failed_attempts += 1
            
            # Lock account if too many failures
            max_attempts = self.config["authentication"]["max_failed_attempts"]
            if user.failed_attempts >= max_attempts:
                lockout_duration = self.config["authentication"]["lockout_duration"]
                user.locked_until = time.time() + lockout_duration
                
            self.save_user_data()
            self.log_security_event("auth_failed", user.user_id, "login", "deny",
                                   {"reason": "invalid_password", "attempts": user.failed_attempts})
            return False, None, ["Invalid credentials"]
            
        # Verify MFA if required
        if self.config["authentication"]["mfa_required"] and user.mfa_secret:
            if not mfa_token:
                return False, None, ["MFA token required"]
                
            if not self.verify_mfa(user.user_id, mfa_token):
                self.log_security_event("auth_failed", user.user_id, "login", "deny",
                                       {"reason": "invalid_mfa"})
                return False, None, ["Invalid MFA token"]
                
        # Check device trust
        if request_info:
            device_fingerprint = self.generate_device_fingerprint(request_info)
            device = self.get_or_create_device(user.user_id, device_fingerprint, request_info)
            
            if not device.trusted:
                # Device verification required
                return False, None, ["Device verification required"]
                
        # Authentication successful
        user.failed_attempts = 0
        user.last_login = time.time()
        self.save_user_data()
        
        # Generate JWT token
        token = self.generate_jwt_token(user)
        
        self.log_security_event("auth_success", user.user_id, "login", "allow", 
                               {"ip_address": request_info.get("ip_address") if request_info else None})
        
        return True, token, []
        
    def get_or_create_device(self, user_id: str, fingerprint: str, request_info: Dict) -> Device:
        """Get or create device registration"""
        # Find existing device
        for device in self.devices.values():
            if device.user_id == user_id and device.fingerprint == fingerprint:
                device.last_seen = time.time()
                device.ip_address = request_info.get("ip_address", "")
                device.user_agent = request_info.get("user_agent", "")
                return device
                
        # Create new device
        device_id = secrets.token_urlsafe(16)
        device = Device(
            device_id=device_id,
            user_id=user_id,
            device_name=request_info.get("device_name", "Unknown Device"),
            device_type=request_info.get("device_type", "unknown"),
            fingerprint=fingerprint,
            trusted=False,  # Requires manual approval
            last_seen=time.time(),
            ip_address=request_info.get("ip_address", ""),
            user_agent=request_info.get("user_agent", "")
        )
        
        self.devices[device_id] = device
        self.save_user_data()
        
        return device
        
    def generate_jwt_token(self, user: User) -> str:
        """Generate JWT token for authenticated user"""
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'roles': user.roles or [],
            'permissions': user.permissions or [],
            'iat': int(time.time()),
            'exp': int(time.time() + self.config["authentication"]["session_timeout"]),
            'iss': 'qenex-ai-os',
            'aud': 'qenex-services'
        }
        
        return jwt.encode(payload, self.private_key, algorithm='RS256')
        
    def verify_jwt_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.public_key, algorithms=['RS256'])
            
            # Check if token is expired
            if payload['exp'] < time.time():
                return False, None
                
            return True, payload
            
        except jwt.InvalidTokenError:
            return False, None
            
    def authorize_access(self, access_request: AccessRequest) -> Tuple[bool, str, int]:
        """Authorize access to resource"""
        try:
            # Get user permissions
            user = self.users.get(access_request.user_id)
            if not user:
                return False, "User not found", 100
                
            # Check if user is active
            if user.locked_until > time.time():
                return False, "Account locked", 90
                
            # Risk assessment
            risk_score = self.calculate_risk_score(access_request)
            
            # Policy engine - simplified implementation
            allowed = self.evaluate_access_policy(access_request, user, risk_score)
            
            result = "allow" if allowed else "deny"
            reason = "Policy evaluation" if allowed else "Access denied by policy"
            
            # Log security event
            self.log_security_event("access_request", access_request.user_id, 
                                   access_request.resource, result,
                                   {"action": access_request.action, "risk_score": risk_score})
            
            return allowed, reason, risk_score
            
        except Exception as e:
            self.logger.error(f"Authorization error: {e}")
            return False, "Authorization error", 100
            
    def evaluate_access_policy(self, request: AccessRequest, user: User, risk_score: int) -> bool:
        """Evaluate access policy"""
        # Default deny if configured
        if self.config["authorization"]["default_deny"]:
            allowed = False
        else:
            allowed = True
            
        # Role-based access control
        if self.config["authorization"]["rbac_enabled"]:
            required_permissions = self.get_required_permissions(request.resource, request.action)
            user_permissions = set(user.permissions or [])
            
            if not required_permissions.issubset(user_permissions):
                allowed = False
                
        # Attribute-based access control
        if self.config["authorization"]["attribute_based"]:
            # Check time-based access
            current_hour = datetime.now().hour
            if current_hour < 6 or current_hour > 22:  # Outside business hours
                if "after_hours_access" not in (user.permissions or []):
                    allowed = False
                    
            # Check location-based access
            if self.is_suspicious_location(request.ip_address):
                if "remote_access" not in (user.permissions or []):
                    allowed = False
                    
        # Risk-based access control
        if risk_score > 70:
            allowed = False
            
        return allowed
        
    def get_required_permissions(self, resource: str, action: str) -> Set[str]:
        """Get required permissions for resource and action"""
        # Resource permission mapping
        permission_map = {
            "admin": {"read", "write", "delete", "admin"},
            "user_data": {"read", "write"},
            "system_config": {"admin"},
            "backup": {"backup", "restore"},
            "logs": {"audit", "read"}
        }
        
        # Action permission mapping
        action_permissions = {
            "read": {"read"},
            "write": {"write"},
            "delete": {"delete"},
            "admin": {"admin"}
        }
        
        required = set()
        
        # Add resource permissions
        for resource_pattern, perms in permission_map.items():
            if resource_pattern in resource:
                required.update(perms)
                break
                
        # Add action permissions
        if action in action_permissions:
            required.update(action_permissions[action])
            
        return required
        
    def calculate_risk_score(self, request: AccessRequest) -> int:
        """Calculate risk score for access request"""
        risk_score = 0
        
        # IP reputation check
        if self.is_suspicious_ip(request.ip_address):
            risk_score += 30
            
        # Geolocation anomaly
        if self.is_suspicious_location(request.ip_address):
            risk_score += 20
            
        # Time-based anomaly
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            risk_score += 15
            
        # User behavior anomaly
        user = self.users.get(request.user_id)
        if user and user.last_login > 0:
            time_since_last = time.time() - user.last_login
            if time_since_last > 86400 * 30:  # 30 days
                risk_score += 25
                
        # Resource sensitivity
        if "admin" in request.resource or "config" in request.resource:
            risk_score += 20
            
        # Action risk
        if request.action in ["delete", "admin", "modify"]:
            risk_score += 15
            
        return min(risk_score, 100)
        
    def is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address is suspicious"""
        # Check against blocked IPs
        if ip_address in self.blocked_ips:
            return True
            
        # Check against known threat feeds (simplified)
        suspicious_ranges = [
            "10.0.0.",    # Example suspicious range
            "192.168.1."  # Internal network access from external
        ]
        
        for suspicious in suspicious_ranges:
            if ip_address.startswith(suspicious):
                return True
                
        return False
        
    def is_suspicious_location(self, ip_address: str) -> bool:
        """Check if location is suspicious (simplified geolocation)"""
        # In production, use actual GeoIP database
        return False  # Placeholder
        
    def log_security_event(self, event_type: str, user_id: Optional[str], 
                          resource: str, result: str, details: Dict[str, Any]):
        """Log security event"""
        event = SecurityEvent(
            event_id=secrets.token_urlsafe(16),
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=details.get("action", "unknown"),
            result=result,
            risk_score=details.get("risk_score", 0),
            timestamp=time.time(),
            details=details
        )
        
        self.security_events.append(event)
        
        # Keep only recent events in memory
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-500:]
            
        # Log to file
        self.logger.info(f"Security Event: {event_type} - {result} - User: {user_id} - Resource: {resource}")
        
        # Save to persistent storage
        self.save_security_events()
        
    def save_security_events(self):
        """Save security events to file"""
        try:
            events_file = Path("/opt/qenex-os/data/security_events.json")
            events_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save recent events
            recent_events = [asdict(event) for event in self.security_events[-100:]]
            with open(events_file, 'w') as f:
                json.dump(recent_events, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save security events: {e}")
            
    def encrypt_data(self, data: bytes, context: str = "") -> Tuple[bytes, bytes]:
        """Encrypt data with AES-256-GCM"""
        # Generate random IV
        iv = secrets.token_bytes(12)  # GCM IV size
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.master_key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        
        # Add context as additional authenticated data
        if context:
            encryptor.authenticate_additional_data(context.encode())
            
        # Encrypt data
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Return ciphertext and tag+iv
        auth_data = encryptor.tag + iv
        
        return ciphertext, auth_data
        
    def decrypt_data(self, ciphertext: bytes, auth_data: bytes, context: str = "") -> bytes:
        """Decrypt data with AES-256-GCM"""
        # Extract tag and IV
        tag = auth_data[:16]
        iv = auth_data[16:]
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.master_key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        
        # Add context as additional authenticated data
        if context:
            decryptor.authenticate_additional_data(context.encode())
            
        # Decrypt data
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext
        
    def create_user(self, username: str, email: str, password: str, 
                   roles: List[str] = None, permissions: List[str] = None) -> str:
        """Create new user"""
        # Validate password
        valid, errors = self.validate_password_policy(password)
        if not valid:
            raise ValueError(f"Password policy violation: {', '.join(errors)}")
            
        # Check if user exists
        for user in self.users.values():
            if user.username == username or user.email == email:
                raise ValueError("User already exists")
                
        # Create user
        user_id = secrets.token_urlsafe(16)
        password_hash = self.hash_password(password)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            roles=roles or ["user"],
            permissions=permissions or ["read"],
            created_at=time.time()
        )
        
        self.users[user_id] = user
        self.save_user_data()
        
        self.log_security_event("user_created", user_id, "user_management", "allow",
                               {"username": username, "roles": roles})
        
        return user_id
        
    def get_security_dashboard(self) -> Dict:
        """Get security dashboard data"""
        try:
            now = time.time()
            last_24h = now - 86400
            last_week = now - 604800
            
            # Count events by type in last 24h
            recent_events = [e for e in self.security_events if e.timestamp > last_24h]
            event_counts = {}
            
            for event in recent_events:
                event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
                
            # Security metrics
            total_users = len(self.users)
            active_sessions = len(self.active_sessions)
            blocked_ips = len(self.blocked_ips)
            
            # Risk assessment
            high_risk_events = [e for e in recent_events if e.risk_score > 70]
            avg_risk_score = sum(e.risk_score for e in recent_events) / len(recent_events) if recent_events else 0
            
            # Authentication metrics
            auth_success = len([e for e in recent_events if e.event_type == "auth_success"])
            auth_failed = len([e for e in recent_events if e.event_type == "auth_failed"])
            auth_success_rate = auth_success / (auth_success + auth_failed) * 100 if (auth_success + auth_failed) > 0 else 100
            
            return {
                "overview": {
                    "total_users": total_users,
                    "active_sessions": active_sessions,
                    "blocked_ips": blocked_ips,
                    "events_24h": len(recent_events)
                },
                "authentication": {
                    "success_rate": round(auth_success_rate, 2),
                    "successful_logins": auth_success,
                    "failed_attempts": auth_failed,
                    "mfa_enabled_users": len([u for u in self.users.values() if u.mfa_secret])
                },
                "risk_assessment": {
                    "high_risk_events": len(high_risk_events),
                    "average_risk_score": round(avg_risk_score, 1),
                    "threat_level": "HIGH" if avg_risk_score > 60 else "MEDIUM" if avg_risk_score > 30 else "LOW"
                },
                "recent_events": event_counts,
                "compliance": {
                    "encryption_enabled": True,
                    "audit_logging": True,
                    "mfa_enforcement": self.config["authentication"]["mfa_required"],
                    "zero_trust_active": True
                },
                "timestamp": now
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate security dashboard: {e}")
            return {"error": str(e)}
            
    async def create_web_server(self):
        """Create web server for security API"""
        app = web.Application()
        
        # Authentication endpoint
        async def handle_login(request):
            try:
                data = await request.json()
                username = data.get('username')
                password = data.get('password')
                mfa_token = data.get('mfa_token')
                
                request_info = {
                    'ip_address': request.remote,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'device_name': data.get('device_name', 'Unknown'),
                    'device_type': data.get('device_type', 'unknown')
                }
                
                success, token, errors = await self.authenticate_user(
                    username, password, mfa_token, request_info
                )
                
                if success:
                    return web.json_response({
                        'success': True,
                        'token': token,
                        'expires_in': self.config["authentication"]["session_timeout"]
                    })
                else:
                    return web.json_response({
                        'success': False,
                        'errors': errors
                    }, status=401)
                    
            except Exception as e:
                return web.json_response({'error': str(e)}, status=500)
                
        # Security dashboard endpoint
        async def handle_dashboard(request):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return web.json_response({'error': 'Unauthorized'}, status=401)
                
            token = auth_header[7:]
            valid, payload = self.verify_jwt_token(token)
            
            if not valid:
                return web.json_response({'error': 'Invalid token'}, status=401)
                
            dashboard_data = self.get_security_dashboard()
            return web.json_response(dashboard_data)
            
        app.router.add_post('/api/auth/login', handle_login)
        app.router.add_get('/api/security/dashboard', handle_dashboard)
        
        return app
        
    async def start(self):
        """Start the zero-trust security system"""
        self.logger.info("Starting QENEX Zero-Trust Security Framework")
        
        # Create default admin user if none exists
        if not self.users:
            admin_password = secrets.token_urlsafe(16)
            admin_id = self.create_user(
                "admin",
                "admin@qenex.ai", 
                admin_password,
                ["admin"],
                ["admin", "read", "write", "delete", "backup", "restore", "audit"]
            )
            
            self.logger.info(f"Created default admin user. Password: {admin_password}")
            
        # Create web server
        app = await self.create_web_server()
        
        # Start web server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, "0.0.0.0", 8003)
        await site.start()
        
        self.logger.info("Security API server started on port 8003")
        
        # Keep running
        try:
            while self.config.get('enabled', True):
                await asyncio.sleep(60)
                # Periodic cleanup and maintenance
                self.cleanup_expired_sessions()
                
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
            
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        session_timeout = self.config["authentication"]["session_timeout"]
        
        expired_sessions = [
            session_id for session_id, session_data in self.active_sessions.items()
            if current_time - session_data.get('created_at', 0) > session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
            
    def stop(self):
        """Stop the security system"""
        self.logger.info("Stopping QENEX Zero-Trust Security Framework")
        self.config['enabled'] = False

async def main():
    """Main entry point"""
    security_system = QenexZeroTrustSecurity()
    
    try:
        await security_system.start()
    except KeyboardInterrupt:
        security_system.stop()
        print("\nSecurity system stopped")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())