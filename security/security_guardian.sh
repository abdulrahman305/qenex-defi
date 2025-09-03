#!/bin/bash
# QENEX AI Security Guardian System
# Comprehensive security monitoring and incident prevention

QENEX_LOG_DIR="/var/log/qenex"
QENEX_CONFIG_DIR="/etc/qenex/security"
QENEX_ALERT_FILE="$QENEX_LOG_DIR/security_alerts.log"

# Create necessary directories
mkdir -p "$QENEX_LOG_DIR" "$QENEX_CONFIG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== QENEX AI Security Guardian ===${NC}"
echo "Initializing comprehensive security system..."

# Function to log events
log_event() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$QENEX_LOG_DIR/security_guardian.log"
}

# Function to send alert
send_alert() {
    local severity=$1
    local message=$2
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$severity] $message" >> "$QENEX_ALERT_FILE"
    
    # For critical alerts, also log to system
    if [ "$severity" = "CRITICAL" ]; then
        logger -t "QENEX-SECURITY" -p auth.crit "$message"
    fi
}

# 1. Monitor outbound SSH connections
monitor_ssh_connections() {
    echo -e "${YELLOW}[QENEX] Monitoring SSH connections...${NC}"
    
    # Check for suspicious outbound SSH
    local ssh_count=$(ss -tunp | grep :22 | grep -v LISTEN | wc -l)
    
    if [ $ssh_count -gt 5 ]; then
        send_alert "WARNING" "High number of SSH connections detected: $ssh_count"
    fi
    
    # Check for connections to suspicious ranges
    if ss -tunp | grep -E "139\.99\.|203\.99\." > /dev/null 2>&1; then
        send_alert "CRITICAL" "Connection attempt to blacklisted IP range detected!"
        # Auto-block
        iptables -I OUTPUT -p tcp --dport 22 -d 139.99.0.0/16 -j DROP
        iptables -I OUTPUT -p tcp --dport 22 -d 203.99.0.0/16 -j DROP
    fi
    
    log_event "SSH connection check completed"
}

# 2. Monitor system processes
monitor_processes() {
    echo -e "${YELLOW}[QENEX] Scanning for suspicious processes...${NC}"
    
    # Check for known attack tools
    local suspicious_tools="hydra|masscan|nmap|nikto|sqlmap|metasploit"
    
    if ps aux | grep -E "$suspicious_tools" | grep -v grep > /dev/null 2>&1; then
        send_alert "CRITICAL" "Suspicious security tool detected in process list!"
        # Kill suspicious processes
        pkill -f "$suspicious_tools" 2>/dev/null
    fi
    
    # Check for unusual CPU usage
    local high_cpu=$(ps aux | awk '$3 > 80 {print $11}' | head -5)
    if [ ! -z "$high_cpu" ]; then
        send_alert "WARNING" "High CPU usage detected: $high_cpu"
    fi
    
    log_event "Process monitoring completed"
}

# 3. Check for unauthorized cron jobs
check_cron_jobs() {
    echo -e "${YELLOW}[QENEX] Auditing cron jobs...${NC}"
    
    # List all cron jobs
    echo "=== Current Cron Jobs ===" >> "$QENEX_LOG_DIR/cron_audit.log"
    crontab -l 2>/dev/null >> "$QENEX_LOG_DIR/cron_audit.log"
    
    # Check for suspicious patterns
    if crontab -l 2>/dev/null | grep -E "curl|wget|nc|/tmp/" > /dev/null; then
        send_alert "WARNING" "Potentially suspicious cron job detected!"
    fi
    
    log_event "Cron audit completed"
}

# 4. Monitor network connections
monitor_network() {
    echo -e "${YELLOW}[QENEX] Analyzing network connections...${NC}"
    
    # Count total connections
    local total_connections=$(ss -tun | wc -l)
    
    # Check for port scanning behavior
    local syn_sent=$(ss -tan | grep SYN-SENT | wc -l)
    if [ $syn_sent -gt 10 ]; then
        send_alert "CRITICAL" "Possible port scanning detected! SYN-SENT: $syn_sent"
    fi
    
    # Log connection summary
    echo "Total connections: $total_connections" >> "$QENEX_LOG_DIR/network_stats.log"
    echo "SYN-SENT: $syn_sent" >> "$QENEX_LOG_DIR/network_stats.log"
    
    log_event "Network monitoring completed"
}

# 5. File integrity monitoring
monitor_file_integrity() {
    echo -e "${YELLOW}[QENEX] Checking file integrity...${NC}"
    
    # Monitor critical directories
    local critical_dirs="/root/.ssh /etc/ssh /etc/cron.d /etc/cron.daily"
    
    for dir in $critical_dirs; do
        if [ -d "$dir" ]; then
            find "$dir" -type f -mmin -60 2>/dev/null | while read file; do
                send_alert "INFO" "Recent modification detected: $file"
            done
        fi
    done
    
    log_event "File integrity check completed"
}

# 6. Check system resources
check_resources() {
    echo -e "${YELLOW}[QENEX] Monitoring system resources...${NC}"
    
    # Check disk usage
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $disk_usage -gt 90 ]; then
        send_alert "WARNING" "High disk usage: ${disk_usage}%"
    fi
    
    # Check memory usage
    local mem_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    if [ $mem_usage -gt 90 ]; then
        send_alert "WARNING" "High memory usage: ${mem_usage}%"
    fi
    
    log_event "Resource check completed"
}

# 7. Security hardening checks
security_hardening() {
    echo -e "${YELLOW}[QENEX] Applying security hardening...${NC}"
    
    # Ensure firewall rules are in place
    if ! iptables -L OUTPUT -n | grep "139.99.0.0/16" > /dev/null 2>&1; then
        iptables -I OUTPUT -p tcp --dport 22 -d 139.99.0.0/16 -j DROP
        log_event "Reapplied firewall rule for 139.99.0.0/16"
    fi
    
    # Rate limiting for SSH
    iptables -N SSH_LIMIT 2>/dev/null
    iptables -A SSH_LIMIT -m recent --set --name SSH
    iptables -A SSH_LIMIT -m recent --update --seconds 60 --hitcount 5 --name SSH -j DROP
    
    log_event "Security hardening applied"
}

# 8. Generate security report
generate_report() {
    echo -e "${YELLOW}[QENEX] Generating security report...${NC}"
    
    local report_file="$QENEX_LOG_DIR/security_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
=====================================
QENEX AI Security Guardian Report
Generated: $(date)
Server: $(hostname -I | awk '{print $1}')
=====================================

1. SYSTEM STATUS
----------------
Uptime: $(uptime -p)
Load Average: $(uptime | awk -F'load average:' '{print $2}')
Disk Usage: $(df -h / | awk 'NR==2 {print $5}')
Memory Usage: $(free -h | grep Mem | awk '{print $3 "/" $2}')

2. NETWORK SECURITY
-------------------
Active Connections: $(ss -tun | wc -l)
Listening Ports: $(ss -tuln | grep LISTEN | wc -l)
Firewall Rules: $(iptables -L -n | grep -c DROP)

3. SSH SECURITY
---------------
SSH Connections: $(ss -tunp | grep :22 | grep -v LISTEN | wc -l)
Failed Login Attempts: $(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l)
Blocked IPs: $(iptables -L OUTPUT -n | grep DROP | wc -l)

4. PROCESS MONITORING
--------------------
Total Processes: $(ps aux | wc -l)
Root Processes: $(ps aux | grep ^root | wc -l)
High CPU Processes: $(ps aux | awk '$3 > 50' | wc -l)

5. RECENT ALERTS
----------------
$(tail -n 10 "$QENEX_ALERT_FILE" 2>/dev/null || echo "No recent alerts")

6. RECOMMENDATIONS
------------------
- Regularly review security logs
- Keep firewall rules updated
- Monitor outbound connections
- Implement intrusion detection
- Regular security audits

=====================================
EOF
    
    echo -e "${GREEN}Report saved to: $report_file${NC}"
    log_event "Security report generated"
}

# Main monitoring loop
main() {
    log_event "QENEX Security Guardian started"
    
    while true; do
        monitor_ssh_connections
        monitor_processes
        check_cron_jobs
        monitor_network
        monitor_file_integrity
        check_resources
        security_hardening
        
        # Generate report every hour
        if [ $(date +%M) -eq 0 ]; then
            generate_report
        fi
        
        # Sleep for 5 minutes
        sleep 300
    done
}

# Check if running as service or standalone
if [ "$1" = "report" ]; then
    generate_report
elif [ "$1" = "check" ]; then
    monitor_ssh_connections
    monitor_processes
    monitor_network
    echo -e "${GREEN}Quick security check completed${NC}"
elif [ "$1" = "start" ]; then
    main &
    echo $! > /var/run/qenex_security_guardian.pid
    echo -e "${GREEN}QENEX Security Guardian started (PID: $!)${NC}"
elif [ "$1" = "stop" ]; then
    if [ -f /var/run/qenex_security_guardian.pid ]; then
        kill $(cat /var/run/qenex_security_guardian.pid) 2>/dev/null
        rm /var/run/qenex_security_guardian.pid
        echo -e "${GREEN}QENEX Security Guardian stopped${NC}"
    fi
else
    echo "Usage: $0 {start|stop|check|report}"
    echo "  start  - Start security monitoring daemon"
    echo "  stop   - Stop security monitoring daemon"
    echo "  check  - Run quick security check"
    echo "  report - Generate security report"
fi