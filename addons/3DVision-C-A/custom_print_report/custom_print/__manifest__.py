{
    "name": "Custom Print",
    "version": "1.0",
    "summary": "Personalized printing management",
    "description": "Module to customize quotation printing formats",
    "category": "Tools",
    "author": "Manolo",
    "depends": ["base", "web", "sale"],
    "data": [
        "reports/custom_quotation_report.xml",
        "views/res_config_settings.xml",
        "views/sale_order.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
