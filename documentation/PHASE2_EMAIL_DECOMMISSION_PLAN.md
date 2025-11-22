# Phase 2 Email Delivery System - Decommission Plan

**Date:** 2025-11-22
**Reason:** Replaced by `hr_payslip_monthly_report` module (Cybrosys)
**Status:** 🔴 DECOMMISSIONED

---

## Executive Summary

The custom Payslip Email Delivery System (Phase 2) developed in module `ueipab_payroll_enhancements` v1.28.0 is being decommissioned in favor of the **hr_payslip_monthly_report** module, which provides:

- ✅ Automatic email sending on payslip confirmation
- ✅ Mass confirm payslips wizard
- ✅ Monthly payslip reporting
- ✅ Maintained by Cybrosys (professional support)

**Decision:** No need to maintain duplicate functionality. Use proven, maintained module instead.

---

## Components to Remove

### 1. Python Models (2 files)
```
addons/ueipab_payroll_enhancements/models/payslip_email_report.py
addons/ueipab_payroll_enhancements/wizard/payslip_email_wizard.py
```

**Impact:**
- Removes `PayslipEmailReport` (report.ueipab_payroll_enhancements.report_payslip_email_document)
- Removes `AguinaldosEmailReport` (report.ueipab_payroll_enhancements.report_aguinaldos_email_document)
- Removes `PayslipEmailWizard` (payslip.email.wizard) TransientModel

### 2. XML Views/Reports (3 files)
```
addons/ueipab_payroll_enhancements/wizard/payslip_email_wizard_view.xml
addons/ueipab_payroll_enhancements/reports/payslip_email_report.xml
addons/ueipab_payroll_enhancements/reports/aguinaldos_email_report.xml
```

**Impact:**
- Removes wizard UI (action_payslip_email_wizard)
- Removes QWeb PDF templates for regular payslip and aguinaldos emails

### 3. Email Templates Directory (entire folder)
```
addons/ueipab_payroll_enhancements/data/email_templates/
  ├── payslip_email_template.xml.bak
  └── aguinaldos_email_template.xml.bak
```

**Impact:**
- Removes backup email template files (never loaded in manifest)

### 4. Menu Entry (1 section in payroll_reports_menu.xml)
```xml
<!-- Lines 63-66 -->
<menuitem id="menu_payslip_email"
          name="Send by Email"
          parent="menu_payroll_reports"
          action="action_payslip_email_wizard"
          sequence="15"/>
```

**Impact:**
- Removes "Payroll > Reporting > Send by Email" menu item

### 5. Security Rules (2 lines in ir.model.access.csv)
```csv
access_payslip_email_wizard_user,payslip.email.wizard.user,model_payslip_email_wizard,...
access_payslip_email_wizard_manager,payslip.email.wizard.manager,model_payslip_email_wizard,...
```

**Impact:**
- Removes access rights for payslip.email.wizard model

### 6. Manifest References (3 lines in __manifest__.py)
```python
Line 71-73: # Email Templates comments (informational only)
Line 83:    'wizard/payslip_email_wizard_view.xml',
Line 92:    'reports/payslip_email_report.xml',
Line 93:    'reports/aguinaldos_email_report.xml',
```

---

## Migration Path to hr_payslip_monthly_report

### Features Comparison

| Feature | Custom Phase 2 | hr_payslip_monthly_report |
|---------|----------------|---------------------------|
| Batch email sending | ✅ Manual wizard | ✅ Auto on confirmation |
| PDF report attachment | ✅ QWeb templates | ✅ Built-in template |
| Regular payslips | ✅ Custom template | ✅ Standard template |
| Aguinaldos | ✅ Custom template | ⚠️ Use standard template |
| Email templates | ✅ Custom | ✅ Configurable |
| Mass confirmation | ❌ Not implemented | ✅ Wizard included |

### Configuration Steps

1. **Settings > General Settings > Payroll**
   - Enable "Automatic Payslip Email" option
   - Configure email template

2. **Email Template Customization**
   - Navigate to: Settings > Technical > Email > Templates
   - Search for payslip-related templates
   - Customize subject/body as needed

3. **Usage**
   - Confirm payslip → Email automatically sent
   - OR: Use "Mass Confirm Payslips" wizard for batch

---

## Decommission Procedure

### Step 1: Backup Current State
```bash
# Create git tag before decommission
cd /opt/odoo-dev
git tag -a v1.28.0-phase2-final -m "Phase 2 email system - final version before decommission"
git push origin v1.28.0-phase2-final
```

### Step 2: Remove Files
```bash
cd /opt/odoo-dev/addons/ueipab_payroll_enhancements

# Remove Python models
rm models/payslip_email_report.py
rm wizard/payslip_email_wizard.py

# Remove XML views/reports
rm wizard/payslip_email_wizard_view.xml
rm reports/payslip_email_report.xml
rm reports/aguinaldos_email_report.xml

# Remove email templates directory
rm -rf data/email_templates/
```

### Step 3: Update Configuration Files

**A. Update __manifest__.py:**
- Remove lines 83, 92, 93 (email wizard and reports)
- Remove lines 71-73 (email template comments)
- Update version: `1.28.0` → `1.29.0`
- Update summary: Remove "email delivery"

**B. Update security/ir.model.access.csv:**
- Remove 2 lines for payslip_email_wizard (user and manager)

**C. Update views/payroll_reports_menu.xml:**
- Remove lines 63-66 (menu_payslip_email menuitem)

### Step 4: Update Module in Odoo
```bash
# Restart Odoo
docker restart odoo-dev-web

# Upgrade module via Odoo shell
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])
module.button_immediate_upgrade()
env.cr.commit()
exit()
EOF
```

### Step 5: Update Documentation

**A. CLAUDE.md:**
- Remove Phase 2 section (lines about email delivery)
- Add note about hr_payslip_monthly_report usage

**B. PAYSLIP_EMAIL_DELIVERY_SYSTEM.md:**
- Add deprecation notice at top
- Update status to "🔴 DECOMMISSIONED"
- Add migration instructions

### Step 6: Commit Changes
```bash
git add -A
git commit -m "refactor(payroll): Decommission Phase 2 email system, use hr_payslip_monthly_report

🗑️ REMOVED Phase 2 Components:
- Removed payslip email wizard (payslip.email.wizard)
- Removed email report models (PayslipEmailReport, AguinaldosEmailReport)
- Removed QWeb PDF templates for email delivery
- Removed 'Send by Email' menu entry
- Removed email template directory
- Removed security rules for email wizard

📦 MIGRATION:
- Now using hr_payslip_monthly_report module (v17.0.1.0)
- Automatic email on payslip confirmation
- Mass confirm payslips wizard available
- Professional support from Cybrosys

Module Version: v1.28.0 → v1.29.0

Rationale: No need to maintain duplicate functionality when proven
module exists with better features and professional maintenance."
```

---

## Rollback Plan

If decommission causes issues:

```bash
# Revert to tagged version
git checkout v1.28.0-phase2-final

# Restart Odoo
docker restart odoo-dev-web

# Downgrade module
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<'EOF'
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])
module.button_immediate_upgrade()
env.cr.commit()
exit()
EOF
```

---

## Testing Checklist

After decommission:

- [ ] Module upgrades without errors
- [ ] No orphaned menu entries
- [ ] No orphaned database records
- [ ] Other reports still work (disbursement, prestaciones, liquidación)
- [ ] hr_payslip_monthly_report features working
- [ ] Email sending configured and tested

---

## Timeline

- **2025-11-22:** Phase 2 completed (v1.28.0)
- **2025-11-22:** hr_payslip_monthly_report installed
- **2025-11-22:** Decommission plan created
- **2025-11-22:** Decommission executed (v1.29.0)

---

## Archived Documentation

Original Phase 2 documentation preserved at:
- `documentation/PAYSLIP_EMAIL_DELIVERY_SYSTEM.md` (with deprecation notice)
- Git tag: `v1.28.0-phase2-final`

**Contact:** HR or technical support at recursoshumanos@ueipab.edu.ve
