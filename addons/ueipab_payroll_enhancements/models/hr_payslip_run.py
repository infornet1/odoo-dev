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

from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    @api.depends('slip_ids', 'slip_ids.state', 'slip_ids.line_ids', 'slip_ids.line_ids.total')
    def _compute_total_net_amount(self):
        """Calculate total net payable for all payslips in batch.

        Business Logic:
            - Only includes payslips in 'done' or 'paid' state
            - Sums the NET salary rule line from each payslip (VE_NET or VE_NET_V2)
            - Ignores cancelled or draft payslips
            - Updates automatically when payslips change

        Technical Implementation:
            - Uses @api.depends for automatic recomputation
            - Stored in database for performance (store=True)
            - Filters payslips by state before calculation
        """
        for batch in self:
            # Get all confirmed payslips (not draft or cancelled)
            valid_slips = batch.slip_ids.filtered(
                lambda s: s.state in ('done', 'paid')
            )

            # Sum the NET line from each payslip
            total = 0.0
            for slip in valid_slips:
                # Find the NET salary rule line (supports V1: VE_NET and V2: VE_NET_V2)
                net_line = slip.line_ids.filtered(
                    lambda l: l.salary_rule_id.code in ('VE_NET', 'VE_NET_V2')
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
                first_slip = batch.slip_ids.sorted(lambda s: s.id)[0]
                batch.exchange_rate = first_slip.exchange_rate_used or 0.0
            else:
                # No payslips yet
                batch.exchange_rate = 0.0

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

        self.message_post(
            body=_("Payslips sent by email to %s employees using template '%s'.") % (
                sent_count, template.name
            )
        )
        return True

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
        """Sync batch date range to all payslips in the batch.

        Business Use Case:
            - User changes batch date_start or date_end after payslips are created
            - Clicks "Sync Dates to Payslips" button
            - All payslips in batch get updated with batch dates
            - Ensures consistency between batch and payslip date ranges

        Business Logic:
            - Updates date_from and date_to on all payslips in batch
            - Only works on draft payslips (confirmed payslips should not be changed)
            - Shows warning if some payslips are not draft

        Technical Implementation:
            - Batch write operation (efficient)
            - Shows confirmation with count of updated payslips
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

            # Build message
            message = _('%d payslip(s) updated with dates %s to %s') % (
                len(draft_slips),
                batch.date_start.strftime('%Y-%m-%d'),
                batch.date_end.strftime('%Y-%m-%d')
            )

            if non_draft_slips:
                message += _('\n\nNote: %d non-draft payslip(s) were skipped.') % len(non_draft_slips)

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Dates Synchronized'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
