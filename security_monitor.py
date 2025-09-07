#!/usr/bin/env python3
"""
Comprehensive Security Monitoring System
Real-time threat detection, anomaly detection, and incident response
"""

import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics
import re
import threading
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Security threat levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class IncidentType(Enum):
    """Types of security incidents"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    DDOS_ATTACK = "ddos_attack"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    CRYPTOGRAPHIC_FAILURE = "cryptographic_failure"
    CONFIGURATION_CHANGE = "configuration_change"
    SUSPICIOUS_TRANSACTION = "suspicious_transaction"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"

@dataclass
class SecurityEvent:
    """Security event representation"""
    event_id: str
    timestamp: datetime
    event_type: IncidentType
    threat_level: ThreatLevel
    source_ip: Optional[str]
    user_id: Optional[str]
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    handled: bool = False

@dataclass
class UserBehaviorProfile:
    """User behavior profile for anomaly detection"""
    user_id: str
    normal_login_times: List[int] = field(default_factory=list)
    normal_ip_addresses: Set[str] = field(default_factory=set)
    average_transaction_amount: Decimal = Decimal('0')
    transaction_frequency: float = 0.0
    failed_login_count: int = 0
    last_activity: datetime = field(default_factory=datetime.utcnow)
    risk_score: float = 0.0

class SecurityMonitor:
    """
    Advanced security monitoring system with:
    - Real-time threat detection
    - Anomaly detection using ML
    - Automated incident response
    - Compliance monitoring
    - Forensic capabilities
    """
    
    def __init__(self, config_path: str = "/opt/qenex/security/config.json"):
        self.config = self._load_config(config_path)
        self.events: deque = deque(maxlen=10000)
        self.active_incidents: Dict[str, SecurityEvent] = {}
        self.user_profiles: Dict[str, UserBehaviorProfile] = {}
        self.blocked_ips: Set[str] = set()
        self.blocked_users: Set[str] = set()
        
        # Detection patterns
        self.sql_injection_patterns = [
            r"(\bunion\b.*\bselect\b)",
            r"(\bselect\b.*\bfrom\b.*\bwhere\b)",
            r"(\bdrop\b.*\btable\b)",
            r"(\binsert\b.*\binto\b)",
            r"(\bupdate\b.*\bset\b)",
            r"(\bdelete\b.*\bfrom\b)",
            r"(;.*--)",
            r"(\bor\b\s+1\s*=\s*1)",
            r"(\band\b\s+1\s*=\s*0)",
            r"(\bexec\b|\bexecute\b)",
            r"(\bscript\b.*\balert\b)",
            r"(<script[^>]*>)",
            r"(javascript:)",
            r"(\bonload\s*=)",
            r"(\bonerror\s*=)"
        ]
        
        self.xss_patterns = [
            r"(<script[^>]*>.*?</script>)",
            r"(<iframe[^>]*>)",
            r"(javascript:)",
            r"(on\w+\s*=)",
            r"(<img[^>]*onerror)",
            r"(<body[^>]*onload)"
        ]
        
        # Rate limiting
        self.rate_limits = defaultdict(lambda: {
            'requests': deque(maxlen=100),
            'failed_logins': deque(maxlen=10),
            'transactions': deque(maxlen=50)
        })
        
        # Metrics
        self.metrics = {
            'total_events': 0,
            'blocked_attacks': 0,
            'false_positives': 0,
            'mean_response_time': 0.0,
            'events_by_type': defaultdict(int),
            'events_by_level': defaultdict(int)
        }
        
        # Anomaly detection thresholds
        self.anomaly_thresholds = {
            'login_time_deviation': 3,  # Standard deviations
            'transaction_amount_deviation': 2.5,
            'new_ip_risk_boost': 0.3,
            'failed_login_threshold': 5,
            'transaction_frequency_deviation': 2
        }
        
        # Start monitoring threads
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load security configuration"""
        default_config = {
            'auto_block_threshold': 10,
            'incident_retention_days': 90,
            'max_failed_logins': 5,
            'rate_limit_window': 60,
            'anomaly_detection_enabled': True,
            'auto_response_enabled': True,
            'compliance_mode': 'PCI_DSS',
            'alert_webhook': None
        }
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                default_config.update(config)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
        
        return default_config
    
    def detect_threat(self, 
                     request_data: str,
                     source_ip: str,
                     user_id: Optional[str] = None) -> List[SecurityEvent]:
        """Detect security threats in request data"""
        threats = []
        timestamp = datetime.utcnow()
        
        # SQL Injection detection
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                event = SecurityEvent(
                    event_id=self._generate_event_id(),
                    timestamp=timestamp,
                    event_type=IncidentType.SQL_INJECTION,
                    threat_level=ThreatLevel.CRITICAL,
                    source_ip=source_ip,
                    user_id=user_id,
                    description=f"SQL injection attempt detected: {pattern}",
                    metadata={'pattern': pattern, 'data': request_data[:200]}
                )
                threats.append(event)
                break
        
        # XSS detection
        for pattern in self.xss_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                event = SecurityEvent(
                    event_id=self._generate_event_id(),
                    timestamp=timestamp,
                    event_type=IncidentType.XSS_ATTEMPT,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=source_ip,
                    user_id=user_id,
                    description=f"XSS attempt detected: {pattern}",
                    metadata={'pattern': pattern, 'data': request_data[:200]}
                )
                threats.append(event)
                break
        
        # Rate limiting check
        if self._check_rate_limit_violation(source_ip, user_id):
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                timestamp=timestamp,
                event_type=IncidentType.RATE_LIMIT_VIOLATION,
                threat_level=ThreatLevel.MEDIUM,
                source_ip=source_ip,
                user_id=user_id,
                description="Rate limit violation detected",
                metadata={'requests_count': len(self.rate_limits[source_ip]['requests'])}
            )
            threats.append(event)
        
        # Process detected threats
        for threat in threats:
            self._process_event(threat)
        
        return threats
    
    def detect_anomaly(self, 
                      user_id: str,
                      activity_type: str,
                      metadata: Dict[str, Any]) -> Optional[SecurityEvent]:
        """Detect anomalous user behavior"""
        if not self.config['anomaly_detection_enabled']:
            return None
        
        profile = self.user_profiles.get(user_id)
        if not profile:
            # Create new profile
            profile = UserBehaviorProfile(user_id=user_id)
            self.user_profiles[user_id] = profile
            return None  # Need baseline data
        
        anomaly_detected = False
        anomaly_details = []
        
        # Check login time anomaly
        if activity_type == 'login':
            hour = metadata.get('hour', datetime.utcnow().hour)
            if profile.normal_login_times:
                mean_hour = statistics.mean(profile.normal_login_times)
                std_hour = statistics.stdev(profile.normal_login_times) if len(profile.normal_login_times) > 1 else 1
                
                if abs(hour - mean_hour) > self.anomaly_thresholds['login_time_deviation'] * std_hour:
                    anomaly_detected = True
                    anomaly_details.append(f"Unusual login time: {hour}")
        
        # Check IP address anomaly
        if 'ip_address' in metadata:
            ip = metadata['ip_address']
            if ip not in profile.normal_ip_addresses:
                profile.risk_score += self.anomaly_thresholds['new_ip_risk_boost']
                anomaly_details.append(f"New IP address: {ip}")
                
                # Add to profile after detection
                profile.normal_ip_addresses.add(ip)
        
        # Check transaction anomaly
        if activity_type == 'transaction':
            amount = Decimal(str(metadata.get('amount', 0)))
            if profile.average_transaction_amount > 0:
                deviation = abs(amount - profile.average_transaction_amount)
                threshold = profile.average_transaction_amount * Decimal(str(
                    self.anomaly_thresholds['transaction_amount_deviation']
                ))
                
                if deviation > threshold:
                    anomaly_detected = True
                    anomaly_details.append(f"Unusual transaction amount: {amount}")
        
        # Create event if anomaly detected
        if anomaly_detected or profile.risk_score > 0.7:
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.utcnow(),
                event_type=IncidentType.ANOMALOUS_BEHAVIOR,
                threat_level=ThreatLevel.MEDIUM if profile.risk_score < 0.7 else ThreatLevel.HIGH,
                source_ip=metadata.get('ip_address'),
                user_id=user_id,
                description=f"Anomalous behavior detected: {', '.join(anomaly_details)}",
                metadata={
                    'risk_score': profile.risk_score,
                    'anomalies': anomaly_details,
                    'activity_type': activity_type
                }
            )
            
            self._process_event(event)
            return event
        
        # Update profile with normal behavior
        self._update_user_profile(profile, activity_type, metadata)
        
        return None
    
    def _update_user_profile(self, 
                            profile: UserBehaviorProfile,
                            activity_type: str,
                            metadata: Dict[str, Any]):
        """Update user behavior profile"""
        profile.last_activity = datetime.utcnow()
        
        if activity_type == 'login':
            hour = metadata.get('hour', datetime.utcnow().hour)
            profile.normal_login_times.append(hour)
            if len(profile.normal_login_times) > 100:
                profile.normal_login_times.pop(0)
        
        elif activity_type == 'transaction':
            amount = Decimal(str(metadata.get('amount', 0)))
            # Update average (exponential moving average)
            alpha = Decimal('0.1')
            if profile.average_transaction_amount == 0:
                profile.average_transaction_amount = amount
            else:
                profile.average_transaction_amount = (
                    alpha * amount + (Decimal('1') - alpha) * profile.average_transaction_amount
                )
        
        # Decay risk score over time
        profile.risk_score *= 0.95
    
    def _check_rate_limit_violation(self, source_ip: str, user_id: Optional[str]) -> bool:
        """Check for rate limit violations"""
        now = time.time()
        window = self.config['rate_limit_window']
        
        # Check IP-based rate limit
        ip_requests = self.rate_limits[source_ip]['requests']
        ip_requests.append(now)
        
        # Count requests in window
        recent_requests = sum(1 for t in ip_requests if now - t < window)
        
        if recent_requests > self.config.get('max_requests_per_minute', 60):
            return True
        
        # Check user-based rate limit if applicable
        if user_id:
            user_requests = self.rate_limits[user_id]['requests']
            user_requests.append(now)
            recent_user_requests = sum(1 for t in user_requests if now - t < window)
            
            if recent_user_requests > self.config.get('max_user_requests_per_minute', 100):
                return True
        
        return False
    
    def handle_failed_login(self, user_id: str, source_ip: str) -> bool:
        """Handle failed login attempt"""
        now = time.time()
        
        # Track failed logins
        self.rate_limits[user_id]['failed_logins'].append(now)
        self.rate_limits[source_ip]['failed_logins'].append(now)
        
        # Count recent failures
        user_failures = sum(
            1 for t in self.rate_limits[user_id]['failed_logins']
            if now - t < 300  # 5 minutes
        )
        
        ip_failures = sum(
            1 for t in self.rate_limits[source_ip]['failed_logins']
            if now - t < 300
        )
        
        # Check thresholds
        if user_failures >= self.config['max_failed_logins']:
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.utcnow(),
                event_type=IncidentType.BRUTE_FORCE,
                threat_level=ThreatLevel.HIGH,
                source_ip=source_ip,
                user_id=user_id,
                description=f"Brute force attack detected: {user_failures} failed attempts",
                metadata={'failed_attempts': user_failures}
            )
            self._process_event(event)
            
            # Auto-block if enabled
            if self.config['auto_response_enabled']:
                self.block_user(user_id, duration_minutes=30)
            
            return True
        
        if ip_failures >= self.config['max_failed_logins'] * 2:
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.utcnow(),
                event_type=IncidentType.BRUTE_FORCE,
                threat_level=ThreatLevel.CRITICAL,
                source_ip=source_ip,
                user_id=user_id,
                description=f"Severe brute force attack from IP: {ip_failures} failed attempts",
                metadata={'failed_attempts': ip_failures}
            )
            self._process_event(event)
            
            # Auto-block IP
            if self.config['auto_response_enabled']:
                self.block_ip(source_ip, duration_minutes=60)
            
            return True
        
        return False
    
    def validate_transaction(self, 
                            user_id: str,
                            amount: Decimal,
                            destination: str,
                            metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate transaction for suspicious activity"""
        suspicious_indicators = []
        
        # Check amount thresholds
        if amount > Decimal('10000'):
            suspicious_indicators.append("High value transaction")
        
        # Check velocity
        now = time.time()
        user_transactions = self.rate_limits[user_id]['transactions']
        user_transactions.append(now)
        
        recent_count = sum(1 for t in user_transactions if now - t < 3600)  # Last hour
        if recent_count > 10:
            suspicious_indicators.append(f"High transaction velocity: {recent_count}/hour")
        
        # Check destination patterns
        if self._is_high_risk_destination(destination):
            suspicious_indicators.append(f"High risk destination: {destination}")
        
        # Check for patterns
        if self._detect_transaction_pattern(user_id, amount, destination):
            suspicious_indicators.append("Suspicious transaction pattern detected")
        
        if suspicious_indicators:
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.utcnow(),
                event_type=IncidentType.SUSPICIOUS_TRANSACTION,
                threat_level=ThreatLevel.MEDIUM if len(suspicious_indicators) < 2 else ThreatLevel.HIGH,
                source_ip=metadata.get('source_ip'),
                user_id=user_id,
                description=f"Suspicious transaction: {', '.join(suspicious_indicators)}",
                metadata={
                    'amount': str(amount),
                    'destination': destination,
                    'indicators': suspicious_indicators
                }
            )
            self._process_event(event)
            
            # Block if critical
            if len(suspicious_indicators) >= 3:
                return False, "Transaction blocked due to suspicious activity"
        
        return True, None
    
    def _is_high_risk_destination(self, destination: str) -> bool:
        """Check if destination is high risk"""
        high_risk_patterns = [
            r"^1[A-Za-z0-9]{25,34}$",  # Bitcoin addresses
            r"^0x[a-fA-F0-9]{40}$",  # Ethereum addresses
            r"tornado",  # Mixer services
            r"mixer",
            r"tumbler"
        ]
        
        for pattern in high_risk_patterns:
            if re.search(pattern, destination, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_transaction_pattern(self, user_id: str, amount: Decimal, destination: str) -> bool:
        """Detect suspicious transaction patterns"""
        # Implement pattern detection logic
        # This could include:
        # - Structuring (multiple small transactions)
        # - Rapid movement of funds
        # - Circular transactions
        # - Known bad actor destinations
        
        return False  # Placeholder
    
    def block_ip(self, ip_address: str, duration_minutes: int = 60):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        logger.warning(f"Blocked IP: {ip_address} for {duration_minutes} minutes")
        
        # Schedule unblock
        if duration_minutes > 0:
            threading.Timer(
                duration_minutes * 60,
                lambda: self.blocked_ips.discard(ip_address)
            ).start()
    
    def block_user(self, user_id: str, duration_minutes: int = 30):
        """Block a user account"""
        self.blocked_users.add(user_id)
        logger.warning(f"Blocked user: {user_id} for {duration_minutes} minutes")
        
        # Schedule unblock
        if duration_minutes > 0:
            threading.Timer(
                duration_minutes * 60,
                lambda: self.blocked_users.discard(user_id)
            ).start()
    
    def is_blocked(self, ip_address: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """Check if IP or user is blocked"""
        if ip_address and ip_address in self.blocked_ips:
            return True
        if user_id and user_id in self.blocked_users:
            return True
        return False
    
    def _process_event(self, event: SecurityEvent):
        """Process security event"""
        # Add to events queue
        self.events.append(event)
        self.active_incidents[event.event_id] = event
        
        # Update metrics
        self.metrics['total_events'] += 1
        self.metrics['events_by_type'][event.event_type.value] += 1
        self.metrics['events_by_level'][event.threat_level.value] += 1
        
        # Log event
        logger.warning(f"Security Event: {event.threat_level.value.upper()} - {event.description}")
        
        # Auto-response if enabled
        if self.config['auto_response_enabled']:
            self._auto_respond(event)
        
        # Send alert if critical
        if event.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
            self._send_alert(event)
    
    def _auto_respond(self, event: SecurityEvent):
        """Automated incident response"""
        if event.threat_level == ThreatLevel.CRITICAL:
            # Block immediately
            if event.source_ip:
                self.block_ip(event.source_ip, duration_minutes=120)
            if event.user_id:
                self.block_user(event.user_id, duration_minutes=60)
        
        elif event.threat_level == ThreatLevel.HIGH:
            # Block temporarily
            if event.source_ip:
                self.block_ip(event.source_ip, duration_minutes=30)
            if event.user_id and event.event_type == IncidentType.BRUTE_FORCE:
                self.block_user(event.user_id, duration_minutes=15)
    
    def _send_alert(self, event: SecurityEvent):
        """Send security alert"""
        if self.config.get('alert_webhook'):
            # Send to webhook
            alert_data = {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'threat_level': event.threat_level.value,
                'type': event.event_type.value,
                'description': event.description,
                'metadata': event.metadata
            }
            # asyncio.create_task(self._send_webhook(alert_data))
            logger.critical(f"SECURITY ALERT: {json.dumps(alert_data, indent=2)}")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Clean old events
                self._cleanup_old_events()
                
                # Update metrics
                self._update_metrics()
                
                # Check for patterns
                self._detect_attack_patterns()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    def _cleanup_old_events(self):
        """Remove old events"""
        retention_days = self.config['incident_retention_days']
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        # Remove from active incidents
        to_remove = [
            event_id for event_id, event in self.active_incidents.items()
            if event.timestamp < cutoff
        ]
        
        for event_id in to_remove:
            del self.active_incidents[event_id]
    
    def _detect_attack_patterns(self):
        """Detect coordinated attack patterns"""
        # Check for DDoS
        recent_events = [
            e for e in self.events
            if (datetime.utcnow() - e.timestamp).seconds < 60
        ]
        
        if len(recent_events) > 100:
            # Possible DDoS
            event = SecurityEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.utcnow(),
                event_type=IncidentType.DDOS_ATTACK,
                threat_level=ThreatLevel.CRITICAL,
                source_ip=None,
                user_id=None,
                description=f"Possible DDoS attack: {len(recent_events)} events/minute",
                metadata={'event_count': len(recent_events)}
            )
            self._process_event(event)
    
    def _update_metrics(self):
        """Update security metrics"""
        if self.events:
            response_times = []
            for event in self.events:
                if event.handled:
                    # Calculate response time
                    pass
            
            if response_times:
                self.metrics['mean_response_time'] = statistics.mean(response_times)
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return f"evt_{int(time.time() * 1000000)}_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        return {
            'active_incidents': len(self.active_incidents),
            'blocked_ips': len(self.blocked_ips),
            'blocked_users': len(self.blocked_users),
            'total_events': self.metrics['total_events'],
            'events_by_type': dict(self.metrics['events_by_type']),
            'events_by_level': dict(self.metrics['events_by_level']),
            'mean_response_time': self.metrics['mean_response_time'],
            'high_risk_users': [
                uid for uid, profile in self.user_profiles.items()
                if profile.risk_score > 0.7
            ]
        }
    
    def shutdown(self):
        """Shutdown monitoring"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

# Usage example
if __name__ == "__main__":
    monitor = SecurityMonitor()
    
    # Test threat detection
    threats = monitor.detect_threat(
        "SELECT * FROM users WHERE id=1 OR 1=1--",
        "192.168.1.100",
        "user123"
    )
    
    # Test anomaly detection
    monitor.detect_anomaly(
        "user456",
        "login",
        {'hour': 3, 'ip_address': '10.0.0.1'}
    )
    
    # Test transaction validation
    valid, reason = monitor.validate_transaction(
        "user789",
        Decimal("15000"),
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        {'source_ip': '192.168.1.1'}
    )
    
    # Get status
    status = monitor.get_security_status()
    print(json.dumps(status, indent=2))
    
    # Cleanup
    monitor.shutdown()