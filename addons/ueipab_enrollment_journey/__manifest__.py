# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Enrollment Journey',
    'version': '17.0.0.15.6',
    'category': 'Sales',
    'summary': 'Customer-facing enrollment journey wizard 2026-2027 (Step 0 gate + 9-step 3-block timeline)',
    'description': """
UEIPAB Enrollment Journey Wizard
================================
- enrollment.journey: one record per family, 9 steps in 3 blocks
- Block 1 hard gate: steps 4-9 blocked until 1-3 complete
- Contract escrow: step 3 triggers retention until payment plan paid
- Public timeline page /enrollment-journey/<token> (mora-policy style)
- Hybrid clearance: soft auto-validation + staff manual clear
- Glenda floating assistant bubble (Telegram deep link)
- QWeb PDF: Contrato Servicio Educativo (CSE-2627-XXXX sequence)

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
        'views/enrollment_withdrawal_views.xml',
        'reports/enrollment_contract_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
