# Production Environment

## Configuration

**Config File:** `config/production.json` (gitignored - contains credentials)

```json
{
  "production": {
    "server": { "host": "10.124.0.3", "user": "root" },
    "database": { "name": "DB_UEIPAB", "user": "odoo" },
    "containers": { "odoo": "0ef7d03db702_ueipab17", "postgres": "ueipab17_postgres_1" }
  }
}
```

## SSH Connection

**Pattern:**
```bash
sshpass -p '$PASSWORD' ssh -o StrictHostKeyChecking=no root@10.124.0.3 \
  "docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c 'SQL_QUERY'"
```

### SSH Rate Limiting Fix (2025-12-12)
- **Problem:** Parallel SSH connections from dev server got "Connection refused"
- **Cause:** UFW had `ufw limit 22/tcp` rule (max 6 connections per 30s)
- **Solution:** Whitelisted dev server IP for unlimited SSH access
- **Rule Applied:** `ufw insert 1 allow from 10.124.0.2 to any port 22 comment 'Dev server SSH unlimited'`
- **Result:** Parallel SSH calls now work; external IPs still rate-limited

## Contract Status

- Production: 44 contracts (V2 structure assigned)
- Testing: 46 contracts

---

## Production Upgrade Procedure

**Last Sync:** 2026-02-28 - `ueipab_payroll_enhancements` 1.52.2 -> 1.53.0 (ack confirmation email with logo, audit trail, net amount, company info)

### Sync Method

```bash
# 1. Create tarball on dev server
cd /opt/odoo-dev/addons
tar -czvf /tmp/ueipab_payroll_enhancements.tar.gz ueipab_payroll_enhancements/

# 2. Copy to production server
scp /tmp/ueipab_payroll_enhancements.tar.gz root@10.124.0.3:/tmp/

# 3. Backup old module on production (host filesystem)
ssh root@10.124.0.3 "cd /home/vision/ueipab17/addons && \
  mv ueipab_payroll_enhancements ueipab_payroll_enhancements.backup_20251216"

# 4. Extract new module
ssh root@10.124.0.3 "cd /home/vision/ueipab17/addons && \
  tar -xzvf /tmp/ueipab_payroll_enhancements.tar.gz"

# 5. Restart Odoo and upgrade
ssh root@10.124.0.3 "docker restart ueipab17"
# Then: Apps -> ueipab_payroll_enhancements -> Upgrade
```

**Production Module Path:** `/home/vision/ueipab17/addons` (mounted as `/mnt/extra-addons` in container)

### Future Upgrade Steps

```bash
# 1. Backup production database
sshpass -p '$PASSWORD' ssh root@10.124.0.3 \
  "docker exec ueipab17_postgres_1 pg_dump -U odoo DB_UEIPAB > /backup/DB_UEIPAB_$(date +%Y%m%d).sql"

# 2. Copy module files (from dev server)
scp -r addons/ueipab_payroll_enhancements root@10.124.0.3:/home/vision/ueipab17/addons/

# 3. Restart Odoo
sshpass -p '$PASSWORD' ssh root@10.124.0.3 "docker restart ueipab17"

# 4. Upgrade module via UI or shell
# Apps -> ueipab_payroll_enhancements -> Upgrade
```

### Optional - HRMS Dashboard Installation

```bash
# Copy both modules
scp -r addons/hrms_dashboard root@10.124.0.3:/path/to/extra-addons/
scp -r addons/ueipab_hrms_dashboard_ack root@10.124.0.3:/path/to/extra-addons/

# Install via Apps menu (hrms_dashboard first, then ueipab_hrms_dashboard_ack)
```

---

## Quick Commands

```bash
# Run script in testing
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/[script-name].py

# Restart Odoo
docker restart odoo-dev-web

# Clear cache
Ctrl+Shift+R (browser hard reload)
```

---

## Environment Sync

**VEB Exchange Rate Sync:** `scripts/sync-veb-rates-from-production.sql`
- Source: `ueipab17_postgres_1` @ 10.124.0.3
- Production: 636 rates (2024-01-30 to 2025-11-27)
- Currency ID: 2 (VEB)
