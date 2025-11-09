{
    "name": "Custom Print Account ",
    "version": "1.0",
    "summary": "Personalized printing management",
    "description": "Module to customize invoice printing formats",
    "category": "Tools",
    "author": "Manolo",
    "depends": ["base", "web", "account"],
    "data": [
        "reports/custom_invoice_report.xml",
        "views/res_config_settings.xml",
        "views/account_move.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
