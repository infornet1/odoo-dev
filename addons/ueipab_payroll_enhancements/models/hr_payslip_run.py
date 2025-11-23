# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrPayslipRun(models.Model):
    _inherit = ['hr.payslip.run', 'mail.thread']

    currency_id = fields.Many2one('res.currency', compute='_compute_total_net_amount_details', string='Currency')
    total_net_amount = fields.Monetary(compute='_compute_total_net_amount_details', string='Total Net Payable', currency_field='currency_id')
    exchange_rate = fields.Float(string='Exchange Rate', default=1.0) # Added as referenced in XML

    @api.depends('slip_ids', 'slip_ids.line_ids.total')
    def _compute_total_net_amount_details(self):
        for record in self:
            total = 0.0
            # Fallback to company currency if no slips are available
            currency = self.env.company.currency_id
            for payslip in record.slip_ids.filtered(lambda p: p.state == 'done'):
                net_line = payslip.line_ids.filtered(lambda l: l.code == 'NET')
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

        template = self.env.ref('ueipab_payroll_enhancements.email_template_edi_payslip_compact', raise_if_not_found=False)
        if not template:
            raise UserError(_("The 'Payslip - Send by Email' template could not be found. Please update the module."))

        for slip in self.slip_ids:
            if slip.employee_id.work_email:
                template.send_mail(slip.id, force_send=True, email_values={'email_to': slip.employee_id.work_email})
        
        self.message_post(body=_("Payslips sent by email to employees."))
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
        """Applies the batch's exchange rate to all payslips in the batch."""
        self.ensure_one()
        if not self.exchange_rate or self.exchange_rate <= 0:
            raise UserError(_("Please set a valid exchange rate (greater than 0) on the batch."))

        # Assuming payslips have a field to store exchange rate
        # This will update all payslips in the batch with the batch's exchange rate
        self.slip_ids.write({'custom_exchange_rate': self.exchange_rate}) # Assuming 'custom_exchange_rate' exists on hr.payslip
        self.message_post(body=_("Exchange rate %s applied to all payslips in this batch.") % self.exchange_rate)
        return True