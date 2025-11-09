# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class HrPayslipRun(models.Model):
    """Create new model for getting Payslip Batches"""
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True, help="Name for Payslip Batches",
                       string="Name")
    slip_ids = fields.One2many('hr.payslip',
                               'payslip_run_id',
                               string='Payslips',
                               help="Choose Payslips for Batches")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
                               help="Status for Payslip Batches")
    date_start = fields.Date(string='Date From', required=True,
                             help="start date for batch",
                             default=lambda self: fields.Date.to_string(
                                 date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True,
                           help="End date for batch",
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1,
                                                               days=-1)).date())
                           )
    credit_note = fields.Boolean(string='Credit Note',
                                 help="If its checked, indicates that all"
                                      "payslips generated from here are refund"
                                      "payslips.")
    is_validate = fields.Boolean(compute='_compute_is_validate')

    # Exchange Rate Control Fields
    batch_exchange_rate = fields.Float(
        string='Batch Exchange Rate (USD→VES)',
        digits=(12, 6),
        default=lambda self: self._default_batch_exchange_rate(),
        help='Exchange rate to be applied to all payslips in this batch. Format: 1 USD = X VES'
    )

    exchange_rate_confirmed = fields.Boolean(
        string='Exchange Rate Confirmed',
        default=False,
        help='Indicates if payroll user has confirmed this exchange rate'
    )

    exchange_rate_set_date = fields.Datetime(
        string='Rate Set Date',
        readonly=True
    )

    exchange_rate_set_by = fields.Many2one(
        'res.users',
        string='Rate Set By',
        readonly=True
    )

    # Status helper field
    can_generate_payslips = fields.Boolean(
        string='Can Generate Payslips',
        compute='_compute_can_generate_payslips'
    )

    def _default_batch_exchange_rate(self):
        """Auto-populate exchange rate with most recent rate or system rate"""
        # Simple default - just return 0.0 for now to avoid transaction issues
        # The auto-population can be done through onchange methods instead
        return 0.0

    @api.onchange('name')
    def _onchange_name_populate_rate(self):
        """Auto-populate exchange rate when creating a new batch"""
        if self.name and not self.batch_exchange_rate:
            try:
                # Get the most recent confirmed rate from previous batches
                recent_batch = self.search([
                    ('batch_exchange_rate', '>', 0),
                    ('exchange_rate_confirmed', '=', True)
                ], limit=1, order='date_start desc, id desc')

                if recent_batch:
                    self.batch_exchange_rate = recent_batch.batch_exchange_rate
            except:
                # If any error occurs, just keep 0.0
                pass

    @api.depends('exchange_rate_confirmed', 'batch_exchange_rate')
    def _compute_can_generate_payslips(self):
        for record in self:
            record.can_generate_payslips = (
                record.exchange_rate_confirmed and
                record.batch_exchange_rate > 0
            )

    def _compute_is_validate(self):
        for record in self:
            if record.slip_ids and record.slip_ids.filtered(
                    lambda slip: slip.state == 'draft'):
                record.is_validate = True
            else:
                record.is_validate = False

    def action_validate_payslips(self):
        if self.slip_ids:
            for slip in self.slip_ids.filtered(
                    lambda slip: slip.state == 'draft'):
                slip.action_payslip_done()

    def action_payslip_run(self):
        """Function for state change"""
        return self.write({'state': 'draft'})

    def close_payslip_run(self):
        """Function for state change"""
        return self.write({'state': 'close'})

    # Exchange Rate Control Methods

    def action_confirm_exchange_rate(self):
        """Any payroll user can confirm the exchange rate"""
        # Basic validation
        if not self.batch_exchange_rate or self.batch_exchange_rate <= 0:
            raise UserError(_("Please set a valid exchange rate before confirming."))

        # Check if rate is within normal ranges (alert but don't block)
        self._check_rate_ranges()

        # Confirm the rate
        self.write({
            'exchange_rate_confirmed': True,
            'exchange_rate_set_date': fields.Datetime.now(),
            'exchange_rate_set_by': self.env.user.id
        })

        # Log the action (message_post not available without mail.thread inheritance)
        # TODO: Add mail.thread inheritance for proper logging
        pass

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Exchange Rate Confirmed'),
                'message': f'Exchange rate {self.batch_exchange_rate} VES/USD has been confirmed.',
                'type': 'success',
            }
        }

    def _check_rate_ranges(self):
        """Alert if rate is outside normal ranges (but don't block)"""
        # Venezuelan business context: rates are fixed for 24hrs
        # Alert if significantly different from recent rates

        # Get yesterday's rate if exists
        yesterday = fields.Date.today() - timedelta(days=1)
        recent_batch = self.search([
            ('date_start', '>=', yesterday),
            ('batch_exchange_rate', '>', 0),
            ('id', '!=', self.id)
        ], limit=1, order='date_start desc')

        if recent_batch:
            variance = abs((self.batch_exchange_rate - recent_batch.batch_exchange_rate) / recent_batch.batch_exchange_rate * 100)
            if variance > 10:  # 10% variance threshold
                # Alert but don't block (message_post not available without mail.thread)
                # TODO: Add mail.thread inheritance or use alternative notification method
                pass

    def action_update_exchange_rate(self):
        """Allow rate changes even after payslips generated (with warning)"""

        # Warning if payslips already exist
        if self.slip_ids:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Update Exchange Rate',
                'res_model': 'hr.payslip.run.rate.update.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_payslip_run_id': self.id,
                    'default_current_rate': self.batch_exchange_rate,
                    'default_has_payslips': True,
                    'default_payslips_count': len(self.slip_ids)
                }
            }
        else:
            # No payslips yet, just reset confirmation
            self.write({
                'exchange_rate_confirmed': False,
                'exchange_rate_set_date': False,
                'exchange_rate_set_by': False
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Rate Reset'),
                    'message': 'You can now set a new exchange rate.',
                    'type': 'info',
                }
            }
