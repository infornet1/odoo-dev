# -*- coding: utf-8 -*-
{
    "name": "TDV POS Kitchen Customer Name",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Add customer name to kitchen order receipts",
    "description": """
        This module adds the customer name to kitchen order receipts (comandas)
        in the Point of Sale restaurant module.
    """,
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "depends": ["point_of_sale", "pos_restaurant"],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "tdv_pos_kitchen_customer_name/static/src/js/models.js",
            "tdv_pos_kitchen_customer_name/static/src/xml/order_change_receipt_template.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
