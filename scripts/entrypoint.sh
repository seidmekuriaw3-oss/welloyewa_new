#!/bin/bash
# ============================
# WOLLOYEWA STORE BOT - DOCKER ENTRYPOINT SCRIPT
# ============================
# This script runs when the Docker container starts

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

log "Starting Wolloyewa Store Bot..." "${GREEN}"

# Wait for database to be ready
wait_for_db() {
    log "Waiting for database to be ready..." "${YELLOW}"
    until PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d postgres -c "SELECT 1" > /dev/null 2>&1; do
        log "Database is unavailable - sleeping" "${YELLOW}"
        sleep 1
    done
    log "Database is ready!" "${GREEN}"
}

# Wait for Redis to be ready
wait_for_redis() {
    log "Waiting for Redis to be ready..." "${YELLOW}"
    until redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping > /dev/null 2>&1; do
        log "Redis is unavailable - sleeping" "${YELLOW}"
        sleep 1
    done
    log "Redis is ready!" "${GREEN}"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..." "${YELLOW}"
    if alembic upgrade head; then
        log "Migrations completed successfully!" "${GREEN}"
    else
        log "Migrations failed!" "${RED}"
        exit 1
    fi
}

# Seed database in development
seed_database() {
    if [ "${ENVIRONMENT}" = "development" ] && [ "${DEV_POPULATE_DUMMY_DATA}" = "True" ]; then
        log "Seeding database with dummy data..." "${YELLOW}"
        if python scripts/seed_db.py; then
            log "Database seeded successfully!" "${GREEN}"
        else
            log "Database seeding failed!" "${RED}"
        fi
    fi
}

# Start the appropriate service
start_service() {
    local service=${1:-app}
    
    case ${service} in
        app)
            log "Starting FastAPI application..." "${GREEN}"
            if [ "${ENVIRONMENT}" = "production" ]; then
                exec gunicorn main:app \
                    --workers ${GUNICORN_WORKERS:-4} \
                    --worker-class uvicorn.workers.UvicornWorker \
                    --bind 0.0.0.0:8000 \
                    --access-logfile - \
                    --error-logfile - \
                    --log-level info
            else
                exec uvicorn main:app \
                    --host 0.0.0.0 \
                    --port 8000 \
                    --reload \
                    --log-level debug
            fi
            ;;
        worker)
            log "Starting Celery worker..." "${GREEN}"
            exec celery -A infrastructure.workers.celery_app worker \
                --loglevel=${LOG_LEVEL:-info} \
                --concurrency=${CELERY_WORKER_CONCURRENCY:-4} \
                --queues=${CELERY_QUEUES:-default,high_priority,email,sms,payment,analytics,maintenance}
            ;;
        beat)
            log "Starting Celery beat scheduler..." "${GREEN}"
            exec celery -A infrastructure.workers.celery_app beat \
                --loglevel=${LOG_LEVEL:-info} \
                --pidfile=/tmp/celerybeat.pid \
                --schedule=/tmp/celerybeat-schedule
            ;;
        flower)
            log "Starting Flower monitoring..." "${GREEN}"
            exec celery -A infrastructure.workers.celery_app flower \
                --port=5555 \
                --url_prefix=flower \
                --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin}
            ;;
        *)
            log "Unknown service: ${service}" "${RED}"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    # Wait for dependencies
    wait_for_db
    wait_for_redis
    
    # Run migrations
    run_migrations
    
    # Seed database (development only)
    seed_database
    
    # Start the requested service
    start_service ${SERVICE:-app}
}

# Run main function
main

exit 0