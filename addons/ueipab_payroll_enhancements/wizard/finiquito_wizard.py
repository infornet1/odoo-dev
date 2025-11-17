# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FiniquitoWizard(models.TransientModel):
    _name = 'finiquito.wizard'
    _description = 'Acuerdo Finiquito Laboral Wizard'

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Payslips',
        required=True,
        domain="[('struct_id.name', 'in', ['Liquidación Venezolana', 'Liquidación Venezolana V2']), ('state', '!=', 'cancel')]",
        help='Select liquidation payslips for finiquito agreement'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.ref('base.USD'),
        help='Currency for displaying amounts'
    )

    def action_print_pdf(self):
        """Generate PDF report"""
        self.ensure_one()
        
        data = {
            'payslip_ids': self.payslip_ids.ids,
            'currency_id': self.currency_id.id,
        }
        
        return self.env.ref('ueipab_payroll_enhancements.action_report_finiquito').report_action(
            self.payslip_ids, data=data
        )
