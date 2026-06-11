# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Sales Enhancements',
    'version': '17.0.1.2.0',
    'category': 'Sales',
    'summary': 'Enrollment quotation engine (Glenda AI + Sales team) with Acuerdo de Inscripción PDF',
    'description': """
UEIPAB Sales Quotation System
=============================
- AI-generated quote flags (is_glenda_quote / quote_channel) on sale.order
- Customer-email suppression for AI quotes (delivery via Glenda channels only)
- Enrollment quote engine: 3 llamados 2026-2027 (comunicado 10/06/2026)
- Custom PDF "Acuerdo de Inscripción" (agreement layout with school logo)

See documentation/UEIPAB_SALES_QUOTATION_PLAN.md
""",
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
        'reports/report_actions.xml',
        'reports/quotation_agreement_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
