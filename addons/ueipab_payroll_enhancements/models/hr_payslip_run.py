# -*- coding: utf-8 -*-
"""
UEIPAB Payroll Enhancements - Payslip Batch (Run) Extensions

This module extends hr.payslip.run with computed fields and enhancements
for better financial control and visibility.

Enhancements:
    1. Total Net Amount: Computed field showing sum of all employee net pay
    2. Print Disbursement List: ICF-compliant PDF report for finance approval
    3. Cancel Workflow: Cancel batches instead of deleting (audit trail policy)
"""

import calendar
import logging
import re
from datetime import date as date_type, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrPayslipRun(models.Model):
    """Extend hr.payslip.run with total net amount calculation and cancel workflow."""

    _inherit = 'hr.payslip.run'

    # ========================================
    # FIELDS
    # ========================================

    # Extend state selection to add 'cancel'
    state = fields.Selection(
        selection_add=[('cancel', 'Cancelled')],
        ondelete={'cancel': 'set default'},
        help="Status for Payslip Batches. "
             "Cancelled batches preserve audit trail without deletion."
    )

    total_net_amount = fields.Monetary(
        string='Total Net Payable',
        compute='_compute_total_net_amount',
        store=True,
        currency_field='currency_id',
        help='Sum of all employee net payments in this batch. '
             'Only includes confirmed payslips (done/paid state).'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
        help='Currency for total net amount display'
    )

    exchange_rate = fields.Float(
        string='Exchange Rate (VEB/USD)',
        digits=(12, 6),
        compute='_compute_exchange_rate',
        store=True,
        readonly=False,
        help='Exchange rate (VEB per USD) used for payslips in this batch. '
             'This rate is used to convert USD amounts to Venezuelan Bolívares in reports. '
             'You can manually adjust this rate and apply it to all payslips using the '
             '"Apply to Payslips" button.'
    )

    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'hr.payslip')]",
        default=lambda self: self._default_email_template(),
        help='Select email template to use when sending payslips by email. '
             'Available templates: Payslip Compact Report, Payslip Email - Employee Delivery, etc.'
    )

    # ========================================
    # ADVANCE PAYMENT FIELDS
    # ========================================

    is_advance_payment = fields.Boolean(
        string='Es Pago Adelanto',
        default=False,
        help='Marcar si este lote es un pago adelanto parcial del salario. '
             'Cuando está activo, se pagará solo el porcentaje indicado del neto.'
    )

    advance_percentage = fields.Float(
        string='Porcentaje Adelanto (%)',
        digits=(5, 2),
        default=100.0,
        help='Porcentaje del salario neto a pagar como adelanto. '
             'Ejemplo: 50.0 = 50% del neto total.'
    )

    advance_total_amount = fields.Monetary(
        string='Total Adelanto',
        compute='_compute_advance_total_amount',
        store=True,
        currency_field='currency_id',
        help='Monto total a desembolsar (total neto × porcentaje adelanto).'
    )

    # ========================================
    # DATE CHECK FIELDS
    # ========================================

    date_check_acknowledged = fields.Boolean(
        string='Date Check Acknowledged',
        default=False,
        help='Set when user has reviewed and acknowledged date logic warnings.',
    )

    # ========================================
    # REMAINDER PAYMENT FIELDS
    # ========================================

    is_remainder_batch = fields.Boolean(
        string='Es Pago Restante',
        default=False,
        help='Marcar si este lote es el pago restante de un adelanto previo. '
             'Permite vincular con el lote de adelanto original para conciliación.'
    )

    advance_batch_id = fields.Many2one(
        'hr.payslip.run',
        string='Lote Adelanto Original',
        domain="[('is_advance_payment', '=', True), ('id', '!=', id)]",
        help='Seleccione el lote de adelanto original al que corresponde este pago restante. '
             'Se usará para mostrar la conciliación completa en el correo al empleado.'
    )

    # ========================================
    # ONCHANGE METHODS
    # ========================================

    @api.onchange('is_remainder_batch', 'advance_batch_id')
    def _onchange_remainder_batch(self):
        """Auto-calculate remaining percentage when linking to advance batch.

        Business Logic:
            - When user checks 'Es Pago Restante' and selects an advance batch
            - System automatically calculates: remaining% = 100% - advance%
            - Example: If advance batch was 50%, remainder is set to 50%
            - This ensures email templates calculate amounts correctly

        User Flow:
            1. User creates new batch (e.g., DICIEMBRE31.2)
            2. User checks 'Es Pago Restante'
            3. User selects 'DICIEMBRE31' (50% advance) from dropdown
            4. System automatically sets advance_percentage = 50 (100 - 50)

        Technical Implementation:
            - Triggers on change of is_remainder_batch or advance_batch_id
            - Reads advance_percentage from linked advance batch
            - Sets this batch's advance_percentage to the remaining amount
        """
        if self.is_remainder_batch and self.advance_batch_id:
            # Calculate remaining percentage: 100% - advance%
            advance_pct = self.advance_batch_id.advance_percentage or 0
            self.advance_percentage = 100.0 - advance_pct
        elif not self.is_remainder_batch:
            # Reset to default when unchecking remainder batch
            self.advance_percentage = 100.0

    @api.onchange('is_advance_payment')
    def _onchange_is_advance_payment(self):
        """Auto-select email template based on advance payment flag."""
        if self.is_advance_payment:
            template = self.env['mail.template'].search([
                ('name', '=', 'Payslip Email - Advance Payment - Employee Delivery'),
                ('model', '=', 'hr.payslip')
            ], limit=1)
        else:
            template = self.env['mail.template'].search([
                ('name', '=', 'Payslip Email - Employee Delivery'),
                ('model', '=', 'hr.payslip')
            ], limit=1)
        if template:
            self.email_template_id = template

    def _default_email_template(self):
        """Return default email template: 'Payslip Email - Employee Delivery'"""
        template = self.env['mail.template'].search([
            ('name', '=', 'Payslip Email - Employee Delivery'),
            ('model', '=', 'hr.payslip')
        ], limit=1)
        return template.id if template else False

    @api.depends('slip_ids', 'slip_ids.state', 'slip_ids.line_ids', 'slip_ids.line_ids.total')
    def _compute_total_net_amount(self):
        """Calculate total net payable for all payslips in batch.

        Business Logic:
            - Includes payslips in 'draft', 'done', or 'paid' state
            - Sums the NET salary rule line from each payslip (VE_NET or VE_NET_V2)
            - Critical for validation before confirming batch
            - Excludes only cancelled payslips
            - Updates automatically when payslips change

        Technical Implementation:
            - Uses @api.depends for automatic recomputation
            - Stored in database for performance (store=True)
            - Filters out cancelled payslips only
        """
        for batch in self:
            # Get all payslips except cancelled ones (include draft for pre-validation)
            valid_slips = batch.slip_ids.filtered(
                lambda s: s.state != 'cancel'
            )

            # Sum the NET line from each payslip
            total = 0.0
            for slip in valid_slips:
                # Find the NET salary rule line (supports V1: VE_NET, V2: VE_NET_V2, and AGUINALDOS)
                net_line = slip.line_ids.filtered(
                    lambda l: l.salary_rule_id.code in ('VE_NET', 'VE_NET_V2', 'AGUINALDOS')
                )
                if net_line:
                    # Should only be one NET line per payslip
                    total += net_line[0].total

            batch.total_net_amount = total

    @api.depends('slip_ids.exchange_rate_used')
    def _compute_exchange_rate(self):
        """Compute exchange rate from payslips.

        Business Logic:
            - Auto-populates from first payslip's exchange_rate_used
            - If all payslips have same rate, shows that rate
            - If no payslips, shows 0.0
            - User can manually override this value

        Technical Implementation:
            - Computed field with store=True
            - readonly=False allows manual override
            - Used for batch-level awareness and bulk updates
        """
        for batch in self:
            if batch.slip_ids:
                # Get exchange rate from first payslip
                # Filter to only real records (with integer IDs) to avoid NewId sorting errors
                real_slips = batch.slip_ids.filtered(lambda s: isinstance(s.id, int))
                if real_slips:
                    first_slip = real_slips.sorted(lambda s: s.id)[0]
                else:
                    # Fallback to first slip if all are unsaved
                    first_slip = batch.slip_ids[0]
                batch.exchange_rate = first_slip.exchange_rate_used or 0.0
            else:
                # No payslips yet
                batch.exchange_rate = 0.0

    @api.depends('total_net_amount', 'is_advance_payment')
    def _compute_advance_total_amount(self):
        """Compute total advance amount to disburse.

        Business Logic:
            - Since salary rules already apply the advance percentage multiplier,
              total_net_amount is already the reduced advance amount.
            - advance_total_amount = total_net_amount (for display consistency)
            - Used for financial planning and disbursement reports

        Technical Implementation:
            - Depends on total_net_amount (which already has % applied via salary rules)
            - Stored for reporting performance
        """
        for batch in self:
            # total_net_amount already has advance % applied via salary rules
            batch.advance_total_amount = batch.total_net_amount

    # ========================================
    # WRITE OVERRIDE
    # ========================================

    def write(self, vals):
        if 'date_start' in vals or 'date_end' in vals:
            vals['date_check_acknowledged'] = False
        return super().write(vals)

    # ========================================
    # DATE LOGIC VALIDATION
    # ========================================

    _MONTH_MAP = {
        'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
        'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
        'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12,
    }
    _MONTH_ES = {v: k for k, v in _MONTH_MAP.items()}
    _REGULAR_STRUCTS = ('NOMINA_VE', 'NOMINA_VE_V2')

    def _get_payroll_sequence_month(self):
        """Return (year, month) of the latest posted entry in the payroll journal, or None.

        Queries account_move for the highest sequence name in the journal used by
        this batch's payslips (e.g. PAY1/2026/04/0024 → (2026, 4)).
        Returns None if no entries found or name pattern does not match.
        """
        self.ensure_one()
        slips_with_journal = self.slip_ids.filtered(lambda s: s.journal_id)
        if not slips_with_journal:
            return None
        journal = slips_with_journal[0].journal_id

        last_move = self.env['account.move'].search([
            ('journal_id', '=', journal.id),
            ('state', '=', 'posted'),
            ('name', '!=', '/'),
        ], order='name desc', limit=1)

        if not last_move or not last_move.name:
            return None

        m = re.match(r'^[^/]+/(\d{4})/(\d{2})/', last_move.name)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    def _get_seq_fix_date(self):
        """Return suggested accounting date to resolve a PAY1 sequence conflict, or None.

        Returns the first day of the sequence month when the journal sequence has
        already advanced beyond the batch's period-end month.  Returns None when
        there is no conflict (no adjustment needed).
        """
        seq_info = self._get_payroll_sequence_month()
        if not seq_info or not self.date_end:
            return None
        seq_year, seq_month = seq_info
        if (seq_year, seq_month) > (self.date_end.year, self.date_end.month):
            return date_type(seq_year, seq_month, 1)
        return None

    # ========================================
    # VALIDATE OVERRIDE — sequence auto-fix
    # ========================================

    def action_validate_payslips(self):
        """Override to silently fix PAY1 sequence/date conflicts before confirming.

        Safety-net layer: if the date-check wizard was bypassed (e.g. user
        acknowledged without fixing), auto-set slip.date to the first day of
        the sequence month so Odoo's sequence/date validation does not block
        confirmation.  Logs the adjustment; no popup is shown.
        """
        for batch in self:
            seq_fix_date = batch._get_seq_fix_date()
            if not seq_fix_date:
                continue
            draft_slips = batch.slip_ids.filtered(lambda s: s.state == 'draft')
            slips_to_fix = [
                s for s in draft_slips
                if not s.date
                or (s.date.year, s.date.month) < (seq_fix_date.year, seq_fix_date.month)
            ]
            if slips_to_fix:
                for slip in slips_to_fix:
                    slip.date = seq_fix_date
                _logger.info(
                    'PAY1 sequence auto-fix: set accounting date to %s on %d payslip(s) in batch "%s"',
                    seq_fix_date, len(slips_to_fix), batch.name,
                )
        return super().action_validate_payslips()

    def _collect_date_issues(self):
        """Run all date validation checks. Returns list of issue dicts."""
        self.ensure_one()
        issues = []

        if not self.date_start or not self.date_end or not self.slip_ids:
            return issues

        batch_start = self.date_start
        batch_end = self.date_end
        batch_slip_ids = self.slip_ids.ids

        # ---- Check 1: Overlap with existing confirmed payslips ----
        for slip in self.slip_ids:
            if not slip.employee_id or not slip.struct_id:
                continue
            overlapping = self.env['hr.payslip'].search([
                ('id', 'not in', batch_slip_ids),
                ('employee_id', '=', slip.employee_id.id),
                ('struct_id', '=', slip.struct_id.id),
                ('state', 'in', ['done', 'paid']),
                ('date_from', '<=', fields.Date.to_string(batch_end)),
                ('date_to', '>=', fields.Date.to_string(batch_start)),
            ])
            for ov in overlapping:
                issues.append({
                    'severity': 'blocker',
                    'employee_name': slip.employee_id.name,
                    'description': 'Overlaps with confirmed payslip %s' % (ov.number or ov.name),
                    'detail': '%s → %s (%s)' % (ov.date_from, ov.date_to, ov.struct_id.name),
                })

        # ---- Check 2: Gap from expected next period (per employee+struct) ----
        seen = set()
        for slip in self.slip_ids:
            if not slip.employee_id or not slip.struct_id:
                continue
            key = (slip.employee_id.id, slip.struct_id.id)
            if key in seen:
                continue
            seen.add(key)
            last = self.env['hr.payslip'].search([
                ('id', 'not in', batch_slip_ids),
                ('employee_id', '=', slip.employee_id.id),
                ('struct_id', '=', slip.struct_id.id),
                ('state', 'in', ['done', 'paid']),
            ], order='date_to desc', limit=1)
            if not last:
                continue
            expected_start = last.date_to + timedelta(days=1)
            gap = (batch_start - expected_start).days
            if gap > 1:
                issues.append({
                    'severity': 'warning',
                    'employee_name': slip.employee_id.name,
                    'description': 'Gap of %d day(s) since last payslip' % gap,
                    'detail': 'Last ended %s → expected start %s, batch starts %s' % (
                        last.date_to, expected_start, batch_start
                    ),
                })

        # ---- Check 3: Quincena alignment (only for regular payroll structures) ----
        regular_slips = self.slip_ids.filtered(
            lambda s: s.struct_id and s.struct_id.code in self._REGULAR_STRUCTS
        )
        if regular_slips:
            last_day = calendar.monthrange(batch_end.year, batch_end.month)[1]
            is_q1 = (batch_start.day == 1 and batch_end.day == 15
                     and batch_start.month == batch_end.month)
            is_q2 = (batch_start.day == 16 and batch_end.day == last_day
                     and batch_start.month == batch_end.month)
            if not is_q1 and not is_q2:
                issues.append({
                    'severity': 'warning',
                    'employee_name': '',
                    'description': 'Dates do not match standard quincena periods',
                    'detail': '%s → %s is not 1-15 or 16-%d of the same month' % (
                        batch_start, batch_end, last_day
                    ),
                })

        # ---- Check 4: Batch name vs date month ----
        name_upper = (self.name or '').upper()
        name_month = next(
            (num for word, num in self._MONTH_MAP.items() if word in name_upper), None
        )
        if name_month and name_month != batch_start.month:
            issues.append({
                'severity': 'info',
                'employee_name': '',
                'description': 'Batch name suggests %s but dates are in %s' % (
                    self._MONTH_ES.get(name_month, str(name_month)),
                    self._MONTH_ES.get(batch_start.month, str(batch_start.month)),
                ),
                'detail': 'Name: "%s" | Dates: %s → %s' % (self.name, batch_start, batch_end),
            })

        # ---- Check 5: PAY1 journal sequence / accounting date conflict ----
        seq_fix_date = self._get_seq_fix_date()
        if seq_fix_date:
            issues.append({
                'severity': 'info',
                'employee_name': '',
                'description': 'PAY1 sequence is already in %s — accounting dates need adjustment' % (
                    seq_fix_date.strftime('%B %Y')
                ),
                'detail': (
                    'Payslip period ends %s but PAY1 journal sequence is already at %02d/%d. '
                    'Click "Auto-fix Accounting Dates" to set payslip accounting dates to %s '
                    '(or validate — the system will adjust automatically).'
                ) % (batch_end, seq_fix_date.month, seq_fix_date.year, seq_fix_date),
                'seq_fix_date': seq_fix_date,
            })

        return issues

    def _open_date_check_wizard(self, issues, sync_done=False):
        """Create and return wizard action for the given issues."""
        has_blocker = any(i['severity'] == 'blocker' for i in issues)
        _cls = {'blocker': 'danger', 'warning': 'warning', 'info': 'info'}
        _lbl = {'blocker': 'Blocker', 'warning': 'Warning', 'info': 'Info'}
        _ord = {'blocker': 0, 'warning': 1, 'info': 2}
        rows = ''.join(
            '<tr>'
            '<td><span class="badge text-bg-{cls}">{lbl}</span></td>'
            '<td>{emp}</td>'
            '<td>{desc}</td>'
            '<td><small class="text-muted">{detail}</small></td>'
            '</tr>'.format(
                cls=_cls[i['severity']],
                lbl=_lbl[i['severity']],
                emp=i.get('employee_name') or '—',
                desc=i['description'],
                detail=i.get('detail', ''),
            )
            for i in sorted(issues, key=lambda x: _ord[x['severity']])
        )
        html = (
            '<table class="table table-sm table-bordered">'
            '<thead><tr>'
            '<th style="width:100px">Severity</th>'
            '<th>Employee</th><th>Issue</th><th>Detail</th>'
            '</tr></thead>'
            '<tbody>%s</tbody></table>' % rows
        )
        seq_fix_date = next(
            (i['seq_fix_date'] for i in issues if i.get('seq_fix_date')), None
        )
        wizard = self.env['hr.payslip.run.date.check.wizard'].create({
            'run_id': self.id,
            'sync_done': sync_done,
            'has_blocker': has_blocker,
            'issues_html': html,
            'seq_fix_date': seq_fix_date,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Date Logic Issues — %s') % self.name,
            'res_model': 'hr.payslip.run.date.check.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_check_date_logic(self):
        """Manually run date logic checks and show results."""
        self.ensure_one()
        if not self.slip_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Payslips'),
                    'message': _('Add payslips to the batch before running date checks.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        issues = self._collect_date_issues()
        if not issues:
            self.date_check_acknowledged = True
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('All Checks Passed'),
                    'message': _('No date logic issues found for batch %s.') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        return self._open_date_check_wizard(issues)

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def action_send_batch_emails(self):
        """Send individual payslips to each employee via email.

        Business Use Case:
            - User creates/confirms payslips in a batch
            - User selects email template (or uses default)
            - Clicks "Send Payslips by Email" button
            - All employees with work_email receive their payslip

        Technical Implementation:
            - Uses selected email_template_id or fallback to default
            - Sends mail using template.send_mail()
            - Posts message to batch chatter with count

        Returns:
            bool: True if emails sent successfully

        Raises:
            UserError: If no payslips in batch or no template selected
        """
        self.ensure_one()
        if not self.slip_ids:
            raise UserError(_("There are no payslips in this batch to send."))

        # Use selected template or fallback to default
        template = self.email_template_id
        if not template:
            template = self.env.ref(
                'ueipab_payroll_enhancements.email_template_edi_payslip_compact',
                raise_if_not_found=False
            )

        if not template:
            raise UserError(_(
                "Please select an email template or update the module to restore default templates."
            ))

        sent_count = 0
        for slip in self.slip_ids:
            if slip.employee_id.work_email:
                template.send_mail(
                    slip.id,
                    force_send=True,
                    email_values={'email_to': slip.employee_id.work_email}
                )
                sent_count += 1

        # Return success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Emails Sent'),
                'message': _("Payslips sent by email to %s employees using template '%s'.") % (
                    sent_count, template.name
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Cancel the payslip batch and all associated payslips.

        Business Policy:
            - Never delete records, only cancel them for audit trail
            - Cancelled batches can be reopened with action_draft
            - All associated payslips are also cancelled
            - All associated journal entries are also cancelled

        Technical Implementation:
            - Sets batch state to 'cancel'
            - Calls action_payslip_cancel on all associated payslips
            - Payslip cancellation automatically handles journal entries:
              * Posted entries are reset to draft via button_draft()
              * Then cancelled via button_cancel()
              * Batch operation handles multiple entries efficiently
              * Preserves audit trail (no deletion)

        Raises:
            UserError: If batch is already cancelled
        """
        for batch in self:
            # Validate batch can be cancelled
            if batch.state == 'cancel':
                raise UserError(
                    _('This batch is already cancelled.')
                )

            # Cancel all associated payslips
            # Note: action_payslip_cancel() automatically handles posted journal entries
            # via button_cancel(), which resets them to draft then cancels them.
            payslips_to_cancel = batch.slip_ids.filtered(
                lambda s: s.state not in ('cancel', 'draft')
            )
            if payslips_to_cancel:
                payslips_to_cancel.action_payslip_cancel()

            # Cancel the batch
            batch.state = 'cancel'

        return True

    def action_draft(self):
        """Set cancelled batch back to draft state.

        Business Logic:
            - Allows reopening cancelled batches
            - Does NOT automatically reopen cancelled payslips
            - User must manually reopen payslips if needed

        Technical Implementation:
            - Sets batch state to 'draft'
            - Only works on cancelled batches

        Raises:
            UserError: If batch is not cancelled
        """
        for batch in self:
            if batch.state != 'cancel':
                raise UserError(
                    _('Only cancelled batches can be set to draft. '
                      'Current state: %s') % dict(batch._fields['state'].selection).get(batch.state)
                )

            batch.state = 'draft'

        return True

    def action_apply_exchange_rate(self):
        """Apply batch exchange rate to all payslips.

        Business Use Case:
            - Market exchange rate changes after payslips are calculated
            - User updates batch exchange_rate field
            - Clicks "Apply to Payslips" button
            - All payslips in batch get updated with new rate
            - Batch operation (one click instead of 44 individual edits)

        Business Logic:
            - Updates exchange_rate_used on all payslips in batch
            - Works on payslips in any state (draft, done, paid, cancel)
            - Does NOT automatically recalculate payslips
            - User must manually recalculate if needed

        Technical Implementation:
            - Batch write operation (efficient)
            - Shows confirmation with count of updated payslips
            - Returns action to refresh view

        Returns:
            dict: Action to show success message and refresh view
        """
        for batch in self:
            if not batch.exchange_rate:
                raise UserError(
                    _('Please enter an exchange rate before applying to payslips.')
                )

            if not batch.slip_ids:
                raise UserError(
                    _('No payslips found in this batch.')
                )

            # Count payslips to update
            payslip_count = len(batch.slip_ids)

            # Update all payslips with batch exchange rate
            batch.slip_ids.write({
                'exchange_rate_used': batch.exchange_rate,
                'exchange_rate_date': fields.Datetime.now(),
            })

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Exchange Rate Applied'),
                    'message': _('%d payslip(s) updated with exchange rate %.6f VEB/USD') % (
                        payslip_count,
                        batch.exchange_rate
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_sync_dates_to_payslips(self):
        """Sync batch date range to all payslips in the batch and recompute.

        Business Use Case:
            - User changes batch date_start or date_end after payslips are created
            - Clicks "Sync Dates to Payslips" button
            - All payslips in batch get updated with batch dates
            - Payslips are automatically recomputed with new dates
            - Ensures consistency between batch and payslip date ranges

        Business Logic:
            - Updates date_from and date_to on all draft payslips in batch
            - Automatically recomputes payslips after date update
            - Only works on draft payslips (confirmed payslips should not be changed)
            - Shows warning if some payslips are not draft

        Technical Implementation:
            - Batch write operation for dates (efficient)
            - Calls action_compute_sheet() on each payslip to recompute
            - Shows confirmation with count of updated/recomputed payslips
            - Returns action to refresh view

        Returns:
            dict: Action to show success message and refresh view
        """
        for batch in self:
            if not batch.date_start or not batch.date_end:
                raise UserError(
                    _('Please set both start and end dates on the batch before syncing.')
                )

            if not batch.slip_ids:
                raise UserError(
                    _('No payslips found in this batch.')
                )

            # Get draft payslips only
            draft_slips = batch.slip_ids.filtered(lambda s: s.state == 'draft')
            non_draft_slips = batch.slip_ids.filtered(lambda s: s.state != 'draft')

            if not draft_slips:
                raise UserError(
                    _('No draft payslips found. Only draft payslips can have their dates updated.\n'
                      'Found %d non-draft payslip(s).') % len(non_draft_slips)
                )

            # Update draft payslips with batch dates
            draft_slips.write({
                'date_from': batch.date_start,
                'date_to': batch.date_end,
            })

            # Recompute all updated payslips
            draft_slips.action_compute_sheet()

            # Build message
            message = _('%d payslip(s) updated with dates %s to %s and recomputed') % (
                len(draft_slips),
                batch.date_start.strftime('%Y-%m-%d'),
                batch.date_end.strftime('%Y-%m-%d')
            )

            if non_draft_slips:
                message += _('\n\nNote: %d non-draft payslip(s) were skipped.') % len(non_draft_slips)

            # Run date logic check — show wizard if issues, notification if clean
            issues = batch._collect_date_issues()
            if issues:
                return batch._open_date_check_wizard(issues, sync_done=True)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Dates Synchronized & Recomputed'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
