# -*- coding: utf-8 -*-
{
    'name': "Purchase Report",
    'summary': "Purchase Report by 3DVision",
    'description': "Description",
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Report',
    'version': '1.0.0',
    'depends': ['account','purchase','report_xlsx','tribute_fields'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',

        'data/purchase_report_paperformat.xml',
        'reports/purchase_report_template_views.xml',

        'views/purchase_report_views.xml',
        'views/account_move_view.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
}
