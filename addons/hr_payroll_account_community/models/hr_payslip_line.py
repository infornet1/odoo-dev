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
from odoo import models


class HrPayslipLine(models.Model):
    """Extends the standard 'hr.payslip.line' model to provide additional
    functionality for accounting.
    Methods:
        - _get_partner_id: Get partner_id of the slip line to use in
        account_move_line."""
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, credit_account):
        """Get partner_id of slip line to use in account_move_line."""
        # First try to get partner from salary rule register
        register_partner_id = self.salary_rule_id.register_id.partner_id
        if register_partner_id:
            return register_partner_id.id

        # For liquidation rules (LIQUID_*), always use employee's partner
        if self.salary_rule_id.code and self.salary_rule_id.code.startswith('LIQUID_'):
            # Use employee's work contact (individual partner)
            if self.slip_id.employee_id:
                if self.slip_id.employee_id.work_contact_id:
                    return self.slip_id.employee_id.work_contact_id.id
                # Fallback to employee's address_id
                if self.slip_id.employee_id.address_id:
                    return self.slip_id.employee_id.address_id.id

        # For receivable/payable accounts, use EMPLOYEE's individual partner
        # This ensures journal entries show employee as partner (not company)
        # Critical for: partner ledger, aging reports, payment reconciliation
        if credit_account:
            if self.salary_rule_id.account_credit_id.account_type in (
                    'asset_receivable', 'liability_payable'):
                if self.slip_id.employee_id:
                    # Use work_contact_id (employee's individual partner record)
                    if self.slip_id.employee_id.work_contact_id:
                        return self.slip_id.employee_id.work_contact_id.id
                    # Fallback to address_id (company) only if work_contact missing
                    if self.slip_id.employee_id.address_id:
                        return self.slip_id.employee_id.address_id.id
        else:
            if self.salary_rule_id.account_debit_id.account_type in (
                    'asset_receivable', 'liability_payable'):
                if self.slip_id.employee_id:
                    # Use work_contact_id (employee's individual partner record)
                    if self.slip_id.employee_id.work_contact_id:
                        return self.slip_id.employee_id.work_contact_id.id
                    # Fallback to address_id (company) only if work_contact missing
                    if self.slip_id.employee_id.address_id:
                        return self.slip_id.employee_id.address_id.id

        # For all other payroll entries, use employee's individual partner
        if self.slip_id.employee_id:
            if self.slip_id.employee_id.work_contact_id:
                return self.slip_id.employee_id.work_contact_id.id
            if self.slip_id.employee_id.address_id:
                return self.slip_id.employee_id.address_id.id

        return False
