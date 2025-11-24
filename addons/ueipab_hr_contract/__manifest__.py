{
    'name': 'UEIPAB HR Contract Extensions',
    'version': '17.0.2.0.0',
    'category': 'Human Resources',
    'summary': 'Venezuelan V2 payroll fields for UEIPAB contracts',
    'description': """
UEIPAB HR Contract Extensions (V2 Only)
=======================================
This module extends the HR contract model with Venezuelan V2 payroll fields.

V2 Compensation Breakdown (CEO APPROVED 2025-11-16):
- ueipab_salary_v2: Salary subject to mandatory deductions (SSO, FAOV, PARO, ARI)
- ueipab_extrabonus_v2: Extra bonus exempt from deductions
- ueipab_bonus_v2: Regular bonus exempt from deductions
- cesta_ticket_usd: Monthly food allowance ($40 default)

Additional Fields:
- Bi-monthly payroll schedule configuration
- Prestaciones sociales tracking
- Venezuelan Withhold Income Tax (ARI) rate management

Liquidation Historical Tracking:
- ueipab_original_hire_date: Employment start for antiguedad continuity
- ueipab_previous_liquidation_date: Already-paid antiguedad for rehires
- ueipab_vacation_paid_until: Last vacation payment date
- ueipab_vacation_prepaid_amount: Prepaid vacation/bono amount

Changelog:
- v2.0.0 (2025-11-24): REMOVED V1 fields (ueipab_salary_base, ueipab_bonus_regular,
  ueipab_extra_bonus, ueipab_deduction_base, ueipab_monthly_salary, ueipab_salary_notes)
- v1.5.0 (2025-11-17): Added ueipab_vacation_prepaid_amount field
- v1.4.0 (2025-11-16): Added V2 compensation fields
- v1.3.0 (2025-11-12): Added liquidation historical tracking
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