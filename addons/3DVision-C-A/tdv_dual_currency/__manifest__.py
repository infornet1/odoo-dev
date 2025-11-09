# -*- coding: utf-8 -*-
{
    "name": "Dual currency - payroll",
    "summary": "Module to handle the dual currency",
    "category": "Human Resources",
    "description": """
        Módulo para manejar conversión de moneda dual en nóminas:
        - Campos de conversión en contratos y líneas de nómina.
        - Configuración de moneda de conversión en la compañía.
        - Cálculo automático de montos en VES.
    """,
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "version": "0.1",
    "license": "AGPL-3",
    "depends": [
        "base_setup",
        "base",
        "hr",
        "hr_contract",
        "hr_payroll",
        "hr_holidays",
        "hr_payroll_account"
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/payslip_report_ves.xml",
        "report/payslip_resport_custom.xml",
        "views/hr_currency_conversion.xml",
        "views/hr_coin_vef.xml",
        "views/hr_payslip_worked_days.xml",
        "views/hr_inherit_line.xml",
        "views/hr_currency_config.xml",
        "views/hr_inherit_payslip_view.xml",
        "views/res_currency.xml",
        "views/hr_payslip_button_report.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False
}