# -*- coding: utf-8 -*-
{
    "name": "tdv_delivery_report",
    "summary": "summary",
    "description": "Description",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "category": "Tools",
    "version": "1.0.0",
    "depends": ["base","stock","web","sale"],
    "license": "LGPL-3",
    "data": [
        "data/res_partner_category_data.xml",
        "reports/custom_delivery_report.xml",
        "views/res_config_settings.xml",
        "views/stock_picking_form.xml",
    ],
    "installable": True,
    "application": True,
}
