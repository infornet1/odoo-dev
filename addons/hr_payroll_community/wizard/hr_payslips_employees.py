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
from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    """Create new model for Generate payslips for all selected employees"""
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    employee_ids = fields.Many2many('hr.employee',
                                    'hr_employee_group_rel',
                                    'payslip_id',
                                    'employee_id', 'Employees',
                                    help="Choose employee for Payslip")

    def action_compute_sheet(self):
        """Function for compute Payslip Sheet"""
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')

        # Get the payslip run/batch
        payslip_run = None
        if active_id:
            payslip_run = self.env['hr.payslip.run'].browse(active_id)
            [run_data] = payslip_run.read(['date_start', 'date_end', 'credit_note'])

            # Exchange rate validation temporarily disabled for testing
            # TODO: Re-enable when UI is working
            # if not payslip_run.exchange_rate_confirmed:
            #     raise UserError(_(
            #         "Cannot generate payslips without confirmed exchange rate.\n"
            #         "Please set the rate and click 'Confirm Exchange Rate' first."
            #     ))

        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(
                _("You must select employee(s) to generate payslip(s)."))

        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = (
                self.env['hr.payslip'].onchange_employee_id(
                    from_date, to_date, employee.id, contract_id=False))
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in
                                   slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in
                                         slip_data['value'].get(
                                             'worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }
            payslips += self.env['hr.payslip'].create(res)

        # Compute payslips first
        payslips.action_compute_sheet()

        # Apply batch exchange rate to all generated payslips (if batch exists)
        if payslip_run and payslip_run.batch_exchange_rate > 0:
            payslips.write({
                'exchange_rate_used': payslip_run.batch_exchange_rate,
                'exchange_rate_date': payslip_run.exchange_rate_set_date or fields.Datetime.now()
            })

            # Log the action (message_post not available on hr.payslip.run without mail.thread)
            # TODO: Add mail.thread inheritance to hr.payslip.run model for logging
            pass

        return {'type': 'ir.actions.act_window_close'}
