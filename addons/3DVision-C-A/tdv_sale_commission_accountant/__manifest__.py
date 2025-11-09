# -*- coding: utf-8 -*-
{
    'name': "tdv_sale_commission_accountant",

    'summary': """commission sales accountant""",

    'description': """""",

    'author': "3DVision, C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tdv_sale_commissions', 'account_accountant'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/menus.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3'
}
