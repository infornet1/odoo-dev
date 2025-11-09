# -*- coding: utf-8 -*-
{
    "name": "fiscal_printer_service",
    "summary": """Fiscal Printer Service""",
    "description": """""",
    "author": "3DVision, C.A.",
    "website": "http://www.3dvisionve.com",
    "category": "Point of Sale",
    "version": "0.1",
    "license": "LGPL-3",
    "depends": ["base", "account", "base_address_extended"],
    "data": [
        # 'security/ir.model.access.csv',
        "security/ir.model.access.csv",
        "views/x_pos_fiscal_printer_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "fiscal_printer_service/static/src/js/**/*",
            "fiscal_printer_service/static/src/xml/**/*",
            "fiscal_printer_service/static/src/css/**/*",
            "fiscal_printer_service/static/src/lib/**/*",
            "fiscal_printer_service/static/src/services/**/*",
        ],
        
    },
}
