{
    'name': 'UEIPAB HR Contract Extensions',
    'version': '17.0.1.0.0',
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