# -*- coding: utf-8 -*-
"""
HR Contract Extension for AR-I Portal

Links AR-I declarations to contracts.
"""

from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # Link to AR-I declarations
    ari_declaration_ids = fields.One2many(
        'hr.employee.ari',
        'contract_id',
        string='AR-I Declarations'
    )
    ari_declaration_count = fields.Integer(
        string='AR-I Count',
        compute='_compute_ari_count'
    )
    current_ari_id = fields.Many2one(
        'hr.employee.ari',
        string='Current AR-I Declaration',
        compute='_compute_current_ari',
        help='Most recent approved AR-I declaration'
    )

    @api.depends('ari_declaration_ids')
    def _compute_ari_count(self):
        for contract in self:
            contract.ari_declaration_count = len(contract.ari_declaration_ids)

    @api.depends('ari_declaration_ids', 'ari_declaration_ids.state')
    def _compute_current_ari(self):
        for contract in self:
            current = self.env['hr.employee.ari'].search([
                ('contract_id', '=', contract.id),
                ('state', '=', 'approved')
            ], order='fiscal_year desc, submission_date desc', limit=1)
            contract.current_ari_id = current

    def action_view_ari_declarations(self):
        """Open AR-I declarations for this contract."""
        self.ensure_one()
        return {
            'name': 'AR-I Declarations',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.ari',
            'view_mode': 'tree,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_contract_id': self.id,
            }
        }
