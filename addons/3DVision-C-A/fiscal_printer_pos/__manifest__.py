# -*- coding: utf-8 -*-
{
    "name": "fiscal_printer_pos",
    "summary": """Fiscal Printer for POS""",
    "description": """""",
    "author": "3DVision, C.A.",
    "website": "http://www.3dvisionve.com",
    "category": "Point of Sale",
    "version": "0.1",
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "depends": ["base", "point_of_sale", "fiscal_printer", "base_address_extended"],
    "data": [
        'security/ir.model.access.csv',
        "views/pos_payment_method.xml",
        "views/pos_order.xml",
        "views/inherited_views.xml",
        "views/pos_report_z.xml"
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "fiscal_printer_pos/static/src/**/*",
            "fiscal_printer_service/static/src/**/*",
        ]
    },
}
