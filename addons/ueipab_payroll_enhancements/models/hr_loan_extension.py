# -*- coding: utf-8 -*-
import uuid
from datetime import date as dt
from odoo import api, fields, models
from odoo.exceptions import UserError


class HrLoan(models.Model):
    _inherit = 'hr.loan'

    # ── recovery type ──────────────────────────────────────────────────────

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

    # ── Bs helper fields ───────────────────────────────────────────────────

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

    # ── journal entry link ─────────────────────────────────────────────────

    move_id = fields.Many2one(
        'account.move',
        string='Asiento Contable',
        readonly=True,
        copy=False,
        help='Journal entry created at loan approval.')

    # ── acknowledgment fields ──────────────────────────────────────────────

    loan_ack_token = fields.Char(
        string='Token de Confirmación',
        readonly=True,
        copy=False)

    loan_ack_url = fields.Char(
        string='URL de Confirmación',
        compute='_compute_loan_ack_url')

    loan_is_acknowledged = fields.Boolean(
        string='Confirmado por Empleado',
        default=False,
        copy=False)

    loan_acknowledged_date = fields.Datetime(
        string='Fecha de Confirmación',
        readonly=True,
        copy=False)

    loan_acknowledged_ip = fields.Char(
        string='IP de Confirmación',
        readonly=True,
        copy=False)

    # ── recovery status ────────────────────────────────────────────────────

    loan_recovery_status = fields.Selection([
        ('pending', 'Pendiente de Descuento'),
        ('recovering', 'En Recuperación'),
        ('cleared', 'Saldado'),
    ], string='Estado de Recuperación',
       compute='_compute_loan_recovery_status',
       store=False)

    clearing_payslip_count = fields.Integer(
        string='Comprobantes de Descuento',
        compute='_compute_clearing_payslip_count',
        store=False)

    # ── computes ───────────────────────────────────────────────────────────

    @api.depends('balance_amount', 'loan_amount', 'state', 'loan_lines.paid')
    def _compute_loan_recovery_status(self):
        for loan in self:
            if loan.state != 'approve':
                loan.loan_recovery_status = 'pending'
            elif loan.balance_amount <= 0:
                loan.loan_recovery_status = 'cleared'
            elif loan.balance_amount < loan.loan_amount:
                loan.loan_recovery_status = 'recovering'
            else:
                loan.loan_recovery_status = 'pending'

    @api.depends('loan_lines.payslip_id')
    def _compute_clearing_payslip_count(self):
        for loan in self:
            loan.clearing_payslip_count = len(
                loan.loan_lines.filtered(lambda l: l.payslip_id))

    def action_view_clearing_payslips(self):
        self.ensure_one()
        payslip_ids = self.loan_lines.filtered(
            lambda l: l.payslip_id).mapped('payslip_id').ids
        if not payslip_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sin comprobantes',
                    'message': 'No hay comprobantes de descuento registrados.',
                    'type': 'warning',
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Comprobantes de Descuento – %s' % self.name,
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payslip_ids)],
        }

    @api.depends('loan_ack_token')
    def _compute_loan_ack_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for loan in self:
            if loan.loan_ack_token and loan.id:
                loan.loan_ack_url = (
                    f'{base_url}/loan/acknowledge/{loan.id}/{loan.loan_ack_token}')
            else:
                loan.loan_ack_url = ''

    # ── default lookups ────────────────────────────────────────────────────

    def _get_veb_rate(self, for_date=None):
        veb = self.env['res.currency'].search(
            [('name', 'in', ['VEB', 'VES']), ('active', '=', True)], limit=1)
        if not veb:
            return 0.0
        domain = [('currency_id', '=', veb.id)]
        if for_date:
            domain.append(('name', '<=', for_date))
        rate = self.env['res.currency.rate'].search(domain, order='name desc', limit=1)
        return rate.company_rate if rate else 0.0

    def _default_loan_account(self):
        return self.env['account.account'].search(
            [('code', '=', '1.1.06.01.001')], limit=1)

    def _default_treasury_account(self):
        return self.env['account.account'].search(
            [('code', '=', '1.1.01.02.001')], limit=1)

    def _default_payroll_journal(self):
        return self.env['account.journal'].search(
            [('type', '=', 'general'), ('name', 'ilike', 'Nomina')], limit=1)

    def _accounting_defaults_vals(self):
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
        # Multiple loans per employee allowed (Option A, v1.66.0).
        # ohrms_loan.create() raises if employee already has an approved loan
        # with balance_amount > 0. We assign the sequence ourselves and skip
        # past ohrms_loan in the MRO so that constraint never runs.
        if not vals.get('name') or vals['name'] == 'New':
            vals['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
        ohrms_cls = next(
            (cls for cls in type(self).__mro__
             if cls.__name__ == 'HrLoan' and 'ohrms_loan' in (cls.__module__ or '')),
            None
        )
        if ohrms_cls:
            record = super(ohrms_cls, self).create(vals)
        else:
            record = super().create(vals)
        defaults = record._accounting_defaults_vals()
        if defaults:
            record.write(defaults)
        return record

    # ── button actions ─────────────────────────────────────────────────────

    def action_fill_accounting_defaults(self):
        defaults = self._accounting_defaults_vals()
        if defaults:
            self.write(defaults)

    def action_view_journal_entry(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asiento Contable',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_send_advance_notification(self):
        """Generate ack token and send the loan advance notification email directly.

        Follows the same pattern as payslip batch: template.send_mail(id, force_send=True).
        This ensures QWeb renders correctly against the loan record.
        """
        self.ensure_one()
        if not self.employee_id.work_email:
            raise UserError(
                'El empleado %s no tiene correo electrónico de trabajo configurado.'
                % self.employee_id.name)
        if not self.loan_ack_token:
            self.loan_ack_token = str(uuid.uuid4())
        template = self.env.ref(
            'ueipab_payroll_enhancements.email_template_loan_advance',
            raise_if_not_found=False)
        if not template:
            raise UserError(
                'Plantilla "Adelanto de Salario" no encontrada. '
                'Verifique que el módulo esté actualizado.')
        template.send_mail(
            self.id,
            force_send=True,
            email_values={'email_to': self.employee_id.work_email},
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Notificación enviada',
                'message': 'Correo enviado a %s (%s).' % (
                    self.employee_id.name, self.employee_id.work_email),
                'type': 'success',
                'sticky': False,
            },
        }

    # ── onchanges ──────────────────────────────────────────────────────────

    @api.onchange('advance_bs_amount', 'advance_exchange_rate')
    def _onchange_bs_fields(self):
        """Bs amount or rate changed → recalculate USD loan_amount."""
        if self.advance_bs_amount and self.advance_exchange_rate:
            self.loan_amount = round(
                self.advance_bs_amount / self.advance_exchange_rate, 2)

    @api.onchange('loan_amount')
    def _onchange_loan_amount(self):
        """USD loan_amount entered directly → compute Bs equivalent."""
        if self.loan_amount and self.advance_exchange_rate:
            self.advance_bs_amount = round(
                self.loan_amount * self.advance_exchange_rate, 2)

    @api.onchange('employee_id')
    def _onchange_employee_accounting_defaults(self):
        if not self.employee_id:
            return
        defaults = self._accounting_defaults_vals()
        for fname, val in defaults.items():
            setattr(self, fname, val)

    @api.onchange('date')
    def _onchange_date_rate(self):
        """Date changed → fetch the BCV rate on or before that date."""
        rate = self._get_veb_rate(for_date=self.date)
        if rate:
            self.advance_exchange_rate = rate

    # ── approval ───────────────────────────────────────────────────────────

    def action_approve(self):
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
        emp_receivable = self.env['account.account'].search(
            [('code', '=', '1.1.06.01.001')], limit=1)
        if not emp_receivable:
            return

        # work_contact_id is the employee's own partner (Odoo 17).
        # address_id is typically the company address — do NOT use it for employee entries.
        work_contact = getattr(self.employee_id, 'work_contact_id', False)
        partner_id = work_contact.id if work_contact else False

        amount = self.loan_amount
        entry_date = self.date or dt.today()
        label = 'Anticipo Salarial – %s' % self.employee_id.name

        def _line(account_id, debit, credit):
            return (0, 0, {
                'name': label,
                'partner_id': partner_id,
                'account_id': account_id,
                'journal_id': self.journal_id.id,
                'date': entry_date,
                'debit': debit,
                'credit': credit,
            })

        move = self.env['account.move'].create({
            'narration': label,
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'date': entry_date,
            'line_ids': [
                _line(emp_receivable.id, amount, 0.0),
                _line(self.treasury_account_id.id, 0.0, amount),
            ],
        })
        move.action_post()
        self.move_id = move


class HrLoanLine(models.Model):
    _inherit = 'hr.loan.line'

    def action_paid_amount(self, month):
        # ohrms_loan_accounting would create a LOAN/ journal entry here with name
        # 'LOAN/ {employee}/{month-year}' — non-unique when same employee has two loans
        # cleared in the same calendar month.  VE_LOAN_DED_V2 / LIQUID_LOAN_DED_V2
        # salary rules already post DR/CR via the standard PAY1 payroll entry,
        # so this duplicate entry is both redundant and a naming-conflict blocker.
        return True


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        # super() → ohrms_loan marks all input lines that have loan_line_id as paid=True.
        # We then revert lines where HR set amount=0 (skip this loan this period)
        # and write the payslip reference back for lines that were genuinely paid.
        res = super().action_payslip_done()
        for payslip in self:
            for line in payslip.input_line_ids:
                if not line.loan_line_id:
                    continue
                if line.amount <= 0:
                    # HR opted to skip this loan — undo ohrms_loan's paid=True
                    line.loan_line_id.write({'paid': False})
                    line.loan_line_id.loan_id._compute_total_amount()
                else:
                    line.loan_line_id.write({'payslip_id': payslip.id})
        return res

    def get_inputs(self, contracts, date_from, date_to):
        # Get all non-LO inputs from the parent chain
        res = super().get_inputs(contracts, date_from, date_to)
        # Remove LO entries — ohrms_loan last-wins is replaced by one entry per loan
        res = [r for r in res if r.get('code') != 'LO']

        struct_code = self.struct_id.code if self.struct_id else ''
        if struct_code == 'LIQUID_VE_V2':
            target_type = 'liquidacion'
        elif struct_code == 'VE_PAYROLL_V2':
            target_type = 'quincena'
        else:
            return res

        employee = contracts[0].employee_id if contracts else self.employee_id
        active_loans = self.env['hr.loan'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'approve'),
            ('balance_amount', '>', 0),
            ('recovery_type', '=', target_type),
        ])

        for loan in active_loans:
            # Earliest unpaid installment with date <= payslip end (handles skipped periods)
            installment = loan.loan_lines.filtered(
                lambda l: not l.paid and l.date <= date_to
            ).sorted('date')
            if not installment:
                continue
            installment = installment[0]
            res.append({
                'name': 'Loan Recovery',
                'code': 'LO',
                'contract_id': contracts[0].id if contracts else False,
                'amount': installment.amount,
                'loan_line_id': installment.id,
            })

        return res
