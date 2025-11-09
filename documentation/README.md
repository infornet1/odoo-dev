# Development Environment Setup - UEIPAB Odoo 17

## Environment Details
- **URL**: http://dev.ueipab.edu.ve:8019
- **Database**: testing (complete replica from production testing)
- **Date Synced**: November 9, 2025
- **Odoo Version**: 17.0
- **PostgreSQL**: 14

## Docker Configuration
- **Location**: `/opt/odoo-dev/`
- **Web Container**: `odoo-dev-web`
- **DB Container**: `odoo-dev-postgres`
- **Ports**: 
  - Web: 8019 (Odoo)
  - Longpolling: 8020
  - PostgreSQL: 5433

## Directory Structure
```
/opt/odoo-dev/
├── docker-compose.yml
├── config/
│   └── odoo.conf
└── addons/
    ├── 3DVision-C-A/        # Main custom addons
    ├── hr_payroll_community/
    ├── dual_currency/
    └── ... (19 total custom addons)
```

## Key Custom Modules Installed
- `impresion_forma_libre` - Invoice printing system
- `dual_currency` - Dual currency support (USD/VES)
- `tdv_invoice_template` - Custom invoice templates
- `hr_payroll_community` - Payroll management
- `custom_print_payslip` - Custom payslip reports

## Important Fixes Applied
1. **Invoice Print RPC Error** - Fixed `_get_rate()` method compatibility
2. **Production Template Sync** - Restored templates to git standard
3. **Payslip Print Button** - Database visibility fix applied

## Docker Commands
```bash
# View containers
docker ps | grep odoo-dev

# Restart services
cd /opt/odoo-dev && docker-compose restart

# View logs
docker logs odoo-dev-web --tail 50
docker logs odoo-dev-postgres --tail 50

# Access containers
docker exec -it odoo-dev-web bash
docker exec -it odoo-dev-postgres psql -U odoo

# Database operations
docker exec odoo-dev-postgres psql -U odoo -d testing
```

## Development Workflow
1. Edit code in `/opt/odoo-dev/addons/`
2. Restart container: `docker restart odoo-dev-web`
3. Update modules in Odoo UI: Apps → Update Apps List
4. Test changes at http://dev.ueipab.edu.ve:8019

## Database Backup/Restore
```bash
# Backup
docker exec odoo-dev-postgres pg_dump -U odoo testing > backup.sql

# Restore
docker exec -i odoo-dev-postgres psql -U odoo testing < backup.sql
```

## Credentials
- **Database**: testing
- **Admin User**: admin
- **Password**: [Same as testing environment]

## Notes
- All modules from testing are pre-installed
- Filestore is fully synchronized (234MB)
- Database contains all testing data (57MB)
- Configuration matches testing environment exactly

## Next Steps - Venezuelan Payslip Reports
Create three custom reports for `hr.payslip`:
1. Bi-weekly payment receipt
2. Vacation/utilities liquidation
3. Social benefits seniority report

Use `impresion_forma_libre` invoice print implementation as reference.

## Support Documentation
See `/opt/odoo-dev/documentation/` for:
- CRITICAL_DISCOVERY_REPORT.md
- INVOICE_PRINT_FIXED.md
- PAYSLIP_PRINT_BUTTON_FIXED.md
- testing_database_backup.sql
