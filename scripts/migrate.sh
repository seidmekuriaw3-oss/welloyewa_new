#!/bin/bash
# ============================
# WOLLOYEWA STORE BOT - DATABASE MIGRATION SCRIPT
# ============================
# This script manages database migrations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log function
log() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  upgrade [revision]   Upgrade to latest revision (or specified revision)"
    echo "  downgrade [revision] Downgrade to previous revision (or specified revision)"
    echo "  create <message>     Create a new migration"
    echo "  current             Show current revision"
    echo "  history             Show migration history"
    echo "  heads               Show available heads"
    echo "  merge               Merge multiple heads"
    echo "  stamp <revision>    Stamp database with revision without running migrations"
    echo "  check               Check if migrations are up to date"
    echo "  help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 upgrade"
    echo "  $0 downgrade -1"
    echo "  $0 create 'add_user_table'"
    exit 0
}

# Check if alembic is available
check_alembic() {
    if ! command -v alembic &> /dev/null; then
        log "alembic could not be found. Please install alembic." "${RED}"
        exit 1
    fi
}

# Run migration command
run_migration() {
    local cmd="$1"
    shift
    log "Running: alembic ${cmd} $@" "${YELLOW}"
    
    if alembic ${cmd} "$@"; then
        log "Command completed successfully!" "${GREEN}"
    else
        log "Command failed!" "${RED}"
        exit 1
    fi
}

# Check if migrations are up to date
check_migrations() {
    log "Checking if migrations are up to date..." "${YELLOW}"
    
    CURRENT=$(alembic current 2>/dev/null | grep -v "Current" | head -1)
    HEAD=$(alembic heads 2>/dev/null | head -1)
    
    if [ -z "${CURRENT}" ]; then
        log "No migrations have been applied!" "${RED}"
        return 1
    fi
    
    if [ "${CURRENT}" = "${HEAD}" ]; then
        log "Migrations are up to date! (Current: ${CURRENT})" "${GREEN}"
        return 0
    else
        log "Migrations are not up to date! Current: ${CURRENT}, Head: ${HEAD}" "${RED}"
        return 1
    fi
}

# Parse command
COMMAND=$1
shift || true

check_alembic

case ${COMMAND} in
    upgrade)
        REVISION=${1:-head}
        run_migration "upgrade" "${REVISION}"
        ;;
    downgrade)
        REVISION=${1:--1}
        run_migration "downgrade" "${REVISION}"
        ;;
    create)
        if [ -z "$1" ]; then
            log "Please provide a migration message" "${RED}"
            usage
        fi
        run_migration "revision" "--autogenerate" "-m" "$1"
        ;;
    current)
        run_migration "current"
        ;;
    history)
        run_migration "history"
        ;;
    heads)
        run_migration "heads"
        ;;
    merge)
        run_migration "merge" "$@"
        ;;
    stamp)
        if [ -z "$1" ]; then
            log "Please provide a revision" "${RED}"
            usage
        fi
        run_migration "stamp" "$1"
        ;;
    check)
        check_migrations
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