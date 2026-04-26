# -*- coding: utf-8 -*-
from odoo import fields, models


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
