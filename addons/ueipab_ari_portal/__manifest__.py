# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB AR-I Portal',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Employee self-service portal for AR-I tax withholding declarations',
    'description': """
UEIPAB AR-I Portal
==================
Employee self-service portal for managing AR-I (Agente de Retención - Impuesto sobre la Renta)
tax withholding declarations as required by Venezuelan law (SENIAT).

Features:
---------
* Employee portal for AR-I submission
* Automatic income calculation from contract
* Desgravamen selection (Único 774 UT or Detallado)
* Family dependents (cargas familiares) declaration
* Excel export using official SENIAT template
* HR approval workflow
* Quarterly deadline reminders (March, June, September, December)
* Integration with payroll deductions

Legal Basis:
------------
* Decreto Nº 1.808 (Gaceta Oficial 36.203, May 12, 1997)
* Ley de ISLR - Artículos 57, 59, 61
* Reglamento Parcial LISLR - Articles 5-7

Update Schedule:
----------------
* Initial: Before January 15 or first paycheck
* Variations: Before March 15, June 15, September 15, December 15
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': [
        'hr',
        'hr_contract',
        'portal',
        'mail',
        'ueipab_hr_contract',  # For ueipab_ari_withholding_rate field
    ],
    'data': [
        # Security
        'security/ari_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ari_cron.xml',
        'data/mail_templates.xml',

        # Views
        'views/hr_employee_ari_views.xml',
        'views/hr_contract_views.xml',
        'views/portal_templates.xml',
        'views/portal_menu.xml',

        # Wizards
        'wizard/ari_wizard_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'ueipab_ari_portal/static/src/css/portal.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
