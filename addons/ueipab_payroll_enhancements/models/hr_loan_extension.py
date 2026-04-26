# -*- coding: utf-8 -*-
from datetime import date as dt
from odoo import api, fields, models
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

    advance_bs_amount = fields.Float(
        string='Monto Adelanto (Bs.)',
        digits=(16, 2),
        help='Monto entregado al empleado en bolívares. '
             'Al ingresarlo junto con la tasa se calcula automáticamente el monto USD.')

    advance_exchange_rate = fields.Float(
        string='Tasa de Cambio (Bs./USD)',
        digits=(16, 4),
        default=lambda self: self._get_veb_rate(),
        help='Tasa BCV vigente al momento del adelanto. '
             'Auto-poblada desde res.currency.rate — editable hasta la aprobación.')

    # ── default lookups ────────────────────────────────────────────────────

    def _get_veb_rate(self):
        veb = self.env['res.currency'].search(
            [('name', 'in', ['VEB', 'VES']), ('active', '=', True)], limit=1)
        if not veb:
            return 0.0
        rate = self.env['res.currency.rate'].search(
            [('currency_id', '=', veb.id)], order='name desc', limit=1)
        return rate.company_rate if rate else 0.0

    def _default_loan_account(self):
        """1.1.06.01.001 — Cuentas por cobrar empleados (salary advance receivable)."""
        return self.env['account.account'].search(
            [('code', '=', '1.1.06.01.001')], limit=1)

    def _default_treasury_account(self):
        """1.1.01.02.001 — Banco Venezuela (default disbursement bank)."""
        return self.env['account.account'].search(
            [('code', '=', '1.1.01.02.001')], limit=1)

    def _default_payroll_journal(self):
        """Nómina y Salarios, Bonos y Prestaciones Sociales journal."""
        return self.env['account.journal'].search(
            [('type', '=', 'general'), ('name', 'ilike', 'Nomina')], limit=1)

    def _accounting_defaults_vals(self):
        """Return dict of accounting field defaults that are currently empty."""
        vals = {}
        if 'employee_account_id' in self._fields and not self.employee_account_id:
            acc = self._default_loan_account()
            if acc:
                vals['employee_account_id'] = acc.id
        if 'treasury_account_id' in self._fields and not self.treasury_account_id:
            acc = self._default_treasury_account()
            if acc:
                vals['treasury_account_id'] = acc.id
        if 'journal_id' in self._fields and not self.journal_id:
            journal = self._default_payroll_journal()
            if journal:
                vals['journal_id'] = journal.id
        return vals

    # ── creation ───────────────────────────────────────────────────────────

    @api.model
    def create(self, vals):
        """Auto-fill accounting defaults on new loans."""
        record = super().create(vals)
        defaults = record._accounting_defaults_vals()
        if defaults:
            record.write(defaults)
        return record

    # ── button action ──────────────────────────────────────────────────────

    def action_fill_accounting_defaults(self):
        """Button: fill any empty accounting fields with company defaults."""
        defaults = self._accounting_defaults_vals()
        if defaults:
            self.write(defaults)

    # ── onchanges ──────────────────────────────────────────────────────────

    @api.onchange('advance_bs_amount', 'advance_exchange_rate')
    def _onchange_bs_fields(self):
        """Auto-calculate USD loan_amount from Bs amount ÷ rate (helper, not enforced)."""
        if self.advance_bs_amount and self.advance_exchange_rate:
            self.loan_amount = round(self.advance_bs_amount / self.advance_exchange_rate, 2)

    @api.onchange('employee_id')
    def _onchange_employee_accounting_defaults(self):
        """Auto-fill accounting fields when employee is selected."""
        if not self.employee_id:
            return
        defaults = self._accounting_defaults_vals()
        for fname, val in defaults.items():
            setattr(self, fname, val)

    # ── approval ───────────────────────────────────────────────────────────

    def action_approve(self):
        """Approve loan and optionally post the advance disbursement journal entry."""
        if not self.loan_lines:
            raise UserError('Debe calcular las cuotas antes de aprobar.')
        contract = self.env['hr.contract'].search(
            [('employee_id', '=', self.employee_id.id)], limit=1)
        if not contract:
            raise UserError('El empleado no tiene un contrato definido.')
        treasury_acc = getattr(self, 'treasury_account_id', False)
        journal = getattr(self, 'journal_id', False)
        if treasury_acc and journal:
            self._create_advance_journal_entry()
        self.write({'state': 'approve'})
        return True

    def _create_advance_journal_entry(self):
        """Post DR Employee Receivable / CR Bank journal entry for the advance."""
        emp_receivable = self.env['account.account'].search(
            [('code', '=', '1.1.06.01.001')], limit=1)
        if not emp_receivable:
            return

        partner_id = False
        if self.employee_id.address_id:
            partner_id = self.employee_id.address_id.id
        elif getattr(self.employee_id, 'work_contact_id', False):
            partner_id = self.employee_id.work_contact_id.id

        amount = self.loan_amount
        today = dt.today()
        label = 'Anticipo Salarial – %s' % self.employee_id.name

        def _line(account_id, debit, credit):
            return (0, 0, {
                'name': label,
                'partner_id': partner_id,
                'account_id': account_id,
                'journal_id': self.journal_id.id,
                'date': today,
                'debit': debit,
                'credit': credit,
            })

        move = self.env['account.move'].create({
            'narration': label,
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'date': today,
            'line_ids': [
                _line(emp_receivable.id, amount, 0.0),
                _line(self.treasury_account_id.id, 0.0, amount),
            ],
        })
        move.action_post()


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_inputs(self, contracts, date_from, date_to):
        res = super().get_inputs(contracts, date_from, date_to)
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
