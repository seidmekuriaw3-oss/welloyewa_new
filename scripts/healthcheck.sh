#!/bin/bash
# ============================
# WOLLOYEWA STORE BOT - HEALTH CHECK SCRIPT
# ============================
# This script performs health checks for the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
HEALTH_ENDPOINT="${API_URL}/health"
TIMEOUT=10
LOG_FILE="/var/log/wolloyewa/healthcheck.log"

# Log function
log() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a ${LOG_FILE}
}

# Check API health
check_api() {
    log "Checking API health at ${HEALTH_ENDPOINT}..." "${YELLOW}"
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time ${TIMEOUT} ${HEALTH_ENDPOINT})
    
    if [ ${HTTP_CODE} -eq 200 ]; then
        log "API health check passed (HTTP ${HTTP_CODE})" "${GREEN}"
        return 0
    else
        log "API health check failed (HTTP ${HTTP_CODE})" "${RED}"
        return 1
    fi
}

# Check database connectivity
check_database() {
    log "Checking database connectivity..." "${YELLOW}"
    
    if PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT 1" > /dev/null 2>&1; then
        log "Database connectivity check passed" "${GREEN}"
        return 0
    else
        log "Database connectivity check failed" "${RED}"
        return 1
    fi
}

# Check Redis connectivity
check_redis() {
    log "Checking Redis connectivity..." "${YELLOW}"
    
    if redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping > /dev/null 2>&1; then
        log "Redis connectivity check passed" "${GREEN}"
        return 0
    else
        log "Redis connectivity check failed" "${RED}"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    log "Checking disk space..." "${YELLOW}"
    
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    THRESHOLD=90
    
    if [ ${DISK_USAGE} -lt ${THRESHOLD} ]; then
        log "Disk space check passed (${DISK_USAGE}% used)" "${GREEN}"
        return 0
    else
        log "Disk space check failed (${DISK_USAGE}% used, threshold: ${THRESHOLD}%)" "${RED}"
        return 1
    fi
}

# Check memory usage
check_memory() {
    log "Checking memory usage..." "${YELLOW}"
    
    if command -v free &> /dev/null; then
        MEMORY_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
        THRESHOLD=90
        
        if [ ${MEMORY_USAGE} -lt ${THRESHOLD} ]; then
            log "Memory usage check passed (${MEMORY_USAGE}% used)" "${GREEN}"
            return 0
        else
            log "Memory usage check failed (${MEMORY_USAGE}% used, threshold: ${THRESHOLD}%)" "${RED}"
            return 1
        fi
    else
        log "Memory check skipped (free command not available)" "${YELLOW}"
        return 0
    fi
}

# Check Celery worker
check_celery() {
    if [ -n "${CELERY_WORKER_ENABLED}" ] && [ "${CELERY_WORKER_ENABLED}" = "true" ]; then
        log "Checking Celery worker status..." "${YELLOW}"
        
        if celery -A infrastructure.workers.celery_app inspect ping > /dev/null 2>&1; then
            log "Celery worker check passed" "${GREEN}"
            return 0
        else
            log "Celery worker check failed" "${RED}"
            return 1
        fi
    else
        log "Celery worker check skipped (not enabled)" "${YELLOW}"
        return 0
    fi
}

# Main execution
main() {
    FAILED=0
    
    log "Starting health checks..." "${GREEN}"
    
    # Run all checks
    check_api || FAILED=$((FAILED+1))
    check_database || FAILED=$((FAILED+1))
    check_redis || FAILED=$((FAILED+1))
    check_disk_space || FAILED=$((FAILED+1))
    check_memory || FAILED=$((FAILED+1))
    check_celery || FAILED=$((FAILED+1))
    
    # Summary
    if [ ${FAILED} -eq 0 ]; then
        log "All health checks passed!" "${GREEN}"
        exit 0
    else
        log "${FAILED} health check(s) failed!" "${RED}"
        exit 1
    fi
}

# Run main function
main

exit $?