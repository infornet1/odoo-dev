# -*- coding: utf-8 -*-

{
    "name": "Fiscal Printer",
    "version": "1.0.0",
    "description": """Sales point helper for fiscal invoice ECSPOS printers""",
    "category": "Sales",
    'website': "https://www.3dvisionve.com",
    "depends": ["base", "account", "fiscal_printer_service"],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "data": [
        "security/ir.model.access.csv",
        # 'views/fiscal_printer_menus.xml',
        "views/res_partner.xml",
        "views/account_move.xml",
        "views/account_journal.xml",
        "views/fiscal_groups.xml",
        "views/res_company.xml",
        "views/account_tax.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "fiscal_printer/static/src/js/invoice_fiscal_printer_action.js",
            "fiscal_printer/static/src/xml/invoice_fiscal_printer_action.xml",
        ],
    },
}
