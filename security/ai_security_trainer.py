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
from datetime import datetime, timedelta
from collections import defaultdict
import pickle
import re

class QenexSecurityAI:
    def __init__(self):
        self.model_path = "/opt/qenex/models/security_ai.pkl"
        self.log_path = "/var/log/qenex/ai_security.log"
        self.patterns_db = "/opt/qenex/security_patterns.json"
        self.training_data = "/opt/qenex/training/security_data.json"
        
        # Create directories
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.training_data), exist_ok=True)
        
        # Initialize attack patterns first
        self.initialize_patterns()
        
        # Initialize or load model
        self.load_model()
    
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
        
    def load_model(self):
        """Load or initialize the AI model"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                saved_data = pickle.load(f)
                self.attack_patterns = saved_data.get('patterns', self.attack_patterns)
                self.baseline = saved_data.get('baseline', self.baseline)
                self.incident_history = saved_data.get('history', [])
            self.log("Model loaded from disk")
        else:
            self.log("Initialized new model")
    
    def save_model(self):
        """Save the trained model"""
        model_data = {
            'patterns': self.attack_patterns,
            'baseline': self.baseline,
            'history': self.incident_history,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        self.log("Model saved to disk")
    
    def log(self, message, level="INFO"):
        """Log events with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        with open(self.log_path, 'a') as f:
            f.write(log_entry)
        if level in ["WARNING", "CRITICAL"]:
            print(f"\033[91m{log_entry}\033[0m", end="")
        else:
            print(log_entry, end="")
    
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
        """Extract new patterns from incidents"""
        # Look for repeated strings that might be attack signatures
        data_str = json.dumps(incident_data)
        
        # Find IP addresses involved
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, data_str)
        
        # Find suspicious commands
        cmd_pattern = r'(curl|wget|nc|ssh|scp).*[;&|]'
        commands = re.findall(cmd_pattern, data_str)
        
        # Add to learned patterns
        for attack_type in self.attack_patterns:
            if attack_type in data_str.lower():
                for ip in ips[:5]:  # Limit to avoid noise
                    if ip not in self.attack_patterns[attack_type]["learned_patterns"]:
                        self.attack_patterns[attack_type]["learned_patterns"].append(ip)
                
                for cmd in commands[:3]:
                    if cmd not in self.attack_patterns[attack_type]["learned_patterns"]:
                        self.attack_patterns[attack_type]["learned_patterns"].append(cmd)
    
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
    
    def continuous_monitoring(self):
        """Main monitoring loop"""
        self.log("QENEX AI Security Training System started", "INFO")
        
        while True:
            try:
                # Collect system data
                data = self.collect_system_data()
                
                # Analyze for threats
                threats = self.analyze_threat(data)
                
                responses = []
                if threats:
                    self.log(f"Detected {len(threats)} threats", "WARNING")
                    
                    for threat in threats:
                        self.log(f"Threat: {threat['type']} (Confidence: {threat.get('confidence', 0)}%)", "CRITICAL")
                        
                        # Automated response for high confidence threats
                        if threat.get("confidence", 0) > 70:
                            response = self.respond_to_threat(threat)
                            responses.extend(response)
                    
                    # Generate report
                    report = self.generate_report(threats, responses)
                    self.log(f"Report generated: {json.dumps(report, indent=2)}")
                    
                    # Learn from this incident (would need human feedback in production)
                    self.learn_from_incident(data, True)
                
                # Save model periodically
                if datetime.now().minute % 10 == 0:
                    self.save_model()
                
                # Sleep before next check
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                self.log("Monitoring stopped by user")
                break
            except Exception as e:
                self.log(f"Error in monitoring: {str(e)}", "ERROR")
                time.sleep(60)

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