# Database Management Scripts

This directory contains scripts for managing the Odoo PostgreSQL database in the development environment.

## Overview

These scripts help you backup, restore, and manage your Odoo database. They work with the Docker containers defined in `docker-compose.yml`.

**Important**: These scripts manage the database **DATA** (backups/restores), while the database **STRUCTURE** is managed by Odoo modules in version control.

## Available Scripts

### 1. backup-database.sh
Creates a compressed backup of the entire database (structure + data).

**Usage:**
```bash
./scripts/backup-database.sh [database_name]
```

**Examples:**
```bash
# Backup the default 'testing' database
./scripts/backup-database.sh

# Backup a specific database
./scripts/backup-database.sh production
```

**Output:**
- Compressed backup file in `backups/` directory
- Format: `{database_name}_{timestamp}.sql.gz`
- Automatically keeps last 10 backups and deletes older ones

**When to use:**
- Before major changes or updates
- Before restoring from another backup
- Regular scheduled backups (recommended: daily)
- Before upgrading Odoo modules

---

### 2. restore-database.sh
Restores a database from a backup file.

**Usage:**
```bash
./scripts/restore-database.sh <backup_file> [target_database_name]
```

**Examples:**
```bash
# Restore to 'testing' database (default)
./scripts/restore-database.sh backups/testing_20251109_120000.sql.gz

# Restore to a different database name
./scripts/restore-database.sh backups/testing_20251109_120000.sql.gz testing_copy
```

**Warning:** This will DROP and recreate the target database. All existing data will be lost!

**When to use:**
- Recovering from data corruption
- Rolling back after failed changes
- Creating a copy of production data for testing
- Setting up a new development environment

---

### 3. export-schema.sh
Exports the database schema (structure only, no data) for version control.

**Usage:**
```bash
./scripts/export-schema.sh [database_name]
```

**Examples:**
```bash
# Export schema from 'testing' database
./scripts/export-schema.sh

# Export schema from a specific database
./scripts/export-schema.sh production
```

**Output:**
- Schema file in `schema/` directory
- Format: `{database_name}_schema.sql` (for git tracking)
- Timestamped copy: `{database_name}_schema_{timestamp}.sql`

**When to use:**
- After creating/modifying Odoo modules that change DB structure
- Before major Odoo upgrades
- For documentation purposes
- When you want to review schema changes in git

---

### 4. init-database.sh
Creates a fresh, empty Odoo database.

**Usage:**
```bash
./scripts/init-database.sh [database_name]
```

**Examples:**
```bash
# Create new 'testing' database
./scripts/init-database.sh

# Create a new development database
./scripts/init-database.sh dev_db
```

**When to use:**
- Setting up a fresh development environment
- Creating a clean database for testing
- Starting a new project from scratch

---

## Directory Structure

```
odoo-dev/
├── scripts/              # Database management scripts (versioned in git)
│   ├── backup-database.sh
│   ├── restore-database.sh
│   ├── export-schema.sh
│   ├── init-database.sh
│   └── README.md
├── backups/              # Database backups (NOT in git - local only)
│   ├── testing_20251109_120000.sql.gz
│   └── testing_20251109_130000.sql.gz
└── schema/               # Schema exports (versioned in git)
    ├── testing_schema.sql
    └── testing_schema_20251109_120000.sql
```

## What's in Git vs What's Not

### ✅ Versioned in Git:
- All scripts in `scripts/`
- Schema exports in `schema/` directory
- This README file

### ❌ NOT in Git (listed in .gitignore):
- Actual database backups in `backups/` directory
- PostgreSQL data volumes
- Any files containing actual data

## Best Practices

### 1. Regular Backups
Create backups before:
- Installing/upgrading Odoo modules
- Making database schema changes
- Testing new features
- Updating Odoo version

**Recommended**: Set up a cron job for daily backups:
```bash
# Add to crontab: backup at 2 AM daily
0 2 * * * cd /opt/odoo-dev && ./scripts/backup-database.sh testing >> /var/log/odoo-backup.log 2>&1
```

### 2. Export Schema After Changes
After modifying Odoo modules that change the database structure:
```bash
./scripts/export-schema.sh
git add schema/
git commit -m "Update database schema after module changes"
```

### 3. Before Restoring
Always create a backup before restoring:
```bash
./scripts/backup-database.sh testing
./scripts/restore-database.sh backups/old_backup.sql.gz testing
```

### 4. Testing Migrations
Use a copy of the database for testing:
```bash
./scripts/backup-database.sh testing
./scripts/restore-database.sh backups/testing_latest.sql.gz testing_test
# Test on testing_test database
```

## Common Workflows

### Starting Fresh
```bash
# Create new database
./scripts/init-database.sh my_new_db

# Initialize Odoo via web interface at http://localhost:8019
```

### Daily Development
```bash
# Morning: ensure you have a backup
./scripts/backup-database.sh

# Work on your code...

# Evening: if schema changed, export it
./scripts/export-schema.sh
git add schema/testing_schema.sql
git commit -m "Update schema after adding custom fields"
```

### Recovery from Mistake
```bash
# Restore from the most recent backup
./scripts/restore-database.sh backups/testing_20251109_120000.sql.gz
```

### Setting Up New Developer Environment
```bash
# Clone the repository
git clone https://github.com/infornet1/odoo-dev.git
cd odoo-dev

# Start Docker containers
docker-compose up -d

# Get a database backup from another developer or server
# Then restore it
./scripts/restore-database.sh backups/shared_backup.sql.gz testing
```

## Troubleshooting

### Script Permission Denied
```bash
chmod +x scripts/*.sh
```

### Container Not Running
```bash
docker-compose up -d
docker ps  # Verify containers are running
```

### Backup Too Large
Consider excluding certain tables or compressing more aggressively:
```bash
# Manual pg_dump with exclusions
docker exec odoo-dev-postgres pg_dump -U odoo -d testing \
  --exclude-table=ir_attachment \
  --exclude-table=ir_logging | gzip > backups/testing_minimal.sql.gz
```

### Restore Taking Too Long
For large databases, optimize PostgreSQL settings temporarily:
```bash
# Edit postgresql.conf in container or use connection parameters
# Increase maintenance_work_mem, disable fsync temporarily (dev only!)
```

## Docker Container Details

- **PostgreSQL Container**: `odoo-dev-postgres`
- **Odoo Container**: `odoo-dev-web`
- **PostgreSQL Port**: 5433 (mapped from 5432)
- **PostgreSQL User**: odoo
- **PostgreSQL Password**: odoo8069

## Security Notes

- Backup files contain sensitive data - keep them secure
- Never commit backup files (.sql, .sql.gz) to git
- Backup files are automatically excluded via .gitignore
- For production, use encrypted backups and secure storage

## Additional Resources

- [Odoo Documentation](https://www.odoo.com/documentation/17.0/)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/14/backup.html)
- Project Documentation: `/opt/odoo-dev/documentation/`
