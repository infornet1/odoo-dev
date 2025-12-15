# -*- coding: utf-8 -*-
"""
UEIPAB Payroll Enhancements - Payslip Extensions

This module extends hr.payslip to maintain state integrity with parent batch.

Enhancement:
    - Prevents setting cancelled payslips to draft when batch is cancelled
    - Maintains parent-child state relationship
    - Follows business policy: batch state controls child payslip states
    - Employee acknowledgment system with portal link and token
"""

import base64
import uuid

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    """Extend hr.payslip with batch state control."""

    _inherit = 'hr.payslip'

    # ========================================
    # FIELDS
    # ========================================

    net_wage = fields.Monetary(
        compute='_compute_net_wage',
        string='Net Wage',
        currency_field='currency_id',
        store=True,
        help='Net amount of the payslip based on NET category lines.'
    )

    @api.depends('line_ids.total', 'line_ids.category_id')
    def _compute_net_wage(self):
        for payslip in self:
            net_total = 0.0
            for line in payslip.line_ids.filtered(lambda l: l.category_id.code == 'NET'):
                net_total += line.total
            payslip.net_wage = net_total

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True,
        store=True # Added store=True to make it accessible in @api.depends
    )

    payslip_run_state = fields.Selection(
        related='payslip_run_id.state',
        string='Batch Status',
        readonly=True,
        store=False,
        help='State of the parent payslip batch. '
             'Used to control button visibility and prevent state changes '
             'when batch is cancelled.'
    )

    # ========================================
    # EMPLOYEE ACKNOWLEDGMENT FIELDS
    # ========================================

    access_token = fields.Char(
        string='Access Token',
        copy=False,
        index=True,
        help='Unique token for secure portal access to acknowledge payslip.'
    )

    is_acknowledged = fields.Boolean(
        string='Acknowledged',
        default=False,
        copy=False,
        tracking=True,
        help='Indicates if employee has acknowledged receipt of this payslip.'
    )

    acknowledged_date = fields.Datetime(
        string='Acknowledged Date',
        copy=False,
        readonly=True,
        help='Date and time when employee acknowledged the payslip.'
    )

    acknowledged_ip = fields.Char(
        string='Acknowledged IP',
        copy=False,
        readonly=True,
        help='IP address from which the acknowledgment was made.'
    )

    acknowledged_user_agent = fields.Char(
        string='User Agent',
        copy=False,
        readonly=True,
        help='Browser/device information when acknowledgment was made.'
    )

    # ========================================
    # EMAIL TEMPLATE HELPER METHODS
    # ========================================

    def get_line_amount(self, code):
        """Get the amount of a payslip line by code.

        Used in email templates where lambda expressions don't work in QWeb.
        Returns the total amount for the line with the given code, or 0.0 if not found.

        Args:
            code: The salary rule code (e.g., 'VE_SALARY_V2', 'VE_SSO_DED_V2')

        Returns:
            float: The line total amount, or 0.0 if not found
        """
        self.ensure_one()
        for line in self.line_ids:
            if line.code == code:
                return line.total
        return 0.0

    # ========================================
    # ACKNOWLEDGMENT METHODS
    # ========================================

    def _generate_access_token(self):
        """Generate a unique access token for secure portal access."""
        for payslip in self:
            if not payslip.access_token:
                payslip.access_token = str(uuid.uuid4())
        return True

    def _get_acknowledgment_url(self):
        """Get the full URL for employee acknowledgment portal page.

        Includes database name parameter for multi-database environments.
        """
        self.ensure_one()
        if not self.access_token:
            self._generate_access_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        db_name = self.env.cr.dbname
        return f"{base_url}/payslip/acknowledge/{self.id}/{self.access_token}?db={db_name}"

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate access token for new payslips."""
        payslips = super().create(vals_list)
        for payslip in payslips:
            payslip._generate_access_token()
        return payslips

    def action_reset_acknowledgment(self):
        """Reset acknowledgment status (for HR use only)."""
        self.ensure_one()
        self.write({
            'is_acknowledged': False,
            'acknowledged_date': False,
            'acknowledged_ip': False,
            'acknowledged_user_agent': False,
        })
        self.message_post(body=_("Acknowledgment status reset by %s") % self.env.user.name)
        return True

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def action_payslip_draft(self):
        """Override to prevent setting to draft if batch is cancelled.

        Business Policy:
            - Individual payslips cannot be reopened when batch is cancelled
            - Maintains parent-child state integrity
            - User must reopen batch first, then reopen payslips

        Correct Workflow:
            1. If batch was cancelled by mistake: Reopen batch first
            2. Then individual payslips can be set to draft
            3. This maintains state consistency

        Technical Implementation:
            - Checks if payslip belongs to a batch
            - If batch exists and is cancelled, raises UserError
            - Otherwise, calls parent method normally

        Raises:
            UserError: If payslip belongs to a cancelled batch
        """
        for payslip in self:
            # Check if payslip belongs to a cancelled batch
            if payslip.payslip_run_id and payslip.payslip_run_id.state == 'cancel':
                raise UserError(
                    _('Cannot set payslip to draft.\n\n'
                      'This payslip belongs to the cancelled batch "%s".\n\n'
                      'To reopen this payslip:\n'
                      '1. Open the batch: %s\n'
                      '2. Click "Set to Draft" on the batch\n'
                      '3. Then you can reopen individual payslips') % (
                          payslip.payslip_run_id.name,
                          payslip.payslip_run_id.name
                      )
                )

        # If validation passes, call parent method
        res = super(HrPayslip, self).action_payslip_draft()
        self.message_post(body=_("Payslip set to Draft."))
        return res
    
    def action_compose_payslip_email(self):
        """Generates the compact payslip PDF and opens the mail composer."""
        self.ensure_one()

        # 1. Generate the PDF report
        report_sudo = self.env['ir.actions.report'].sudo()
        pdf_content, _ = report_sudo._render_qweb_pdf(
            'ueipab_payroll_enhancements.action_report_payslip_compact',
            self.id
        )

        # 2. Create an ir.attachment record for the PDF
        attachment = self.env['ir.attachment'].create({
            'name': f"Payslip-{self.name.replace('/', '_')}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'mail.compose.message',  # Link to mail.compose.message for temporary attachment
            'res_id': 0,  # No specific record yet, will be linked to the composer
            'mimetype': 'application/pdf',
        })

        # 3. Prepare email values and open the mail.compose.message wizard
        email_to = self.employee_id.work_email if self.employee_id.work_email else self.employee_id.user_id.email
        if not email_to:
            raise UserError(_("Employee %s has no work email or user email configured.") % self.employee_id.name)

        subject = f"Your Payslip for {self.name}"
        body = f"""
            <p>Dear {self.employee_id.name},</p>
            <p>Please find your payslip attached for the period from {self.date_from} to {self.date_to}.</p>
            <p>If you have any questions, please contact the HR department.</p>
            <br/>
            <p>Best regards,</p>
            <p>{self.env.company.name}</p>
        """

        # Get the partner for the employee (user's partner)
        partner = self.employee_id.user_partner_id if self.employee_id.user_partner_id else False

        ctx = {
            'default_composition_mode': 'comment',
            'default_model': 'hr.payslip',
            'default_res_id': self.id,
            'default_partner_ids': [(6, 0, [partner.id])] if partner else False,
            'default_email_to': email_to,
            'default_subject': subject,
            'default_body': body,
            'default_attachment_ids': [(6, 0, [attachment.id])],
            'custom_layout': 'mail.mail_notification_light',
        }

        return {
            'name': 'Compose Email',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }
