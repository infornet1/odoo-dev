#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick script to upgrade ueipab_payroll_enhancements module"""

import odoo
from odoo import api, SUPERUSER_ID

# Get registry
registry = odoo.registry('testing')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Find module
    module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])

    if module:
        print(f"Module state before: {module.state}")

        # Button upgrade
        module.button_immediate_upgrade()

        print("Module upgraded successfully")
    else:
        print("Module not found!")
