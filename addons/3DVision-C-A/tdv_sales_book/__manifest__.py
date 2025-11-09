# -*- coding: utf-8 -*-
{
    'name': "Sales Book",
    'summary': "summary",
    'description': "Description",
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Customization',
    'version': '1.0.0',
    'depends': ['account','tribute_fields','report_xlsx'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'reports/sales_book_report_views.xml',
        'views/sales_book_views.xml',
        'views/menu_views.xml',
    ],
}