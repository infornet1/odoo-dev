#!/bin/bash
#
# Database Initialization Script for Odoo Development Environment
# Creates a fresh Odoo database with demo data
# Usage: ./scripts/init-database.sh [database_name]
#

set -e  # Exit on error

# Configuration
CONTAINER_NAME="odoo-dev-postgres"
ODOO_CONTAINER="odoo-dev-web"
POSTGRES_USER="odoo"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get database name from argument or use default
DATABASE_NAME=${1:-testing}

echo -e "${YELLOW}=== Odoo Database Initialization ===${NC}"
echo "Database name: $DATABASE_NAME"
echo ""

# Check if database already exists
DB_EXISTS=$(docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DATABASE_NAME'")

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${RED}WARNING: Database '$DATABASE_NAME' already exists!${NC}"
    read -p "Do you want to drop and recreate it? (yes/no): " -r
    echo
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${YELLOW}Stopping Odoo container...${NC}"
        docker stop "$ODOO_CONTAINER" 2>/dev/null || true

        echo -e "${YELLOW}Dropping existing database...${NC}"
        docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE $DATABASE_NAME;"
    else
        echo "Initialization cancelled."
        exit 0
    fi
fi

echo -e "${YELLOW}Creating new database...${NC}"
docker exec "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $DATABASE_NAME OWNER $POSTGRES_USER;"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database '$DATABASE_NAME' created successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Starting Odoo container...${NC}"
    docker start "$ODOO_CONTAINER"

    echo -e "${GREEN}✓ Odoo container started${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Access Odoo at: http://localhost:8019"
    echo "2. Create a new database using Odoo's web interface"
    echo "   - Database name: $DATABASE_NAME"
    echo "   - Email: admin@example.com"
    echo "   - Password: admin"
    echo "   - Language: Choose your language"
    echo "   - Load demonstration data: Choose based on your needs"
    echo ""
    echo "Or initialize via command line:"
    echo "docker exec $ODOO_CONTAINER odoo -d $DATABASE_NAME -i base --stop-after-init"
else
    echo -e "${RED}✗ Database creation failed!${NC}"
    exit 1
fi
