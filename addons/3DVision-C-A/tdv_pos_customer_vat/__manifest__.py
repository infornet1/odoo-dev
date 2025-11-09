# -*- coding: utf-8 -*-
{
    'name': 'TDV POS Customer VAT',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Display customer VAT in POS payment screen',
    'description': """
        This module adds the customer VAT field to the POS payment screen.
        The VAT number is displayed next to the customer name in the format: Customer Name - (VAT).
    """,
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'tdv_pos_customer_vat/static/src/xml/payment_screen_patch.xml',
            'tdv_pos_customer_vat/static/src/js/pos_customer_vat.js',
        ],
    },
    'installable': True,
    'auto_install': True,
    'application': False,
    'license': 'LGPL-3',
}
