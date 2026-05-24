#!/bin/bash
# ============================
# WOLLOYEWA STORE BOT - DOCUMENTATION GENERATOR
# ============================
# This script generates project documentation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOCS_DIR="docs"
BUILD_DIR="site"
API_DOCS_DIR="${DOCS_DIR}/api"
EXAMPLES_DIR="${DOCS_DIR}/examples"

# Log function
log() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build       Build documentation"
    echo "  serve       Serve documentation locally"
    echo "  deploy      Deploy documentation to GitHub Pages"
    echo "  clean       Clean build directory"
    echo "  api         Generate API documentation from code"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 serve"
    echo "  $0 deploy"
    exit 0
}

# Check if mkdocs is available
check_mkdocs() {
    if ! command -v mkdocs &> /dev/null; then
        log "mkdocs could not be found. Installing..." "${YELLOW}"
        pip install mkdocs mkdocs-material mkdocstrings
    fi
}

# Clean build directory
clean_docs() {
    log "Cleaning build directory..." "${YELLOW}"
    if [ -d "${BUILD_DIR}" ]; then
        rm -rf ${BUILD_DIR}
        log "Build directory cleaned." "${GREEN}"
    else
        log "Build directory does not exist." "${YELLOW}"
    fi
}

# Generate API documentation
generate_api_docs() {
    log "Generating API documentation from code..." "${YELLOW}"
    
    # Create API docs directory
    mkdir -p ${API_DOCS_DIR}
    
    # Generate documentation using pydoc or sphinx
    if command -v pydoc &> /dev/null; then
        # Generate module documentation
        for module in core apps infrastructure bot; do
            if [ -d "${module}" ]; then
                pydoc -w ${module} 2>/dev/null || true
                log "Generated docs for ${module}" "${GREEN}"
            fi
        done
        
        # Move generated HTML files
        mv *.html ${API_DOCS_DIR}/ 2>/dev/null || true
    fi
    
    log "API documentation generated in ${API_DOCS_DIR}" "${GREEN}"
}

# Build documentation
build_docs() {
    log "Building documentation..." "${YELLOW}"
    
    # Generate API docs first
    generate_api_docs
    
    # Build with mkdocs
    if [ -f "mkdocs.yml" ]; then
        mkdocs build --clean
        log "Documentation built in ${BUILD_DIR}" "${GREEN}"
    else
        log "mkdocs.yml not found. Creating default configuration..." "${YELLOW}"
        
        cat > mkdocs.yml << EOF
site_name: Wolloyewa Store Bot Documentation
site_description: Ethiopian E-commerce Telegram Bot Documentation
site_author: Wolloyewa Team
copyright: Copyright © 2024 Wolloyewa Technologies PLC

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.highlight
    - search.share

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - API Reference: api/
  - Deployment: deployment.md
  - Contributing: contributing.md

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  - toc:
      permalink: true
EOF
        
        # Create placeholder docs
        mkdir -p ${DOCS_DIR}
        cat > ${DOCS_DIR}/index.md << EOF
# Welcome to Wolloyewa Store Bot

Wolloyewa Store Bot is an Ethiopian e-commerce Telegram bot with multi-vendor support.

## Features

- 🛍️ Product catalog and search
- 💳 Multiple payment methods (Chapa, Telebirr, CBE Birr)
- 📦 Order tracking
- 🏪 Vendor management
- 📊 Analytics dashboard

## Quick Start

Check out the [Getting Started](getting-started.md) guide.
EOF
        
        cat > ${DOCS_DIR}/getting-started.md << EOF
# Getting Started

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

## Installation

\`\`\`bash
git clone https://github.com/wolloyewa/store-bot.git
cd store-bot
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_db.py
uvicorn main:app --reload
\`\`\`

## Configuration

Edit the \`.env\` file with your settings.
EOF
        
        mkdocs build --clean
        log "Default documentation built in ${BUILD_DIR}" "${GREEN}"
    fi
}

# Serve documentation locally
serve_docs() {
    log "Serving documentation at http://localhost:8000" "${GREEN}"
    
    if [ -f "mkdocs.yml" ]; then
        mkdocs serve --dev-addr=0.0.0.0:8000
    else
        log "mkdocs.yml not found. Please run 'build' first." "${RED}"
        exit 1
    fi
}

# Deploy to GitHub Pages
deploy_docs() {
    log "Deploying documentation to GitHub Pages..." "${YELLOW}"
    
    if [ -f "mkdocs.yml" ]; then
        mkdocs gh-deploy --force
        log "Documentation deployed successfully!" "${GREEN}"
    else
        log "mkdocs.yml not found. Please run 'build' first." "${RED}"
        exit 1
    fi
}

# Parse command
COMMAND=$1

case ${COMMAND} in
    build)
        check_mkdocs
        build_docs
        ;;
    serve)
        check_mkdocs
        serve_docs
        ;;
    deploy)
        check_mkdocs
        build_docs
        deploy_docs
        ;;
    clean)
        clean_docs
        ;;
    api)
        generate_api_docs
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        if [ -z "${COMMAND}" ]; then
            usage
        else
            log "Unknown command: ${COMMAND}" "${RED}"
            usage
        fi
        ;;
esac

exit 0