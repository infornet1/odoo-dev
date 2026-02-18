{
    'name': 'UEIPAB HR Employee Extensions',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Venezuelan employee fields for UEIPAB (RIF, document expiry)',
    'description': """
UEIPAB HR Employee Extensions
==============================
Extends hr.employee with Venezuelan-specific fields:
- RIF (Registro de Informacion Fiscal) number and expiry date
- Combined document expiry CRON (RIF + Cedula)

Follows the same pattern as ueipab_hr_contract for contract extensions.
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': ['hr', 'hr_employee_updation'],
    'data': [
        'views/hr_employee_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
