# -*- coding: utf-8 -*-
{
    "name": "Inventory resume",
    "summary": "summary",
    "description": "Description",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "category": "Customization",
    "version": "1.0.0",
    "depends": ["account", "stock", "report_xlsx","base"],
    "license": "LGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "views/tdv_inventory_resume.xml",
        "views/tdv_inventory_resume_line.xml",
        "report/tdv_inventory_report.xml",
    ],
    "installable": True,
    "application": True,
    "assets": {
        "web.assets_backend": [
            "tdv_inventory_book/static/src/xml/monthly_inventory_resume.xml",
        ],
    },
}
