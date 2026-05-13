{
    'name': 'UEIPAB HR Employee Extensions',
    'version': '17.0.1.3.0',
    'category': 'Human Resources',
    'summary': 'Venezuelan employee fields + Private Info Request system for UEIPAB',
    'description': """
UEIPAB HR Employee Extensions
==============================
Extends hr.employee with Venezuelan-specific fields:
- RIF (Registro de Informacion Fiscal) number and expiry date
- Combined document expiry CRON (RIF + Cedula)

v1.1.0 adds the Employee Private Info Request feature:
- HR sends tokenized emails requesting employees to confirm private data
- Public form at /employee-info/<token> — mobile-friendly, pre-filled
- 14 private fields: personal email/phone, marital status, emergency contact,
  ID, gender, birthday, birth place/country, city, state, zip, country
- HR diff notification email on every submission
- Batch wizard from Employees list view
- HR tracking view under Employees > Solicitudes de Datos
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': ['hr', 'hr_employee_updation', 'mail'],
    'data': [
        # Security must come first — required before any model views load
        'security/ir.model.access.csv',
        # Data / templates
        'data/cron.xml',
        'data/employee_info_request_template.xml',
        # Views
        'views/hr_employee_views.xml',
        'views/hr_employee_info_request_views.xml',
        'views/employee_info_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
