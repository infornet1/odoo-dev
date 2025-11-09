{
    "name": "Custom Print Quotation",
    "version": "1.0",
    "summary": "Custom quote printing",
    "description": "Module to customize quotation printing formats",
    "category": "Tools",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
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
