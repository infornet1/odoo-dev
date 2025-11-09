{
    "name": "Custom Print Dispatch Guide",
    "version": "17.0.0.1",
    "summary": "Custom Dispatch Guide printing in invoices",
    "description": "Module to customize Dispatch Guide printing formats",
    "category": "Tools",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "depends": ["tribute_fields", "tdv_module_vehicle"],
    "data": [
            "data/res_partner_category_data.xml",
            "reports/custom_invoice_dispatch_guide_report.xml",
            "views/res_config_settings.xml",
            "views/account_move.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
