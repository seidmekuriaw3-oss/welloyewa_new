#!/bin/bash
# ============================
# WOLLOYEWA STORE BOT - DATABASE BACKUP SCRIPT
# ============================
# This script creates a backup of the PostgreSQL database

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/wolloyewa_backup_${TIMESTAMP}.sql.gz"
LOG_FILE="/var/log/wolloyewa/backup.log"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values if not set
DB_USER=${POSTGRES_USER:-postgres}
DB_PASSWORD=${POSTGRES_PASSWORD:-}
DB_NAME=${POSTGRES_DB:-welloyewadb}
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}
mkdir -p $(dirname ${LOG_FILE})

# Log function
log() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a ${LOG_FILE}
}

log "Starting database backup..." "${GREEN}"

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    log "pg_dump could not be found. Please install postgresql-client." "${RED}"
    exit 1
fi

# Create backup
log "Creating backup of database ${DB_NAME}..." "${YELLOW}"

if [ -z "${DB_PASSWORD}" ]; then
    # No password (trust authentication)
    PGPASSWORD=${DB_PASSWORD} pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -Fc | gzip > ${BACKUP_FILE}
else
    PGPASSWORD=${DB_PASSWORD} pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -Fc | gzip > ${BACKUP_FILE}
fi

# Check if backup was successful
if [ $? -eq 0 ] && [ -f ${BACKUP_FILE} ]; then
    BACKUP_SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
    log "Backup completed successfully: ${BACKUP_FILE} (${BACKUP_SIZE})" "${GREEN}"
    
    # Create a latest symlink
    ln -sf ${BACKUP_FILE} ${BACKUP_DIR}/latest_backup.sql.gz
    
    # Backup verification
    log "Verifying backup integrity..." "${YELLOW}"
    if gzip -t ${BACKUP_FILE} 2>/dev/null; then
        log "Backup integrity check passed." "${GREEN}"
    else
        log "Backup integrity check failed!" "${RED}"
        exit 1
    fi
else
    log "Backup failed!" "${RED}"
    exit 1
fi

# Clean up old backups
log "Cleaning up backups older than ${RETENTION_DAYS} days..." "${YELLOW}"
find ${BACKUP_DIR} -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
DELETED_COUNT=$(find ${BACKUP_DIR} -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -print | wc -l)
log "Deleted ${DELETED_COUNT} old backup files." "${GREEN}"

# Upload to cloud storage (optional)
if [ "${CLOUD_BACKUP_ENABLED}" = "true" ]; then
    log "Uploading backup to cloud storage..." "${YELLOW}"
    # Add your cloud upload command here
    # Example: aws s3 cp ${BACKUP_FILE} s3://${AWS_S3_BUCKET_NAME}/backups/
    log "Cloud upload skipped (not configured)." "${YELLOW}"
fi

# Send notification
if [ "${BACKUP_NOTIFICATIONS}" = "true" ]; then
    # Send Telegram notification
    if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ -n "${ADMIN_IDS}" ]; then
        MESSAGE="✅ Database backup completed successfully!
📁 File: ${BACKUP_FILE}
📦 Size: ${BACKUP_SIZE}
🕐 Time: $(date '+%Y-%m-%d %H:%M:%S')"
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ADMIN_IDS%%:*}" \
            -d "text=${MESSAGE}" \
            -d "parse_mode=Markdown" > /dev/null
    fi
fi

log "Backup process completed successfully!" "${GREEN}"

exit 0