# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "3DVision - Payroll",
    "version": "17.0.0.0.5",
    "depends": ["hr_payroll"],
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "summary": "Allows a better payroll record for Venezuela",
    "description": """""",
    "license": "LGPL-3",
    "application": True,
    "installable": True,
    "data": [
        "security/ir.model.access.csv",
        "views/hr_payslip_other_inputs_views.xml",
        "views/hr_payslip_lines_views.xml",
        "views/hr_contract_views.xml",
        "views/hr_rule_parameter_views.xml",
        "views/hr_employee_views.xml",
    ],
}
