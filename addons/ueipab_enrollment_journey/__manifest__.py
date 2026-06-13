# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Enrollment Journey',
    'version': '17.0.0.2.0',
    'category': 'Sales',
    'summary': 'Customer-facing enrollment journey wizard 2026-2027 (6-step timeline + hybrid clearance)',
    'description': """
UEIPAB Enrollment Journey Wizard
================================
- enrollment.journey: one record per family, 6 clearance steps
- Public timeline page /enrollment-journey/<token> (mora-policy style)
- Hybrid clearance: soft auto-validation + staff manual clear
- Glenda floating assistant bubble (Telegram deep link)

See documentation/ENROLLMENT_JOURNEY_WIZARD.md
""",
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': ['ueipab_sales'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/enrollment_journey_views.xml',
        'reports/enrollment_contract_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
