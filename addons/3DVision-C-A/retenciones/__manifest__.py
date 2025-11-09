# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Retenciones",
    "version": "17.0.3.0.11",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "depends": ["base", "tribute_fields", "report_xml"],
    "summary": "Módulo encargado de la creación y gestión de retenciones para clientes y proveedores",
    "description": """
        Este módulo crea un nuevo modelo que se encarga de registrar
        las retenciones aplicadas tanto a facturas de proveedores como de clientes,
        genera reportes relacionados con las retenciones (PDF y TXT) y los asientos correspondientes.
    """,
    "license": "LGPL-3",
    "application": True,
    "installable": True,
    # "post_init_hook": "_init_hook",
    "data": [
        # Security
        "security/ir.model.access.csv",

        # Data
        "data/retention_sequence.xml",
        
        # Views
        "views/retention_views.xml",
        "views/retention_tax_views.xml",
        "views/account_move.xml",
        "views/account_move_out_views.xml",
        "views/res_partner_view.xml",
        "views/res_config_settings.xml",
        "views/menus_view.xml",
        
        # Reports
        "report/retention_report_views.xml",
        "report/retention_text_report.xml",
        "report/retention_report.xml",
        "report/account_move_retention_report_views.xml",
        "report/account_move_retention_report_template.xml",
        
        # Wizards
        "wizards/account_move_retention_wizard_views.xml",
    ],
    "demo": ["demo/retention_demo_data.xml"],
}
