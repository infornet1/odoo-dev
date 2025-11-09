#!/bin/bash
#
# Database Backup Script for Odoo Development Environment
# Usage: ./scripts/backup-database.sh [database_name]
#

set -e  # Exit on error

# Configuration
CONTAINER_NAME="odoo-dev-postgres"
POSTGRES_USER="odoo"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get database name from argument or use default
DATABASE_NAME=${1:-testing}

echo -e "${YELLOW}=== Odoo Database Backup ===${NC}"
echo "Database: $DATABASE_NAME"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate backup filename
BACKUP_FILE="${BACKUP_DIR}/${DATABASE_NAME}_${TIMESTAMP}.sql"

echo -e "${YELLOW}Starting backup...${NC}"

# Perform the backup
docker exec -t "$CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -d "$DATABASE_NAME" > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    # Compress the backup
    echo -e "${YELLOW}Compressing backup...${NC}"
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"

    # Get file size
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

    echo -e "${GREEN}✓ Backup completed successfully!${NC}"
    echo "File: $BACKUP_FILE"
    echo "Size: $FILE_SIZE"
    echo ""

    # List recent backups
    echo -e "${YELLOW}Recent backups:${NC}"
    ls -lht "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -5 || echo "No previous backups found"

    # Cleanup old backups (keep last 10)
    echo ""
    echo -e "${YELLOW}Cleaning up old backups (keeping last 10)...${NC}"
    ls -t "$BACKUP_DIR"/${DATABASE_NAME}_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
    echo -e "${GREEN}✓ Cleanup completed${NC}"
else
    echo -e "${RED}✗ Backup failed!${NC}"
    exit 1
fi
