# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB HR Payroll Customizations',
    'version': '17.0.2.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Venezuelan payroll customizations for UEIPAB',
    'description': """
UEIPAB HR Payroll Customizations
=================================
Complete Venezuelan payroll system for UEIPAB including contract field
extensions and payroll processing enhancements.

This module consolidates previously separate modules (ueipab_hr_contract,
ueipab_payroll_enhancements, and ueipab_aguinaldos) into a single,
maintainable module following Odoo best practices.

Contract Field Extensions
-------------------------
* Venezuelan compensation structure (70/25/5 distribution)
  - ueipab_salary_base: 70% base salary component
  - ueipab_bonus_regular: 25% regular bonus
  - ueipab_extra_bonus: 5% extra performance bonus

* Bi-monthly payroll schedule
  - First payment: 15th of each month
  - Second payment: Last day of each month

* Venezuelan benefits
  - Cesta Ticket (food allowance) in USD
  - Wage tracking in VES (Venezuelan Bolivars)

* Prestaciones Sociales (social benefits)
  - Reset date tracking
  - Last payment date tracking

* Aguinaldos (Christmas Bonus)
  - Monthly salary field from payroll spreadsheet
  - Complete audit trail with exchange rate tracking
  - Independent from regular 70/25/5 distribution
  - Synced from Google Sheets master spreadsheet

Payroll Processing Enhancements
--------------------------------
* Batch payslip structure selector
  - Override structure for entire batch
  - Smart defaults based on batch name
  - Automatic Aguinaldos detection

* Smart batch processing
  - Detects "Aguinaldos" in batch name
  - Auto-selects AGUINALDOS_2025 structure
  - Manual override available for any scenario

* Use cases supported
  - Regular bi-monthly payroll (UEIPAB_VE structure)
  - Aguinaldos Christmas bonuses
  - Special bonuses and liquidations
  - Any custom payroll structure

Technical Details
-----------------
* Model inheritance: hr.contract (persistent)
* Wizard enhancement: hr.payslip.employees (transient)
* No database schema migrations required
* View inheritance only (non-breaking changes)
* Backward compatible with existing payroll structures
* Tested and production-ready

Migration from Previous Modules
--------------------------------
This module replaces:
- ueipab_hr_contract (v17.0.1.1.0)
- ueipab_payroll_enhancements (v17.0.1.0.0)
- ueipab_aguinaldos (never installed, redundant)

Migration procedure:
1. Uninstall old modules
2. Install ueipab_hr_payroll
3. All contract data preserved (no schema changes)
4. All functionality maintained

See /opt/odoo-dev/documentation/MODULE_CONSOLIDATION_PLAN.md for details.

Testing & Validation
--------------------
* Tested with 44-employee Aguinaldos batch
* $13,124.65 USD total validated
* All accounting entries verified
* Zero-downtime deployment tested
* Browser cache resolution documented

See /opt/odoo-dev/documentation/AGUINALDOS_TEST_RESULTS_2025-11-10.md
for complete test results.
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': [
        'hr_contract',
        'hr_payroll_community',
    ],
    'data': [
        'views/hr_contract_views.xml',
        'views/hr_payslip_employees_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
