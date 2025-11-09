{
    'name': 'UEIPAB Payslip Reports',
    'version': '17.0.1.0',
    'author': '3DVision C.A.',
    'description': 'Custom payslip reports for Venezuelan labor compliance',
    'summary': 'Professional payslip reports following Venezuelan LOTTT requirements',
    'depends': ['hr_payroll_community'],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
    'data': [
        'views/hr_payslip_view.xml',
        'report/payslip_report_views.xml',
        'report/payslip_templates.xml',
    ]
}