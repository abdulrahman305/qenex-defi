#!/usr/bin/env python3
"""
QENEX AI Security Training System
Self-learning security monitoring with pattern recognition
"""

import json
import os
import time
import hashlib
import subprocess
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import re
import base64
import hmac
from pathlib import Path
from typing import Dict, List, Optional, Any
import signal
import sys
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Security constants
MAX_LOG_SIZE = 100 * 1024 * 1024  # 100MB
MAX_PATTERN_COUNT = 1000
MAX_INCIDENT_HISTORY = 10000
SECURE_DELETE_PASSES = 3

class QenexSecurityAI:
    def __init__(self):
        # Use JSON instead of pickle for security
        self.model_path = "/opt/qenex/models/security_ai.json"
        self.log_path = "/var/log/qenex/ai_security.log"
        self.patterns_db = "/opt/qenex/security_patterns.json"
        self.training_data = "/opt/qenex/training/security_data.json"
        
        # Thread safety
        self.lock = threading.RLock()
        self._shutdown = False
        
        # Security key for data integrity
        self.security_key = self._generate_security_key()
        
        # Create directories securely
        self._create_secure_directories()
        
        # Initialize attack patterns first
        self.initialize_patterns()
        
        # Initialize or load model
        self.load_model()
        
        # Register cleanup
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def initialize_patterns(self):
        
        # Attack patterns database
        self.attack_patterns = {
            "ssh_bruteforce": {
                "indicators": [
                    r"Failed password",
                    r"Invalid user",
                    r"Connection reset by peer",
                    r"ssh.*139\.99",
                    r"multiple SSH connections"
                ],
                "threshold": 5,
                "time_window": 300,  # 5 minutes
                "severity": "critical",
                "learned_patterns": []
            },
            "port_scanning": {
                "indicators": [
                    r"SYN_SENT",
                    r"Connection refused",
                    r"nmap|masscan|zmap",
                    r"rapid connection attempts"
                ],
                "threshold": 10,
                "time_window": 60,
                "severity": "high",
                "learned_patterns": []
            },
            "malware": {
                "indicators": [
                    r"xmr|miner|crypto",
                    r"/tmp/.*\.sh",
                    r"curl.*\|.*sh",
                    r"wget.*\|.*bash",
                    r"base64.*decode"
                ],
                "threshold": 1,
                "time_window": 3600,
                "severity": "critical",
                "learned_patterns": []
            },
            "data_exfiltration": {
                "indicators": [
                    r"large outbound transfer",
                    r"unusual DNS queries",
                    r"tar.*\|.*nc",
                    r"scp.*sensitive",
                    r"rsync.*unauthorized"
                ],
                "threshold": 3,
                "time_window": 1800,
                "severity": "high",
                "learned_patterns": []
            }
        }
        
        # Behavioral baseline
        self.baseline = {
            "normal_ssh_rate": 5,  # connections per hour
            "normal_cpu_usage": 30,  # percentage
            "normal_network_connections": 50,
            "normal_processes": 150,
            "learned_behaviors": []
        }
        
        # Incident history for learning
        self.incident_history = []
        
    def _generate_security_key(self) -> bytes:
        """Generate security key for data integrity"""
        key_file = "/opt/qenex/.security_key"
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception:
                pass
        
        # Generate new key
        key = os.urandom(32)
        try:
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure file permissions
            os.chmod(key_file, 0o600)
        except Exception as e:
            logger.warning(f"Could not save security key: {e}")
        return key
    
    def _create_secure_directories(self):
        """Create directories with secure permissions"""
        directories = [
            os.path.dirname(self.model_path),
            os.path.dirname(self.log_path),
            os.path.dirname(self.training_data)
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                # Secure permissions - only owner can read/write/execute
                os.chmod(directory, 0o700)
            except Exception as e:
                logger.error(f"Failed to create secure directory {directory}: {e}")
                raise
    
    def _calculate_integrity_hash(self, data: Any) -> str:
        """Calculate HMAC for data integrity using SHA256"""
        data_bytes = json.dumps(data, sort_keys=True).encode('utf-8')
        return hmac.new(self.security_key, data_bytes, hashlib.sha256).hexdigest()
    
    def _verify_integrity(self, data: Any, expected_hash: str) -> bool:
        """Verify data integrity"""
        calculated_hash = self._calculate_integrity_hash(data)
        return hmac.compare_digest(calculated_hash, expected_hash)
    
    def load_model(self):
        """Load or initialize the AI model using secure JSON format"""
        with self.lock:
            if os.path.exists(self.model_path):
                try:
                    with open(self.model_path, 'r') as f:
                        saved_data = json.load(f)
                    
                    # Verify data integrity
                    if 'integrity_hash' in saved_data:
                        model_data = saved_data.get('model_data', {})
                        if not self._verify_integrity(model_data, saved_data['integrity_hash']):
                            logger.warning("Model data integrity check failed, reinitializing")
                            self.log("Model integrity compromised - reinitializing", "WARNING")
                            return
                        
                        self.attack_patterns = model_data.get('patterns', self.attack_patterns)
                        self.baseline = model_data.get('baseline', self.baseline)
                        # Limit history size to prevent memory issues
                        history = model_data.get('history', [])
                        self.incident_history = history[-MAX_INCIDENT_HISTORY:] if history else []
                        self.log("Model loaded from disk with integrity verification")
                    else:
                        logger.warning("Model file missing integrity hash, reinitializing")
                        self.log("Model missing integrity verification - reinitializing", "WARNING")
                        
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.error(f"Failed to load model: {e}")
                    self.log(f"Model loading failed: {e} - reinitializing", "ERROR")
                except Exception as e:
                    logger.error(f"Unexpected error loading model: {e}")
                    self.log(f"Unexpected error loading model: {e}", "ERROR")
            else:
                self.log("Initialized new model")
    
    def save_model(self):
        """Save the trained model using secure JSON format"""
        with self.lock:
            try:
                # Limit incident history size
                limited_history = self.incident_history[-MAX_INCIDENT_HISTORY:]
                
                model_data = {
                    'patterns': self.attack_patterns,
                    'baseline': self.baseline,
                    'history': limited_history,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Calculate integrity hash
                integrity_hash = self._calculate_integrity_hash(model_data)
                
                save_data = {
                    'model_data': model_data,
                    'integrity_hash': integrity_hash,
                    'version': '2.0'  # Version for future compatibility
                }
                
                # Write to temporary file first for atomic operation
                temp_path = self.model_path + '.tmp'
                with open(temp_path, 'w') as f:
                    json.dump(save_data, f, indent=2)
                
                # Atomic rename
                os.rename(temp_path, self.model_path)
                
                # Secure file permissions
                os.chmod(self.model_path, 0o600)
                
                self.log("Model saved to disk with integrity protection")
                
            except Exception as e:
                logger.error(f"Failed to save model: {e}")
                self.log(f"Model save failed: {e}", "ERROR")
                # Clean up temp file if it exists
                temp_path = self.model_path + '.tmp'
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
    
    def log(self, message, level="INFO"):
        """Log events with timestamp and proper security measures"""
        try:
            # Sanitize message to prevent log injection
            safe_message = re.sub(r'[\r\n\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(message))
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {safe_message}\n"
            
            # Check log file size and rotate if needed
            if os.path.exists(self.log_path) and os.path.getsize(self.log_path) > MAX_LOG_SIZE:
                self._rotate_log()
            
            with open(self.log_path, 'a') as f:
                f.write(log_entry)
            
            # Also log to system logger
            if level == "CRITICAL":
                logger.critical(safe_message)
            elif level == "ERROR":
                logger.error(safe_message)
            elif level == "WARNING":
                logger.warning(safe_message)
            else:
                logger.info(safe_message)
            
            # Console output with colors
            if level in ["WARNING", "CRITICAL", "ERROR"]:
                print(f"\033[91m{log_entry}\033[0m", end="")
            else:
                print(log_entry, end="")
                
        except Exception as e:
            # Fallback logging to stderr
            print(f"Logging error: {e}", file=sys.stderr)
    
    def _rotate_log(self):
        """Rotate log file when it gets too large"""
        try:
            backup_path = f"{self.log_path}.{int(time.time())}"
            os.rename(self.log_path, backup_path)
            
            # Compress old log if possible
            try:
                import gzip
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(backup_path)
            except ImportError:
                pass  # gzip not available, keep uncompressed
            
        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
    
    def collect_system_data(self):
        """Collect current system state for analysis"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "connections": self.get_network_connections(),
            "processes": self.get_processes(),
            "ssh_activity": self.get_ssh_activity(),
            "system_load": self.get_system_load(),
            "firewall_events": self.get_firewall_events()
        }
        return data
    
    def get_network_connections(self):
        """Get current network connections"""
        try:
            result = subprocess.run(['ss', '-tunap'], capture_output=True, text=True)
            connections = result.stdout.strip().split('\n')
            return {
                "total": len(connections),
                "details": connections[:100]  # Limit for performance
            }
        except:
            return {"total": 0, "details": []}
    
    def get_processes(self):
        """Get running processes"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            processes = result.stdout.strip().split('\n')
            suspicious = []
            for proc in processes:
                if any(pattern in proc.lower() for pattern in ['miner', 'xmr', 'scan', 'brute']):
                    suspicious.append(proc)
            return {
                "total": len(processes),
                "suspicious": suspicious
            }
        except:
            return {"total": 0, "suspicious": []}
    
    def get_ssh_activity(self):
        """Analyze SSH activity"""
        try:
            # Check active SSH connections
            result = subprocess.run(['ss', '-tunp'], capture_output=True, text=True)
            ssh_connections = [line for line in result.stdout.split('\n') if ':22' in line]
            
            # Check for outbound SSH to suspicious IPs
            suspicious_ssh = []
            for conn in ssh_connections:
                if any(ip in conn for ip in ['139.99', '203.99']):
                    suspicious_ssh.append(conn)
            
            return {
                "active_connections": len(ssh_connections),
                "suspicious": suspicious_ssh
            }
        except:
            return {"active_connections": 0, "suspicious": []}
    
    def get_system_load(self):
        """Get system resource usage"""
        try:
            # CPU usage
            with open('/proc/loadavg', 'r') as f:
                load = f.read().strip().split()
            
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            mem_total = int(re.search(r'MemTotal:\s+(\d+)', meminfo).group(1))
            mem_free = int(re.search(r'MemAvailable:\s+(\d+)', meminfo).group(1))
            mem_used_percent = ((mem_total - mem_free) / mem_total) * 100
            
            return {
                "load_average": float(load[0]),
                "memory_usage": round(mem_used_percent, 2)
            }
        except:
            return {"load_average": 0, "memory_usage": 0}
    
    def get_firewall_events(self):
        """Check firewall blocks"""
        try:
            result = subprocess.run(['iptables', '-L', '-n', '-v'], capture_output=True, text=True)
            drops = [line for line in result.stdout.split('\n') if 'DROP' in line]
            return {
                "total_drops": len(drops),
                "rules": drops[:10]
            }
        except:
            return {"total_drops": 0, "rules": []}
    
    def analyze_threat(self, data):
        """Analyze collected data for threats using AI patterns"""
        threats = []
        
        # Check each attack pattern
        for attack_type, pattern_info in self.attack_patterns.items():
            score = 0
            matched_indicators = []
            
            # Check indicators
            data_str = json.dumps(data)
            for indicator in pattern_info["indicators"]:
                if re.search(indicator, data_str, re.IGNORECASE):
                    score += 1
                    matched_indicators.append(indicator)
            
            # Check learned patterns
            for learned in pattern_info.get("learned_patterns", []):
                if learned in data_str:
                    score += 2  # Learned patterns have higher weight
                    matched_indicators.append(f"[LEARNED] {learned}")
            
            # Evaluate threat
            if score >= pattern_info["threshold"]:
                threats.append({
                    "type": attack_type,
                    "severity": pattern_info["severity"],
                    "score": score,
                    "indicators": matched_indicators,
                    "confidence": min(score * 20, 100)  # Confidence percentage
                })
        
        # Behavioral anomaly detection
        anomalies = self.detect_anomalies(data)
        if anomalies:
            threats.extend(anomalies)
        
        return threats
    
    def detect_anomalies(self, data):
        """Detect behavioral anomalies"""
        anomalies = []
        
        # Check SSH connection rate
        ssh_count = data["ssh_activity"]["active_connections"]
        if ssh_count > self.baseline["normal_ssh_rate"] * 2:
            anomalies.append({
                "type": "anomaly_ssh_rate",
                "severity": "medium",
                "description": f"SSH connections ({ssh_count}) exceed baseline ({self.baseline['normal_ssh_rate']})",
                "confidence": 70
            })
        
        # Check system load
        load = data["system_load"]["load_average"]
        if load > self.baseline["normal_cpu_usage"] / 10:
            anomalies.append({
                "type": "anomaly_high_load",
                "severity": "medium",
                "description": f"System load ({load}) is unusually high",
                "confidence": 60
            })
        
        # Check process count
        proc_count = data["processes"]["total"]
        if abs(proc_count - self.baseline["normal_processes"]) > 50:
            anomalies.append({
                "type": "anomaly_process_count",
                "severity": "low",
                "description": f"Unusual process count ({proc_count})",
                "confidence": 50
            })
        
        return anomalies
    
    def learn_from_incident(self, incident_data, was_true_positive):
        """Learn from incident feedback"""
        self.incident_history.append({
            "timestamp": datetime.now().isoformat(),
            "data": incident_data,
            "true_positive": was_true_positive
        })
        
        if was_true_positive:
            # Extract patterns from true positive
            self.extract_patterns(incident_data)
            self.log("Learned from true positive incident")
        else:
            # Adjust thresholds for false positive
            self.adjust_thresholds(incident_data)
            self.log("Adjusted thresholds based on false positive")
        
        # Update baseline periodically
        if len(self.incident_history) % 10 == 0:
            self.update_baseline()
        
        self.save_model()
    
    def extract_patterns(self, incident_data):
        """Extract new patterns from incidents with security limits"""
        with self.lock:
            try:
                # Look for repeated strings that might be attack signatures
                data_str = json.dumps(incident_data)
                
                # Find IP addresses involved (with validation)
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                potential_ips = re.findall(ip_pattern, data_str)
                
                # Validate and filter IPs
                ips = []
                for ip in potential_ips:
                    parts = ip.split('.')
                    if all(0 <= int(part) <= 255 for part in parts):
                        ips.append(ip)
                
                # Find suspicious commands (with safer regex)
                cmd_pattern = r'\b(curl|wget|nc|ssh|scp)\s+[^\s]+'
                commands = re.findall(cmd_pattern, data_str)
                
                # Add to learned patterns with limits
                for attack_type in self.attack_patterns:
                    if attack_type in data_str.lower():
                        learned_patterns = self.attack_patterns[attack_type]["learned_patterns"]
                        
                        # Limit learned patterns to prevent memory exhaustion
                        if len(learned_patterns) >= MAX_PATTERN_COUNT:
                            # Remove oldest patterns (FIFO)
                            learned_patterns = learned_patterns[-MAX_PATTERN_COUNT//2:]
                            self.attack_patterns[attack_type]["learned_patterns"] = learned_patterns
                        
                        for ip in ips[:3]:  # Further limit to avoid noise
                            if ip not in learned_patterns:
                                learned_patterns.append(ip)
                        
                        for cmd in commands[:2]:  # Limit commands
                            # Sanitize command to prevent injection
                            safe_cmd = re.sub(r'[^\w\s\.\-]', '', cmd)
                            if safe_cmd and safe_cmd not in learned_patterns:
                                learned_patterns.append(safe_cmd)
                                
            except Exception as e:
                logger.error(f"Error extracting patterns: {e}")
                self.log(f"Pattern extraction error: {e}", "ERROR")
    
    def adjust_thresholds(self, incident_data):
        """Adjust detection thresholds based on false positives"""
        for attack_type in self.attack_patterns:
            if attack_type in json.dumps(incident_data).lower():
                # Increase threshold slightly to reduce false positives
                self.attack_patterns[attack_type]["threshold"] += 1
                self.log(f"Increased threshold for {attack_type} to {self.attack_patterns[attack_type]['threshold']}")
    
    def update_baseline(self):
        """Update behavioral baseline from historical data"""
        if not self.incident_history:
            return
        
        # Calculate averages from recent history
        recent = self.incident_history[-20:]  # Last 20 incidents
        
        ssh_rates = []
        proc_counts = []
        
        for incident in recent:
            if "data" in incident and not incident.get("true_positive", False):
                data = incident["data"]
                if "ssh_activity" in data:
                    ssh_rates.append(data["ssh_activity"]["active_connections"])
                if "processes" in data:
                    proc_counts.append(data["processes"]["total"])
        
        if ssh_rates:
            self.baseline["normal_ssh_rate"] = sum(ssh_rates) // len(ssh_rates)
        if proc_counts:
            self.baseline["normal_processes"] = sum(proc_counts) // len(proc_counts)
        
        self.log("Updated behavioral baseline")
    
    def respond_to_threat(self, threat):
        """Automated response to detected threats"""
        response_log = []
        
        if threat["type"] == "ssh_bruteforce":
            # Block outbound SSH to suspicious networks
            subprocess.run(['iptables', '-I', 'OUTPUT', '-p', 'tcp', '--dport', '22', 
                          '-d', '139.99.0.0/16', '-j', 'DROP'], capture_output=True)
            response_log.append("Blocked SSH to suspicious networks")
            
            # Kill suspicious SSH processes
            subprocess.run(['pkill', '-f', 'ssh.*139.99'], capture_output=True)
            response_log.append("Terminated suspicious SSH connections")
            
        elif threat["type"] == "malware":
            # Kill malware processes
            for proc in threat.get("indicators", []):
                if "miner" in proc or "xmr" in proc:
                    subprocess.run(['pkill', '-f', proc], capture_output=True)
            response_log.append("Terminated malware processes")
            
        elif threat["type"] == "port_scanning":
            # Rate limit connections
            subprocess.run(['iptables', '-I', 'OUTPUT', '-p', 'tcp', '-m', 'limit',
                          '--limit', '10/min', '-j', 'ACCEPT'], capture_output=True)
            response_log.append("Applied rate limiting")
        
        return response_log
    
    def generate_report(self, threats, responses):
        """Generate security report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "server": subprocess.run(['hostname', '-I'], capture_output=True, text=True).stdout.strip(),
            "threats_detected": len(threats),
            "threats": threats,
            "responses": responses,
            "model_accuracy": self.calculate_accuracy(),
            "recommendations": self.generate_recommendations(threats)
        }
        
        # Save report
        report_path = f"/opt/qenex/reports/security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def calculate_accuracy(self):
        """Calculate model accuracy from history"""
        if not self.incident_history:
            return 0
        
        true_positives = sum(1 for i in self.incident_history if i.get("true_positive", False))
        total = len(self.incident_history)
        
        return round((true_positives / total) * 100, 2) if total > 0 else 0
    
    def generate_recommendations(self, threats):
        """Generate security recommendations based on threats"""
        recommendations = []
        
        if any(t["type"] == "ssh_bruteforce" for t in threats):
            recommendations.append("Implement fail2ban for SSH protection")
            recommendations.append("Use SSH keys instead of passwords")
            recommendations.append("Change SSH port from default 22")
        
        if any(t["type"] == "malware" for t in threats):
            recommendations.append("Install and configure ClamAV")
            recommendations.append("Regular system integrity checks")
            recommendations.append("Implement application whitelisting")
        
        if any(t["type"] == "port_scanning" for t in threats):
            recommendations.append("Configure port knocking")
            recommendations.append("Implement IDS/IPS system")
            recommendations.append("Use honeypots to detect scanners")
        
        return recommendations
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self._shutdown = True
        self.log(f"Received signal {signum}, shutting down gracefully...")
    
    def _secure_delete_file(self, file_path: str):
        """Securely delete a file by overwriting it"""
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                with open(file_path, 'r+b') as f:
                    for _ in range(SECURE_DELETE_PASSES):
                        f.seek(0)
                        f.write(os.urandom(file_size))
                        f.flush()
                        os.fsync(f.fileno())
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Secure delete failed for {file_path}: {e}")
    
    def shutdown(self):
        """Properly shutdown the security system"""
        with self.lock:
            if not self._shutdown:
                self._shutdown = True
                self.log("Shutting down QENEX AI Security System...")
                
                # Save final model state
                try:
                    self.save_model()
                except Exception as e:
                    logger.error(f"Error saving model during shutdown: {e}")
                
                self.log("QENEX AI Security System shutdown complete")
    
    def continuous_monitoring(self):
        """Main monitoring loop with proper error handling and security"""
        self.log("QENEX AI Security Training System started", "INFO")
        
        try:
            while not self._shutdown:
                try:
                    # Collect system data
                    data = self.collect_system_data()
                    
                    # Analyze for threats
                    threats = self.analyze_threat(data)
                    
                    responses = []
                    if threats:
                        self.log(f"Detected {len(threats)} threats", "WARNING")
                        
                        for threat in threats:
                            confidence = threat.get('confidence', 0)
                            self.log(f"Threat: {threat['type']} (Confidence: {confidence}%)", "CRITICAL")
                            
                            # Automated response for high confidence threats
                            if confidence > 70 and not self._shutdown:
                                try:
                                    response = self.respond_to_threat(threat)
                                    responses.extend(response)
                                except Exception as e:
                                    self.log(f"Threat response failed: {e}", "ERROR")
                        
                        # Generate report
                        try:
                            report = self.generate_report(threats, responses)
                            # Don't log full report in continuous mode to avoid log spam
                            self.log(f"Report generated with {len(threats)} threats")
                        except Exception as e:
                            self.log(f"Report generation failed: {e}", "ERROR")
                        
                        # Learn from this incident (would need human feedback in production)
                        try:
                            self.learn_from_incident(data, True)
                        except Exception as e:
                            self.log(f"Learning failed: {e}", "ERROR")
                    
                    # Save model periodically
                    if datetime.now().minute % 10 == 0 and not self._shutdown:
                        try:
                            self.save_model()
                        except Exception as e:
                            self.log(f"Periodic model save failed: {e}", "ERROR")
                    
                    # Sleep before next check (with interruption support)
                    for _ in range(60):  # Check every minute
                        if self._shutdown:
                            break
                        time.sleep(1)
                        
                except KeyboardInterrupt:
                    self.log("Monitoring stopped by user")
                    break
                except Exception as e:
                    self.log(f"Error in monitoring loop: {str(e)}", "ERROR")
                    # Wait before retrying, but allow interruption
                    for _ in range(60):
                        if self._shutdown:
                            break
                        time.sleep(1)
                        
        finally:
            self.shutdown()
    
    def __del__(self):
        """Destructor with proper cleanup"""
        try:
            self.shutdown()
        except:
            pass  # Ignore errors in destructor

def main():
    import sys
    
    ai = QenexSecurityAI()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "monitor":
            ai.continuous_monitoring()
        elif command == "analyze":
            data = ai.collect_system_data()
            threats = ai.analyze_threat(data)
            print(json.dumps(threats, indent=2))
        elif command == "report":
            data = ai.collect_system_data()
            threats = ai.analyze_threat(data)
            report = ai.generate_report(threats, [])
            print(json.dumps(report, indent=2))
        elif command == "train":
            # Simulate training with feedback
            data = ai.collect_system_data()
            ai.learn_from_incident(data, True)
            print("Model trained with current data")
        elif command == "accuracy":
            print(f"Model accuracy: {ai.calculate_accuracy()}%")
        else:
            print("Unknown command")
    else:
        print("QENEX AI Security Training System")
        print("Usage: python3 ai_security_trainer.py [monitor|analyze|report|train|accuracy]")
        print("  monitor  - Start continuous monitoring")
        print("  analyze  - Analyze current system state")
        print("  report   - Generate security report")
        print("  train    - Train model with current data")
        print("  accuracy - Show model accuracy")

if __name__ == "__main__":
    main()