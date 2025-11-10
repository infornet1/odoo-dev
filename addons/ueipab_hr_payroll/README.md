# UEIPAB HR Payroll Customizations

**Version:** 17.0.2.0.0
**Category:** Human Resources/Payroll
**License:** AGPL-3

## Overview

Complete Venezuelan payroll customization module for UEIPAB, consolidating contract field extensions and payroll processing enhancements into a single, maintainable module.

## Features

### Contract Field Extensions

#### Venezuelan Compensation Structure (70/25/5)
- **Salary Base (70%):** Primary salary component
- **Regular Bonus (25%):** Benefits and regular bonuses
- **Extra Bonus (5%):** Performance-based bonus

#### Venezuelan Benefits
- **Cesta Ticket:** Monthly food allowance (USD)
- **Wage VES:** Salary tracking in Venezuelan Bolivars

#### Payroll Schedule
- **Bi-monthly Payroll:** 15th and last day of each month
- Configurable payment days per contract

#### Prestaciones Sociales
- Social benefits tracking
- Reset date management
- Payment history

#### Aguinaldos (Christmas Bonus)
- Monthly salary tracking from master spreadsheet
- Complete audit trail with exchange rates
- Independent from regular payroll distribution
- Synced from Google Sheets

### Payroll Processing Enhancements

#### Batch Structure Selector
- Override payroll structure for entire batch
- Smart defaults based on batch name patterns
- Manual override capability

#### Smart Detection
- Auto-detects "Aguinaldos" in batch names
- Pre-selects AGUINALDOS_2025 structure
- Supports any custom structure

#### Supported Use Cases
- Regular bi-monthly payroll
- Aguinaldos (Christmas bonuses)
- Special bonuses
- Employee liquidations
- Custom payroll scenarios

## Installation

```bash
# Install via Odoo CLI
docker exec odoo-dev-web odoo -c /etc/odoo/odoo.conf -d database_name -i ueipab_hr_payroll --stop-after-init

# Or install via Odoo UI
Apps → Update Apps List → Search "UEIPAB HR Payroll" → Install
```

## Migration from Previous Modules

This module replaces three separate modules:
- `ueipab_hr_contract` (v17.0.1.1.0)
- `ueipab_payroll_enhancements` (v17.0.1.0.0)
- `ueipab_aguinaldos` (never installed)

### Migration Procedure

1. **Backup database:**
   ```bash
   docker exec odoo-dev-postgres pg_dump -U odoo database_name > backup.sql
   ```

2. **Uninstall old modules** (via Odoo UI):
   - Apps → Remove filter → Search each module → Uninstall

3. **Update module list:**
   ```bash
   docker exec odoo-dev-web odoo -c /etc/odoo/odoo.conf -d database_name -u base --stop-after-init
   ```

4. **Install new module:**
   ```bash
   docker exec odoo-dev-web odoo -c /etc/odoo/odoo.conf -d database_name -i ueipab_hr_payroll --stop-after-init
   ```

5. **Restart Odoo:**
   ```bash
   docker restart odoo-dev-web
   ```

6. **Clear browser cache:**
   - Enable Debug Mode
   - Click bug icon → "Regenerate Assets Bundles"
   - Hard refresh: Ctrl+Shift+R

### Data Preservation

- ✅ All contract field data preserved (no schema changes)
- ✅ All existing payslips unaffected
- ✅ All accounting entries intact
- ✅ No data migration required

## Usage

### Regular Payroll

1. Create payroll batch (HR → Payroll → Batches)
2. Add employees
3. Click "Generate Payslips"
4. Leave structure selector empty (uses contract structure)
5. Generate → Compute → Validate

### Aguinaldos Payroll

1. Create payroll batch named "Aguinaldos31" (or containing "aguinaldo")
2. Add employees
3. Click "Generate Payslips"
4. **Automatic:** AGUINALDOS_2025 structure pre-selected
5. Generate → Compute → Validate

### Custom Structure Override

1. Create any payroll batch
2. Add employees
3. Click "Generate Payslips"
4. **Manually select** desired structure from dropdown
5. Generate → Compute → Validate

## Technical Details

### Dependencies
- `hr_contract` (Odoo Community)
- `hr_payroll_community` (OCA)

### Models Extended
- `hr.contract` (persistent model)
- `hr.payslip.employees` (transient wizard)

### Views Modified
- Contract form view (field additions)
- Payslip generation wizard (structure selector)

### Database Impact
- ✅ No table creation
- ✅ No schema modifications
- ✅ Model inheritance only
- ✅ View inheritance only
- ✅ Zero-downtime deployment possible

## Testing

Module has been thoroughly tested:
- ✅ 44-employee Aguinaldos batch
- ✅ $13,124.65 USD total validated
- ✅ All accounting entries verified
- ✅ Regular payroll compatibility confirmed
- ✅ Browser cache resolution documented

See `/opt/odoo-dev/documentation/AGUINALDOS_TEST_RESULTS_2025-11-10.md` for complete test results.

## Troubleshooting

### Structure Selector Not Visible

**Symptom:** After installation, structure selector field doesn't appear in wizard

**Solution:**
1. Enable Debug Mode (`?debug=1` in URL)
2. Click bug icon (🐞) → "Regenerate Assets Bundles"
3. Hard refresh browser: Ctrl+Shift+R

### Payslips with Zero Amounts

**Symptom:** Aguinaldos payslips show $0.00

**Cause:** NULL `ueipab_monthly_salary` in contracts

**Solution:**
```sql
UPDATE hr_contract
SET ueipab_monthly_salary = ueipab_salary_base + ueipab_bonus_regular + ueipab_extra_bonus
WHERE state = 'open'
  AND ueipab_monthly_salary IS NULL
  AND (ueipab_salary_base + ueipab_bonus_regular + ueipab_extra_bonus) > 0;
```

## Documentation

- **Consolidation Plan:** `/opt/odoo-dev/documentation/MODULE_CONSOLIDATION_PLAN.md`
- **Test Results:** `/opt/odoo-dev/documentation/AGUINALDOS_TEST_RESULTS_2025-11-10.md`
- **Feature Spec:** `/opt/odoo-dev/documentation/PAYROLL_BATCH_STRUCTURE_SELECTOR.md`
- **Production Migration:** `/opt/odoo-dev/documentation/PRODUCTION_MIGRATION_PLAN.md`

## Support

- **Author:** UEIPAB Technical Team
- **Website:** https://ueipab.edu.ve
- **Repository:** Internal UEIPAB Git Repository

## Changelog

### Version 17.0.2.0.0 (2025-11-10)
- **MAJOR:** Consolidated 3 modules into 1
- Module structure reorganization
- Eliminated code duplication
- Improved documentation
- Follows Odoo best practices

### Previous Versions
- 17.0.1.1.0: ueipab_hr_contract final standalone version
- 17.0.1.0.0: ueipab_payroll_enhancements standalone version
- 17.0.1.0.0: ueipab_aguinaldos (never installed, redundant)

## License

This module is licensed under AGPL-3.

---

**Module Status:** ✅ Production Ready
**Last Updated:** November 10, 2025
**Odoo Version:** 17.0 Community Edition
