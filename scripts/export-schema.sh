#!/bin/bash
#
# Schema Export Script for Odoo Development Environment
# Exports database schema (structure only, no data) for version control
# Usage: ./scripts/export-schema.sh [database_name]
#

set -e  # Exit on error

# Configuration
CONTAINER_NAME="odoo-dev-postgres"
POSTGRES_USER="odoo"
SCHEMA_DIR="./schema"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get database name from argument or use default
DATABASE_NAME=${1:-testing}

echo -e "${YELLOW}=== Odoo Database Schema Export ===${NC}"
echo "Database: $DATABASE_NAME"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create schema directory if it doesn't exist
mkdir -p "$SCHEMA_DIR"

# Generate schema filename
SCHEMA_FILE="${SCHEMA_DIR}/${DATABASE_NAME}_schema.sql"
TIMESTAMPED_FILE="${SCHEMA_DIR}/${DATABASE_NAME}_schema_${TIMESTAMP}.sql"

echo -e "${YELLOW}Exporting schema (structure only)...${NC}"

# Export schema only (no data)
docker exec -t "$CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -d "$DATABASE_NAME" --schema-only --no-owner --no-acl > "$TIMESTAMPED_FILE"

if [ $? -eq 0 ]; then
    # Create/update the main schema file (for git tracking)
    cp "$TIMESTAMPED_FILE" "$SCHEMA_FILE"

    FILE_SIZE=$(du -h "$SCHEMA_FILE" | cut -f1)

    echo -e "${GREEN}✓ Schema exported successfully!${NC}"
    echo "Main file: $SCHEMA_FILE (tracked in git)"
    echo "Timestamped: $TIMESTAMPED_FILE"
    echo "Size: $FILE_SIZE"
    echo ""

    # Show table count
    TABLE_COUNT=$(grep -c "CREATE TABLE" "$SCHEMA_FILE" || echo "0")
    echo "Tables found: $TABLE_COUNT"

    # Cleanup old timestamped schema files (keep last 5)
    echo ""
    echo -e "${YELLOW}Cleaning up old schema exports (keeping last 5)...${NC}"
    ls -t "$SCHEMA_DIR"/${DATABASE_NAME}_schema_*.sql 2>/dev/null | tail -n +6 | xargs -r rm -f
    echo -e "${GREEN}✓ Cleanup completed${NC}"
    echo ""
    echo -e "${YELLOW}Note: The file '$SCHEMA_FILE' should be committed to git${NC}"
else
    echo -e "${RED}✗ Schema export failed!${NC}"
    exit 1
fi
