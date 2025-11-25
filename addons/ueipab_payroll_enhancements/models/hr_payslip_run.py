# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _inherit = ['hr.payslip.run', 'mail.thread']

    currency_id = fields.Many2one('res.currency', compute='_compute_total_net_amount_details', string='Currency')
    total_net_amount = fields.Monetary(compute='_compute_total_net_amount_details', string='Total Net Payable', currency_field='currency_id')
    exchange_rate = fields.Float(
        string='Exchange Rate',
        compute='_compute_exchange_rate',
        store=True,
        readonly=False,
        help='VEB/USD exchange rate. Auto-populated from latest rate but can be manually overridden.'
    )

    # Email template selector for batch sending
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'hr.payslip')]",
        default=lambda self: self.env.ref('ueipab_payroll_enhancements.email_template_edi_payslip_compact', raise_if_not_found=False),
        help='Select which email template to use when sending payslips to employees'
    )

    # Override to bypass hr_payroll_community exchange rate gating
    # We use our own simpler exchange_rate field for VEB rate tracking
    exchange_rate_confirmed = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-confirm exchange rate (bypasses hr_payroll_community gating)."""
        for vals in vals_list:
            vals['exchange_rate_confirmed'] = True
        return super().create(vals_list)

    def _compute_can_generate_payslips(self):
        """Override to always allow payslip generation (bypasses hr_payroll_community gating).

        The base hr_payroll_community requires both batch_exchange_rate > 0 AND exchange_rate_confirmed.
        We use our own exchange_rate field, so we override this to always allow generation.
        """
        for record in self:
            record.can_generate_payslips = True

    @api.depends('date_end')
    def _compute_exchange_rate(self):
        """Auto-populate exchange rate from latest VEB rate for the batch end date."""
        veb_currency = self.env['res.currency'].search([('name', '=', 'VEB')], limit=1)
        for record in self:
            if veb_currency:
                # Get rate for batch end date (or today if not set)
                rate_date = record.date_end or fields.Date.today()
                rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', veb_currency.id),
                    ('name', '<=', rate_date),
                ], order='name desc', limit=1)
                if rate:
                    record.exchange_rate = rate.company_rate
                else:
                    record.exchange_rate = 1.0
            else:
                record.exchange_rate = 1.0

    @api.depends('slip_ids', 'slip_ids.line_ids.total', 'slip_ids.state')
    def _compute_total_net_amount_details(self):
        for record in self:
            total = 0.0
            # Fallback to company currency if no slips are available
            currency = self.env.company.currency_id
            # Include both draft and done payslips (exclude only cancelled)
            for payslip in record.slip_ids.filtered(lambda p: p.state in ('draft', 'done', 'verify')):
                # Support both standard NET and Venezuelan V2 net codes
                net_line = payslip.line_ids.filtered(lambda l: l.code in ('NET', 'VE_NET_V2'))
                if net_line:
                    total += sum(net_line.mapped('total'))
                    if not currency and payslip.currency_id:
                        currency = payslip.currency_id

            record.total_net_amount = total
            record.currency_id = currency


    def action_send_batch_emails(self):
        self.ensure_one()
        if not self.slip_ids:
            raise UserError(_("There are no payslips in this batch to send."))

        # Use selected template or fallback to default
        template = self.email_template_id
        if not template:
            template = self.env.ref('ueipab_payroll_enhancements.email_template_edi_payslip_compact', raise_if_not_found=False)

        if not template:
            raise UserError(_("Please select an email template or update the module to restore default templates."))

        sent_count = 0
        for slip in self.slip_ids:
            if slip.employee_id.work_email:
                template.send_mail(slip.id, force_send=True, email_values={'email_to': slip.employee_id.work_email})
                sent_count += 1

        self.message_post(body=_("Payslips sent by email to %s employees using template '%s'.") % (sent_count, template.name))
        return True

    def action_cancel(self):
        """Cancels the payslip batch and all associated payslips."""
        self.ensure_one()
        # Set batch state to cancel
        self.state = 'cancel'
        # Set all associated payslips to cancel
        self.slip_ids.write({'state': 'cancel'})
        self.message_post(body=_("Payslip batch and associated payslips cancelled."))
        return True

    def action_draft(self):
        """Sets the payslip batch and all associated payslips to draft."""
        self.ensure_one()
        # Set batch state to draft
        self.state = 'draft'
        # Set all associated payslips to draft
        self.slip_ids.write({'state': 'draft'})
        self.message_post(body=_("Payslip batch and associated payslips set to draft."))
        return True

    def action_apply_exchange_rate(self):
        """Applies the batch's exchange rate to all payslips in the batch.

        This updates the exchange_rate_used field on all payslips, overriding
        any previously set rate (including hardcoded defaults from hr_payroll_community).
        """
        self.ensure_one()
        if not self.exchange_rate or self.exchange_rate <= 0:
            raise UserError(_("Please set a valid exchange rate (greater than 0) on the batch."))

        if not self.slip_ids:
            raise UserError(_("There are no payslips in this batch to update."))

        # Apply exchange rate to ALL payslips in the batch
        self.slip_ids.write({
            'exchange_rate_used': self.exchange_rate,
            'exchange_rate_date': fields.Datetime.now()
        })

        # Post a confirmation message with the rate details
        payslip_count = len(self.slip_ids)
        total_net_veb = self.total_net_amount * self.exchange_rate if self.total_net_amount else 0.0

        self.message_post(body=_(
            "Exchange rate applied to %s payslips: %.4f VEB/USD<br/>"
            "Batch total: $%.2f USD = Bs. %.2f VEB"
        ) % (payslip_count, self.exchange_rate, self.total_net_amount or 0, total_net_veb))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Exchange Rate Applied'),
                'message': _('Exchange rate %.4f VEB/USD applied to %s payslips.') % (self.exchange_rate, payslip_count),
                'type': 'success',
                'sticky': False,
            }
        }