# -*- coding: utf-8 -*-
{
    'name': "automatic pos invoice generation",
    'summary': "allows to generate an invoice from pos sales",
    'description': """
        Automatically generates the associated invoice for the current pos
        sale, and disable the button, as is required to invoice.
    """,
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Customization',
    'version': '1.0.0',
    'depends': ['base', 'point_of_sale'],
    'license': 'LGPL-3',
    'data': [
        # 'security/ir.model.access.csv',
        'views/pos_config.xml',
    ],
    'assets': {
        "point_of_sale._assets_pos": [
            # "automate_pos_invoice/static/src/js/Screens/PaymentScreen/PaymentScreen.js"
            "automate_pos_invoice/static/src/app/screens/paymentScreen/paymentScreen.js"
        ]
    }
}
