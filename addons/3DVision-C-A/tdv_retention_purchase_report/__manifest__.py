# -*- coding: utf-8 -*-
{
    'name': "Retention Purchase Report",
    'summary': "Retention Purchase Report by 3DVision",
    'description': "Description",
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Report',
    'version': '1.0.0',
    'depends': ['account','retenciones','tdv_purchase_report'],
    'license': 'LGPL-3',
    'data': [
        'views/purchase_report_views.xml',
    ],
    'installable': True,
    'auto_install':True,
    'application': True,

}
