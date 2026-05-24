#!/bin/bash
# ============================
# WOLLOYEWA STORE BOT - SYSTEM MONITOR SCRIPT
# ============================
# This script monitors system resources and application health

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOG_FILE="/var/log/wolloyewa/monitor.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=80
ALERT_THRESHOLD_DISK=85
CHECK_INTERVAL=60

# Log function
log() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a ${LOG_FILE}
}

# Send alert
send_alert() {
    local message="$1"
    
    log "ALERT: ${message}" "${RED}"
    
    # Send Telegram alert if configured
    if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ -n "${ADMIN_IDS}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ADMIN_IDS%%:*}" \
            -d "text=🚨 *System Alert* 🚨%0A%0A${message}" \
            -d "parse_mode=Markdown" > /dev/null
    fi
}

# Check CPU usage
check_cpu() {
    if command -v mpstat &> /dev/null; then
        CPU_USAGE=$(mpstat 1 1 | awk 'END {print 100 - $NF}')
    else
        CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    fi
    CPU_USAGE=${CPU_USAGE%.*}
    
    if [ ${CPU_USAGE} -gt ${ALERT_THRESHOLD_CPU} ]; then
        send_alert "High CPU usage: ${CPU_USAGE}% (threshold: ${ALERT_THRESHOLD_CPU}%)"
        return 1
    else
        log "CPU usage: ${CPU_USAGE}%" "${GREEN}"
        return 0
    fi
}

# Check Memory usage
check_memory() {
    if command -v free &> /dev/null; then
        TOTAL_MEM=$(free -m | awk 'NR==2 {print $2}')
        USED_MEM=$(free -m | awk 'NR==2 {print $3}')
        MEMORY_USAGE=$((USED_MEM * 100 / TOTAL_MEM))
        
        if [ ${MEMORY_USAGE} -gt ${ALERT_THRESHOLD_MEMORY} ]; then
            send_alert "High memory usage: ${MEMORY_USAGE}% (${USED_MEM}MB / ${TOTAL_MEM}MB)"
            return 1
        else
            log "Memory usage: ${MEMORY_USAGE}% (${USED_MEM}MB / ${TOTAL_MEM}MB)" "${GREEN}"
            return 0
        fi
    else
        log "Memory check skipped (free command not available)" "${YELLOW}"
        return 0
    fi
}

# Check Disk usage
check_disk() {
    if command -v df &> /dev/null; then
        DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
        
        if [ ${DISK_USAGE} -gt ${ALERT_THRESHOLD_DISK} ]; then
            send_alert "High disk usage: ${DISK_USAGE}% (threshold: ${ALERT_THRESHOLD_DISK}%)"
            return 1
        else
            log "Disk usage: ${DISK_USAGE}%" "${GREEN}"
            return 0
        fi
    else
        log "Disk check skipped (df command not available)" "${YELLOW}"
        return 0
    fi
}

# Check application health
check_app_health() {
    local health_url=${1:-"http://localhost:8000/health"}
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 ${health_url} 2>/dev/null || echo "000")
    
    if [ ${HTTP_CODE} -eq 200 ]; then
        log "Application health: OK (HTTP ${HTTP_CODE})" "${GREEN}"
        return 0
    else
        send_alert "Application health check failed! (HTTP ${HTTP_CODE})"
        return 1
    fi
}

# Check database connectivity
check_database() {
    if PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT 1" > /dev/null 2>&1; then
        log "Database: Connected" "${GREEN}"
        return 0
    else
        send_alert "Database connection failed!"
        return 1
    fi
}

# Check Redis connectivity
check_redis() {
    if redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping > /dev/null 2>&1; then
        log "Redis: Connected" "${GREEN}"
        return 0
    else
        send_alert "Redis connection failed!"
        return 1
    fi
}

# Check active connections
check_connections() {
    if command -v netstat &> /dev/null; then
        CONNECTIONS=$(netstat -an | grep -c "ESTABLISHED")
        log "Active connections: ${CONNECTIONS}" "${BLUE}"
    fi
}

# Check process status
check_processes() {
    # Check Python processes
    PYTHON_COUNT=$(pgrep -c python3 2>/dev/null || echo "0")
    log "Python processes: ${PYTHON_COUNT}" "${BLUE}"
    
    # Check Postgres
    if pgrep -x "postgres" > /dev/null; then
        log "PostgreSQL: Running" "${GREEN}"
    else
        log "PostgreSQL: Not running" "${RED}"
    fi
    
    # Check Redis
    if pgrep -x "redis-server" > /dev/null; then
        log "Redis: Running" "${GREEN}"
    else
        log "Redis: Not running" "${RED}"
    fi
}

# Show system summary
show_summary() {
    log "=== System Summary ===" "${BLUE}"
    check_cpu
    check_memory
    check_disk
    check_connections
    echo ""
}

# Main monitoring loop
monitor_loop() {
    local interval=${1:-${CHECK_INTERVAL}}
    
    log "Starting system monitor (interval: ${interval}s)" "${GREEN}"
    
    while true; do
        clear
        echo "=== Wolloyewa Store Bot Monitor ==="
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        
        show_summary
        check_app_health
        check_database
        check_redis
        check_processes
        
        echo ""
        echo "Next check in ${interval} seconds... (Press Ctrl+C to exit)"
        sleep ${interval}
    done
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  once        Run a single health check"
    echo "  watch       Continuously monitor (default)"
    echo "  summary     Show system summary only"
    echo "  help        Show this help message"
    echo ""
    echo "Options:"
    echo "  --interval N Set check interval in seconds (default: 60)"
    echo ""
    echo "Examples:"
    echo "  $0 once"
    echo "  $0 watch --interval 30"
    exit 0
}

# Parse command
COMMAND=${1:-watch}
shift || true

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

case ${COMMAND} in
    once)
        show_summary
        check_app_health
        check_database
        check_redis
        ;;
    watch)
        monitor_loop ${CHECK_INTERVAL}
        ;;
    summary)
        show_summary
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        log "Unknown command: ${COMMAND}" "${RED}"
        usage
        ;;
esac

exit 0