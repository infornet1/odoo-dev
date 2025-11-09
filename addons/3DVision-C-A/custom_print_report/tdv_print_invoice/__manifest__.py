{
    "name": "Custom Print Invoice",
    "version": "17.0.0.1",
    "summary": "Custom invoice printing",
    "description": "Module to customize invoice printing formats",
    "category": "Tools",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "depends": ["tribute_fields"],
    "data": [
        "reports/custom_invoice_report.xml",
        "reports/custom_invoice_report_libre.xml",
        "views/res_config_settings.xml",
        "views/account_move.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
