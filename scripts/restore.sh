#!/bin/bash
# ============================
# WOLLOYEWA STORE BOT - DATABASE RESTORE SCRIPT
# ============================
# This script restores a PostgreSQL database from a backup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="/backups/postgres"
LOG_FILE="/var/log/wolloyewa/restore.log"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
DB_USER=${POSTGRES_USER:-postgres}
DB_PASSWORD=${POSTGRES_PASSWORD:-}
DB_NAME=${POSTGRES_DB:-welloyewadb}
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}

# Log function
log() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a ${LOG_FILE}
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS] [BACKUP_FILE]"
    echo ""
    echo "Options:"
    echo "  -f, --file FILE     Backup file to restore"
    echo "  -l, --latest        Restore the latest backup"
    echo "  -d, --database DB   Target database name (default: ${DB_NAME})"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --latest"
    echo "  $0 --file /backups/postgres/wolloyewa_backup_20240101_120000.sql.gz"
    exit 0
}

# Parse arguments
LATEST=false
BACKUP_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            BACKUP_FILE="$2"
            shift 2
            ;;
        -l|--latest)
            LATEST=true
            shift
            ;;
        -d|--database)
            DB_NAME="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Create log directory
mkdir -p $(dirname ${LOG_FILE})

log "Starting database restore..." "${GREEN}"

# Check if pg_restore is available
if ! command -v pg_restore &> /dev/null; then
    log "pg_restore could not be found. Please install postgresql-client." "${RED}"
    exit 1
fi

# Determine backup file
if [ "${LATEST}" = true ]; then
    BACKUP_FILE="${BACKUP_DIR}/latest_backup.sql.gz"
    if [ ! -f "${BACKUP_FILE}" ]; then
        log "Latest backup symlink not found." "${RED}"
        exit 1
    fi
fi

if [ -z "${BACKUP_FILE}" ]; then
    log "No backup file specified. Use --latest or --file." "${RED}"
    usage
fi

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    log "Backup file not found: ${BACKUP_FILE}" "${RED}"
    exit 1
fi

log "Restoring from backup: ${BACKUP_FILE}" "${YELLOW}"

# Confirm restore
read -p "⚠️  This will overwrite the database '${DB_NAME}'. Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Restore cancelled." "${YELLOW}"
    exit 0
fi

# Drop existing connections
log "Terminating existing connections to database..." "${YELLOW}"
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();
" 2>/dev/null || true

# Drop and recreate database
log "Dropping and recreating database ${DB_NAME}..." "${YELLOW}"
PGPASSWORD=${DB_PASSWORD} dropdb -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} --if-exists ${DB_NAME}
PGPASSWORD=${DB_PASSWORD} createdb -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} ${DB_NAME}

# Restore from backup
log "Restoring data from backup..." "${YELLOW}"

if [[ "${BACKUP_FILE}" == *.gz ]]; then
    # Restore from compressed backup
    gunzip -c ${BACKUP_FILE} | PGPASSWORD=${DB_PASSWORD} pg_restore -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} --no-owner --no-privileges
else
    # Restore from uncompressed backup
    PGPASSWORD=${DB_PASSWORD} pg_restore -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} --no-owner --no-privileges ${BACKUP_FILE}
fi

# Check if restore was successful
if [ $? -eq 0 ]; then
    log "Database restore completed successfully!" "${GREEN}"
    
    # Run migrations after restore
    log "Running database migrations..." "${YELLOW}"
    if command -v alembic &> /dev/null; then
        alembic upgrade head
        log "Migrations completed." "${GREEN}"
    fi
    
    # Send notification
    if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ -n "${ADMIN_IDS}" ]; then
        MESSAGE="✅ Database restore completed successfully!
📁 File: ${BACKUP_FILE}
🕐 Time: $(date '+%Y-%m-%d %H:%M:%S')
🗄️ Database: ${DB_NAME}"
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ADMIN_IDS%%:*}" \
            -d "text=${MESSAGE}" \
            -d "parse_mode=Markdown" > /dev/null
    fi
else
    log "Database restore failed!" "${RED}"
    exit 1
fi

log "Restore process completed!" "${GREEN}"

exit 0