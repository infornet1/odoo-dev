# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    """Extend payslip generation wizard with structure selector"""
    _inherit = 'hr.payslip.employees'

    structure_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
        help="Optional: Select a salary structure to override the default "
             "contract structure for all generated payslips.\n\n"
             "Leave empty to use each employee's contract structure (standard behavior).\n\n"
             "Use this when generating special payrolls like:\n"
             "• Aguinaldos (Christmas Bonus)\n"
             "• Mid-year bonuses\n"
             "• Liquidations\n"
             "• Any other non-regular payroll"
    )

    use_contract_structure = fields.Boolean(
        string='Use Contract Structure',
        default=True,
        help="If checked, each payslip will use the structure from the employee's contract. "
             "If unchecked, the selected structure above will be used for all payslips."
    )

    @api.onchange('structure_id')
    def _onchange_structure_id(self):
        """Auto-update use_contract_structure based on structure selection"""
        if self.structure_id:
            self.use_contract_structure = False
        else:
            self.use_contract_structure = True

    @api.model
    def default_get(self, fields_list):
        """Smart defaults based on batch name or context"""
        res = super(HrPayslipEmployees, self).default_get(fields_list)

        # Get the active batch
        active_id = self.env.context.get('active_id')
        if active_id:
            batch = self.env['hr.payslip.run'].browse(active_id)

            # Smart default: Detect Aguinaldos batch by name
            if batch.name and 'aguinaldo' in batch.name.lower():
                aguinaldos_struct = self.env['hr.payroll.structure'].search([
                    ('code', '=', 'AGUINALDOS_2025')
                ], limit=1)
                if aguinaldos_struct:
                    res['structure_id'] = aguinaldos_struct.id
                    res['use_contract_structure'] = False

        return res

    def action_compute_sheet(self):
        """Override to apply selected structure to all payslips"""

        # Validation: Check if we have employees
        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        # Get batch data
        active_id = self.env.context.get('active_id')
        if not active_id:
            raise UserError(_("No batch selected. Please generate payslips from a batch."))

        payslip_run = self.env['hr.payslip.run'].browse(active_id)
        run_data = payslip_run.read(['date_start', 'date_end', 'credit_note'])[0]

        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')

        # Determine which structure to use
        override_structure_id = False
        if not self.use_contract_structure and self.structure_id:
            override_structure_id = self.structure_id.id

        # Generate payslips
        payslips = self.env['hr.payslip']

        for employee in self.employee_ids:
            # Get default data from contract
            slip_data = self.env['hr.payslip'].onchange_employee_id(
                from_date, to_date, employee.id, contract_id=False
            )

            # Prepare payslip data
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in
                                   slip_data['value'].get('input_line_ids', [])],
                'worked_days_line_ids': [(0, 0, x) for x in
                                         slip_data['value'].get('worked_days_line_ids', [])],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }

            # CRITICAL: Apply structure override if selected
            if override_structure_id:
                res['struct_id'] = override_structure_id
            else:
                # Use default from contract
                res['struct_id'] = slip_data['value'].get('struct_id')

            # Create payslip
            payslips += self.env['hr.payslip'].create(res)

        # Compute all payslips
        payslips.action_compute_sheet()

        # Apply batch exchange rate from our custom field (NOT batch_exchange_rate from hr_payroll_community)
        # Our exchange_rate field is auto-populated from VEB currency rates
        if payslip_run.exchange_rate > 0:
            payslips.write({
                'exchange_rate_used': payslip_run.exchange_rate,
                'exchange_rate_date': fields.Datetime.now()
            })

        return {'type': 'ir.actions.act_window_close'}
