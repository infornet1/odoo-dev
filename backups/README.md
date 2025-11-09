# Database Backups Directory

This directory contains database backup files created by `scripts/backup-database.sh`.

**Important**: This directory is excluded from git version control (see `.gitignore`).

## Backup Files

Backup files are named: `{database_name}_{timestamp}.sql.gz`

Example:
- `testing_20251109_143000.sql.gz`
- `production_20251108_020000.sql.gz`

## Retention Policy

The backup script automatically:
- Keeps the last 10 backups
- Deletes older backups to save disk space

## Manual Backup Management

To list all backups:
```bash
ls -lht backups/
```

To delete old backups manually:
```bash
rm backups/testing_20251101_*.sql.gz
```

## Restoring from Backup

Use the restore script:
```bash
./scripts/restore-database.sh backups/testing_20251109_143000.sql.gz
```

See `scripts/README.md` for more details.

## Security

- Backup files contain sensitive data
- Keep this directory secure
- Never commit backups to git
- For production backups, consider:
  - Encrypted backups
  - Off-site storage
  - Regular backup testing
