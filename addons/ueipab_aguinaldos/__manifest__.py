# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Aguinaldos',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Aguinaldos (Christmas Bonus) for UEIPAB Venezuelan Payroll',
    'description': """
UEIPAB Aguinaldos Module
========================
Adds monthly salary tracking fields for Aguinaldos calculations.

Features:
- Monthly salary field synced from spreadsheet
- Enhanced audit trail with exchange rate tracking
- Aguinaldos salary structure (2x monthly salary)
    """,
    'author': 'UEIPAB',
    'depends': ['hr_contract', 'hr_payroll'],
    'data': [
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
