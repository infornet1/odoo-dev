# -*- coding: utf-8 -*-
{
    'name': "Purchase Sale Tax",
    'summary': "summary",
    'description': "Description",
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Customization',
    'version': '1.0.0',
    'depends': ['base','account','purchase', 'sale'],
    'license': 'LGPL-3',
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_tax_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        # 'views/account_move_views.xml'
    ],
    'installable': True,
    'application': True,

}
