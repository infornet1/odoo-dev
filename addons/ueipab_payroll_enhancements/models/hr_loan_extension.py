# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class HrLoan(models.Model):
    _inherit = 'hr.loan'

    recovery_type = fields.Selection([
        ('quincena', 'Quincena (NOMINA_VE_V2)'),
        ('liquidacion', 'Liquidación (LIQUID_VE_V2)'),
    ], string='Tipo de Recuperación',
       default='quincena',
       required=True,
       help='Determines which payslip structure triggers the deduction:\n'
            '• Quincena: deducted from regular bi-weekly NOMINA_VE_V2 payslips\n'
            '• Liquidación: deducted only from LIQUID_VE_V2 termination payslip\n\n'
            'For Quincena: set installment date inside the target quincena window.\n'
            'For Liquidación: set installment date inside the employee\'s final period.')

    def action_approve(self):
        # Phase 1: advance was already paid outside Odoo.
        # ohrms_loan_accounting requires accounting fields that would double-count
        # the disbursement. Bypass its journal entry — just validate and approve.
        if not self.loan_lines:
            raise UserError('Debe calcular las cuotas antes de aprobar.')
        contract = self.env['hr.contract'].search(
            [('employee_id', '=', self.employee_id.id)], limit=1)
        if not contract:
            raise UserError('El empleado no tiene un contrato definido.')
        self.write({'state': 'approve'})
        return True


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_inputs(self, contracts, date_from, date_to):
        res = super().get_inputs(contracts, date_from, date_to)
        # ohrms_loan already injected LO inputs based on installment date range.
        # Guard: zero out any LO input whose loan.recovery_type doesn't match
        # the current payslip structure, preventing cross-structure deductions.
        struct_code = self.struct_id.code if self.struct_id else ''
        for r in res:
            if r.get('code') == 'LO' and r.get('amount', 0) != 0:
                loan_line_id = r.get('loan_line_id')
                if not loan_line_id:
                    continue
                loan = self.env['hr.loan.line'].browse(loan_line_id).loan_id
                recovery_type = loan.recovery_type or 'quincena'
                if recovery_type == 'liquidacion' and struct_code != 'LIQUID_VE_V2':
                    r['amount'] = 0
                    r.pop('loan_line_id', None)
                elif recovery_type == 'quincena' and struct_code == 'LIQUID_VE_V2':
                    r['amount'] = 0
                    r.pop('loan_line_id', None)
        return res
