# -*- coding: utf-8 -*-
{
    'name': "Ref Payment POS",
    'summary': """summary""",
    'description': "Description",
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Customization',
    'version': '17.0.0.0',
    'depends': ["point_of_sale", "account"],
    'license': 'LGPL-3',
    'data': [
        # 'security/ir.model.access.csv',
        'views/pos_payment_method_views.xml',
    ],
    'assets':{
        "point_of_sale._assets_pos":[
            "tdv_pos_payment_ref/static/src/app/store/model.js",

            "tdv_pos_payment_ref/static/src/app/screens/payment_screen/payment_screen.js"
        ]
    },
    'installable': True,
    'application': True,

}
