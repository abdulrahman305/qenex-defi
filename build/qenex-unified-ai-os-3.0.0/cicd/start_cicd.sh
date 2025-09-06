#!/bin/bash
"""
QENEX CI/CD System Startup Script
Provides easy access to the CI/CD orchestrator through QENEX shell
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
CICD_DIR="/opt/qenex-os/cicd"
LOGS_DIR="${CICD_DIR}/logs"
PID_FILE="${CICD_DIR}/orchestrator.pid"
LOG_FILE="${LOGS_DIR}/orchestrator.log"

# Ensure directories exist
mkdir -p "${LOGS_DIR}"

print_status() {
    echo -e "${BLUE}[QENEX-CICD]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check required Python packages
    python3 -c "import fastapi, uvicorn, cryptography" 2>/dev/null || {
        print_warning "Some Python dependencies may be missing. Install with:"
        echo "pip install fastapi uvicorn cryptography pydantic redis lz4"
    }
    
    print_success "Dependencies check completed"
}

start_orchestrator() {
    if is_running; then
        print_warning "QENEX CI/CD Orchestrator is already running (PID: $(cat ${PID_FILE}))"
        return 0
    fi
    
    print_status "Starting QENEX CI/CD Orchestrator..."
    
    # Start orchestrator in background
    nohup python3 "${CICD_DIR}/cicd_orchestrator.py" start > "${LOG_FILE}" 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > "${PID_FILE}"
    
    # Wait a moment and check if it's still running
    sleep 3
    if kill -0 $pid 2>/dev/null; then
        print_success "QENEX CI/CD Orchestrator started successfully (PID: $pid)"
        print_status "Dashboard: http://localhost:8080"
        print_status "API: http://localhost:8000"
        print_status "Webhooks: http://localhost:9000"
        print_status "Logs: tail -f ${LOG_FILE}"
        return 0
    else
        print_error "Failed to start orchestrator. Check logs: ${LOG_FILE}"
        rm -f "${PID_FILE}"
        return 1
    fi
}

stop_orchestrator() {
    if ! is_running; then
        print_warning "QENEX CI/CD Orchestrator is not running"
        return 0
    fi
    
    local pid=$(cat "${PID_FILE}")
    print_status "Stopping QENEX CI/CD Orchestrator (PID: $pid)..."
    
    # Send TERM signal
    if kill -TERM $pid 2>/dev/null; then
        # Wait for graceful shutdown
        local count=0
        while kill -0 $pid 2>/dev/null && [ $count -lt 30 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if kill -0 $pid 2>/dev/null; then
            print_warning "Graceful shutdown failed, forcing termination..."
            kill -KILL $pid 2>/dev/null
        fi
        
        rm -f "${PID_FILE}"
        print_success "QENEX CI/CD Orchestrator stopped"
    else
        print_error "Failed to stop orchestrator (PID: $pid may not exist)"
        rm -f "${PID_FILE}"
        return 1
    fi
}

restart_orchestrator() {
    print_status "Restarting QENEX CI/CD Orchestrator..."
    stop_orchestrator
    sleep 2
    start_orchestrator
}

is_running() {
    if [ -f "${PID_FILE}" ]; then
        local pid=$(cat "${PID_FILE}")
        kill -0 $pid 2>/dev/null
        return $?
    fi
    return 1
}

show_status() {
    print_status "QENEX CI/CD System Status"
    echo "=================================="
    
    if is_running; then
        local pid=$(cat "${PID_FILE}")
        echo -e "Status: ${GREEN}RUNNING${NC} (PID: $pid)"
        
        # Show service endpoints
        echo ""
        echo "Service Endpoints:"
        echo "  Dashboard: http://localhost:8080"
        echo "  API Server: http://localhost:8000"
        echo "  Webhook Server: http://localhost:9000"
        
        # Show resource usage
        if command -v ps &> /dev/null; then
            local mem_usage=$(ps -p $pid -o rss= 2>/dev/null | awk '{print int($1/1024)"MB"}')
            echo "  Memory Usage: $mem_usage"
        fi
        
        # Check if services are responding
        echo ""
        echo "Service Health:"
        check_endpoint "Dashboard" "http://localhost:8080"
        check_endpoint "API Server" "http://localhost:8000/health"
        check_endpoint "Webhooks" "http://localhost:9000/health"
        
    else
        echo -e "Status: ${RED}STOPPED${NC}"
    fi
    
    echo ""
    echo "Log Files:"
    echo "  Main Log: ${LOG_FILE}"
    echo "  Logs Directory: ${LOGS_DIR}"
}

check_endpoint() {
    local name=$1
    local url=$2
    
    if command -v curl &> /dev/null; then
        if curl -s --max-time 3 "$url" > /dev/null 2>&1; then
            echo -e "  $name: ${GREEN}HEALTHY${NC}"
        else
            echo -e "  $name: ${RED}UNHEALTHY${NC}"
        fi
    else
        echo -e "  $name: ${YELLOW}UNKNOWN${NC} (curl not available)"
    fi
}

show_logs() {
    local lines=${1:-50}
    
    if [ -f "${LOG_FILE}" ]; then
        print_status "Showing last $lines lines of orchestrator logs:"
        echo "=================================="
        tail -n "$lines" "${LOG_FILE}"
    else
        print_warning "Log file not found: ${LOG_FILE}"
    fi
}

follow_logs() {
    if [ -f "${LOG_FILE}" ]; then
        print_status "Following orchestrator logs (Ctrl+C to stop):"
        echo "=================================="
        tail -f "${LOG_FILE}"
    else
        print_warning "Log file not found: ${LOG_FILE}"
    fi
}

create_config() {
    local config_file="${CICD_DIR}/orchestrator_config.json"
    
    if [ -f "$config_file" ]; then
        print_warning "Configuration file already exists: $config_file"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    print_status "Creating default configuration..."
    python3 "${CICD_DIR}/cicd_orchestrator.py" create-config "$config_file"
    print_success "Configuration created: $config_file"
}

validate_config() {
    local config_file="${CICD_DIR}/orchestrator_config.json"
    
    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        print_status "Create one with: $0 create-config"
        return 1
    fi
    
    print_status "Validating configuration..."
    python3 "${CICD_DIR}/cicd_orchestrator.py" validate-config "$config_file"
}

show_help() {
    echo "QENEX CI/CD System Control Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start           Start the CI/CD orchestrator"
    echo "  stop            Stop the CI/CD orchestrator"
    echo "  restart         Restart the CI/CD orchestrator"
    echo "  status          Show system status"
    echo "  logs [lines]    Show recent logs (default: 50 lines)"
    echo "  follow          Follow logs in real-time"
    echo "  create-config   Create default configuration file"
    echo "  validate-config Validate configuration file"
    echo "  check-deps      Check system dependencies"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start the orchestrator"
    echo "  $0 logs 100                # Show last 100 log lines"
    echo "  $0 status                  # Check system status"
    echo ""
    echo "Service URLs:"
    echo "  Dashboard: http://localhost:8080"
    echo "  API: http://localhost:8000/docs"
    echo "  Webhooks: http://localhost:9000"
}

# Main script logic
case "${1:-help}" in
    start)
        check_dependencies
        start_orchestrator
        ;;
    stop)
        stop_orchestrator
        ;;
    restart)
        restart_orchestrator
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-50}"
        ;;
    follow)
        follow_logs
        ;;
    create-config)
        create_config
        ;;
    validate-config)
        validate_config
        ;;
    check-deps)
        check_dependencies
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac