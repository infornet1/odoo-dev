# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Payroll Enhancements',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Enhanced payroll batch generation with structure selector',
    'description': """
UEIPAB Payroll Enhancements
============================
Enhancements to HR Payroll Community for UEIPAB-specific requirements.

Features:
---------
* Salary structure selector in batch payslip generation wizard
* Smart defaults based on batch name/context
* Support for special payroll structures (Aguinaldos, bonuses, etc.)
* Maintains backward compatibility with standard flow

Use Cases:
----------
* Generate Aguinaldos batch with correct structure
* Generate bonus payslips without manual correction
* Generate liquidation payslips with appropriate structure
* Flexible override for any special payroll scenario
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': [
        'hr_payroll_community',
        'ueipab_hr_contract',  # For access to custom fields if needed
    ],
    'data': [
        'views/hr_payslip_employees_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
