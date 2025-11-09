# -*- coding: utf-8 -*-
{
    'name': "Sales Summary",
    'summary': "",
    'description': "",
    'author': "3DVision",
    'category': 'Report',
    'version': '1.0.0',
    'depends': ['base', 'account'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'reports/account_move_summary_report_views.xml',
        'reports/account_move_summary_report.xml',
        'wizards/account_move_summary_wizard_views.xml',
        'views/account_move_wizard_summary_menu.xml',
    ],
}
