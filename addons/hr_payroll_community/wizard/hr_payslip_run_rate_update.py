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

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrPayslipRunRateUpdateWizard(models.TransientModel):
    _name = 'hr.payslip.run.rate.update.wizard'
    _description = 'Exchange Rate Update Wizard'

    payslip_run_id = fields.Many2one('hr.payslip.run', required=True)
    current_rate = fields.Float('Current Rate', readonly=True)
    new_rate = fields.Float('New Rate', required=True)
    has_payslips = fields.Boolean('Has Payslips', default=False)
    payslips_count = fields.Integer('Payslips Count', default=0)

    regenerate_payslips = fields.Boolean(
        'Regenerate Payslips',
        help='Delete existing payslips and regenerate with new rate'
    )

    def action_confirm_update(self):
        """Apply the rate change"""
        if self.has_payslips and self.regenerate_payslips:
            # Delete existing payslips
            self.payslip_run_id.slip_ids.unlink()

            # Log the regeneration (message_post not available without mail.thread inheritance)
            # TODO: Add alternative logging method
            pass

        # Update the rate
        self.payslip_run_id.write({
            'batch_exchange_rate': self.new_rate,
            'exchange_rate_confirmed': True,
            'exchange_rate_set_date': fields.Datetime.now(),
            'exchange_rate_set_by': self.env.user.id
        })

        # If regenerate was selected, generate new payslips automatically would need UI action
        # If just updating existing payslips
        if self.has_payslips and not self.regenerate_payslips:
            # Just update existing payslips
            self.payslip_run_id.slip_ids.write({
                'exchange_rate_used': self.new_rate,
                'exchange_rate_date': fields.Datetime.now()
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Rate Updated'),
                    'message': f'Updated {self.payslips_count} existing payslips with new rate {self.new_rate}',
                    'type': 'success',
                }
            }
        elif self.has_payslips and self.regenerate_payslips:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Payslips Deleted'),
                    'message': f'Deleted {self.payslips_count} payslips. You can now generate new ones with rate {self.new_rate}',
                    'type': 'success',
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rate Updated'),
                'message': f'Exchange rate updated to {self.new_rate} VES/USD',
                'type': 'success',
            }
        }