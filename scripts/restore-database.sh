#!/bin/bash
#
# Database Restore Script for Odoo Development Environment
# Usage: ./scripts/restore-database.sh <backup_file> [target_database_name]
#

set -e  # Exit on error

# Configuration
CONTAINER_NAME="odoo-dev-postgres"
POSTGRES_USER="odoo"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Backup file not specified${NC}"
    echo "Usage: $0 <backup_file> [target_database_name]"
    echo ""
    echo "Available backups:"
    ls -lht ./backups/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB=${2:-testing}

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}=== Odoo Database Restore ===${NC}"
echo "Backup file: $BACKUP_FILE"
echo "Target database: $TARGET_DB"
echo ""

# Warning prompt
echo -e "${RED}WARNING: This will DROP and recreate the database '$TARGET_DB'${NC}"
echo -e "${RED}All existing data in '$TARGET_DB' will be LOST!${NC}"
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo -e "${YELLOW}Stopping Odoo container (if running)...${NC}"
docker stop odoo-dev-web 2>/dev/null || true

echo -e "${YELLOW}Dropping existing database...${NC}"
docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $TARGET_DB;"

echo -e "${YELLOW}Creating fresh database...${NC}"
docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $TARGET_DB OWNER $POSTGRES_USER;"

echo -e "${YELLOW}Restoring database from backup...${NC}"

# Check if file is compressed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "Decompressing and restoring..."
    gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$TARGET_DB"
else
    echo "Restoring uncompressed backup..."
    cat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$TARGET_DB"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Starting Odoo container...${NC}"
    docker start odoo-dev-web
    echo -e "${GREEN}✓ Odoo container started${NC}"
    echo ""
    echo "Database '$TARGET_DB' has been restored from: $BACKUP_FILE"
else
    echo -e "${RED}✗ Restore failed!${NC}"
    docker start odoo-dev-web 2>/dev/null || true
    exit 1
fi
