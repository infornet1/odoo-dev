{
    'name': 'UEIPAB HR Contract Extensions',
    'version': '17.0.1.4.0',
    'category': 'Human Resources',
    'summary': 'Venezuelan payroll fields for UEIPAB contracts',
    'description': """
UEIPAB HR Contract Extensions
=============================
This module extends the HR contract model with Venezuelan payroll fields:
- Venezuelan compensation breakdown (Salary/Bonus/Extra Bonus)
- Bi-monthly payroll schedule
- Prestaciones sociales tracking
- Cesta Ticket management
- Aguinaldos (Christmas Bonus) tracking with audit trail
- Venezuelan Withhold Income Tax (ARI) rate management
  * Employee-specific ARI withholding rate (0.5% or 1%)
  * Quarterly tax bracket update tracking
  * Synced from payroll spreadsheet Column AA

Liquidation Historical Tracking (v1.3.0 - Added 2025-11-12):
- Original Hire Date: Track employment start for antiguedad continuity
- Previous Liquidation Date: Subtract already-paid antiguedad for rehires
- Vacation Paid Until: Calculate accrued vacation from last Aug 1 payment
- Supports complex scenarios: rehires, gaps, multiple liquidations

V2 Compensation Breakdown (v1.4.0 - Added 2025-11-16 - CEO APPROVED):
- ueipab_salary_v2: Salary subject to mandatory deductions (SSO, FAOV, PARO, ARI)
- ueipab_extrabonus_v2: Extra bonus exempt from deductions
- ueipab_bonus_v2: Regular bonus exempt from deductions
- Parallel V1/V2 operation: Both structures coexist during migration
- Transparent deduction base: Eliminates confusing percentage calculations
- Option A proration: Deductions calculated by actual payslip period days/30
- Data source: Google Spreadsheet columns K, L, M (100% validated)
- Legal compliance: CEO confirmed full Venezuelan labor law compliance
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': ['hr_contract'],
    'data': [
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}