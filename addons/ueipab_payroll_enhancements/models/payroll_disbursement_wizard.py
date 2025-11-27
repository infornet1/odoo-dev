# -*- coding: utf-8 -*-
"""
Payroll Disbursement Detail Report Wizard

This wizard allows users to generate detailed payroll disbursement reports
with flexible filtering options (batch or date range).
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
import xlsxwriter


class PayrollDisbursementWizard(models.TransientModel):
    """Wizard for generating Payroll Disbursement Detail reports."""

    _name = 'payroll.disbursement.wizard'
    _description = 'Payroll Disbursement Detail Report Wizard'

    # ========================================
    # FILTER SELECTION
    # ========================================

    filter_type = fields.Selection([
        ('batch', 'Specific Batch'),
        ('date_range', 'Date Range'),
    ], string='Filter By', required=True, default='batch',
       help='Select how to filter payslips: by specific batch or by date range')

    # Batch selection (when filter_type = 'batch')
    batch_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        help='Select specific payslip batch to generate report for'
    )

    # Date range selection (when filter_type = 'date_range')
    date_from = fields.Date(
        string='Date From',
        default=lambda self: fields.Date.today().replace(day=1),
        help='Start date for payslip date range filter'
    )

    date_to = fields.Date(
        string='Date To',
        default=fields.Date.today,
        help='End date for payslip date range filter'
    )

    # Additional filters (apply to both modes)
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Filter specific employees (leave empty for all employees)'
    )

    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Filter specific departments (leave empty for all departments)'
    )

    # Currency selection
    currency_id = fields.Many2one(
        'res.currency',
        string='Display Currency',
        required=True,
        default=lambda self: self.env.ref('base.USD'),
        help='Currency for report display (USD or VEB)'
    )

    # Output format selection
    output_format = fields.Selection([
        ('pdf', 'PDF Report'),
        ('excel', 'Excel Spreadsheet (.xlsx)'),
    ], string='Output Format', required=True, default='pdf',
       help='Choose export format: PDF for printing or Excel for data analysis')

    # ========================================
    # COMPUTED FIELDS
    # ========================================

    payslip_count = fields.Integer(
        string='Payslips Found',
        compute='_compute_payslip_count',
        help='Number of payslips matching current filter criteria (excludes cancelled payslips)'
    )

    @api.depends('filter_type', 'batch_id', 'date_from', 'date_to',
                 'employee_ids', 'department_ids')
    def _compute_payslip_count(self):
        """Count payslips matching current filter criteria."""
        for wizard in self:
            payslips = wizard._get_filtered_payslips()
            wizard.payslip_count = len(payslips)

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def _get_filtered_payslips(self):
        """Get payslips matching wizard filter criteria.

        Returns:
            recordset: hr.payslip records matching filters
        """
        self.ensure_one()

        # Include all payslips except cancelled ones
        # This allows reporting on draft, verify, done, and paid payslips
        domain = [('state', '!=', 'cancel')]

        # Filter by batch or date range
        if self.filter_type == 'batch':
            if not self.batch_id:
                return self.env['hr.payslip']
            domain.append(('payslip_run_id', '=', self.batch_id.id))
        else:  # date_range
            if self.date_from:
                domain.append(('date_from', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_to', '<=', self.date_to))

        # Additional filters
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))

        # Find matching payslips
        payslips = self.env['hr.payslip'].search(domain)

        # Sort by employee name (can't use order='employee_id.name' in Odoo 17)
        return payslips.sorted(lambda p: p.employee_id.name or '')

    def action_print_report(self):
        """Generate and export the Payroll Disbursement Detail report.

        Routes to PDF or Excel export based on output_format field.

        Returns:
            dict: Report action or file download action

        Raises:
            UserError: If no payslips match the filter criteria
        """
        self.ensure_one()

        # Validate filters
        if self.filter_type == 'batch' and not self.batch_id:
            raise UserError(_('Please select a payslip batch.'))

        if self.filter_type == 'date_range':
            if not self.date_from or not self.date_to:
                raise UserError(_('Please specify both start and end dates.'))
            if self.date_from > self.date_to:
                raise UserError(_('Start date must be before end date.'))

        # Get filtered payslips
        payslips = self._get_filtered_payslips()

        if not payslips:
            raise UserError(_(
                'No payslips found matching the selected criteria.\n\n'
                'Please ensure:\n'
                '- Payslips are not cancelled\n'
                '- Filter criteria are correct\n'
                '- Selected batch/date range contains payslips'
            ))

        # Route based on output format
        if self.output_format == 'excel':
            return self._action_export_excel(payslips)
        else:
            return self._action_export_pdf(payslips)

    def _action_export_pdf(self, payslips):
        """Generate PDF report.

        Args:
            payslips: hr.payslip recordset

        Returns:
            dict: PDF report action
        """
        self.ensure_one()

        # Get payslip IDs and ensure we have a fresh recordset
        # This is necessary because wizard is a TransientModel
        payslip_ids = payslips.ids

        # Prepare report data context
        data = {
            'wizard_id': self.id,
            'filter_type': self.filter_type,
            'batch_name': self.batch_id.name if self.batch_id else None,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_count': len(payslips.mapped('employee_id')),
            'payslip_count': len(payslips),
            'payslip_ids': payslip_ids,  # Store IDs in data for debugging
            'currency_id': self.currency_id.id,
            'currency_name': self.currency_id.name,
        }

        # Generate PDF report using the report's _render method directly
        report = self.env.ref('ueipab_payroll_enhancements.action_report_payroll_disbursement_detail')

        # Use report_action with explicit docids parameter
        return report.report_action(docids=payslip_ids, data=data)

    def _action_export_excel(self, payslips):
        """Generate Excel spreadsheet export.

        Args:
            payslips: hr.payslip recordset

        Returns:
            dict: File download action
        """
        self.ensure_one()

        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Payroll Disbursement')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
        })

        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'align': 'right',
        })

        text_format = workbook.add_format({
            'align': 'left',
        })

        total_format = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00',
            'align': 'right',
            'top': 1,
        })

        # Set column widths
        worksheet.set_column('A:A', 25)  # Employee Name
        worksheet.set_column('B:B', 20)  # Employee ID
        worksheet.set_column('C:C', 12)  # Salary
        worksheet.set_column('D:D', 12)  # Bonus
        worksheet.set_column('E:E', 12)  # Gross
        worksheet.set_column('F:F', 12)  # ARI TAX
        worksheet.set_column('G:G', 12)  # SSO 4%
        worksheet.set_column('H:H', 12)  # FAOV 1%
        worksheet.set_column('I:I', 12)  # PARO 0.5%
        worksheet.set_column('J:J', 12)  # Total Deductions
        worksheet.set_column('K:K', 12)  # Net Payable

        # Get currency info
        currency_symbol = self.currency_id.symbol
        currency_name = self.currency_id.name

        # Write title
        title = 'Payroll Disbursement Detail Report'
        if self.batch_id:
            title += f' - {self.batch_id.name}'
        elif self.date_from and self.date_to:
            title += f' - {self.date_from} to {self.date_to}'
        title += f' ({currency_name})'

        worksheet.merge_range('A1:K1', title, workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
        }))

        # Write headers
        headers = [
            'Employee Name',
            'Employee ID',
            f'Salary ({currency_symbol})',
            f'Bonus ({currency_symbol})',
            f'Gross ({currency_symbol})',
            f'ARI TAX ({currency_symbol})',
            f'SSO 4% ({currency_symbol})',
            f'FAOV 1% ({currency_symbol})',
            f'PARO 0.5% ({currency_symbol})',
            f'Total Deductions ({currency_symbol})',
            f'Net Payable ({currency_symbol})',
        ]

        for col, header in enumerate(headers):
            worksheet.write(2, col, header, header_format)

        # Initialize totals
        total_salary = 0.0
        total_bonus = 0.0
        total_gross = 0.0
        total_ari = 0.0
        total_sso = 0.0
        total_faov = 0.0
        total_paro = 0.0
        total_deductions = 0.0
        total_net = 0.0

        # Get exchange rate if VEB
        # Priority: 1) Batch exchange_rate, 2) Payslip exchange_rate_used, 3) Date-based lookup
        usd_currency = self.env.ref('base.USD')
        exchange_rate = 1.0
        if self.currency_id != usd_currency:
            # Try to get exchange rate from batch first
            if self.batch_id and self.batch_id.exchange_rate and self.batch_id.exchange_rate > 0:
                # Priority 1: Use batch's custom exchange rate
                exchange_rate = self.batch_id.exchange_rate
            elif payslips and payslips[0].exchange_rate_used and payslips[0].exchange_rate_used > 0:
                # Priority 2: Use payslip's exchange_rate_used field
                exchange_rate = payslips[0].exchange_rate_used
            else:
                # Priority 3: Fallback to date-based currency lookup
                latest_date = max(payslips.mapped('date_to'))
                veb_currency = self.currency_id
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', veb_currency.id),
                    ('name', '<=', latest_date)
                ], limit=1, order='name desc')
                if rate_record:
                    exchange_rate = rate_record.company_rate

        # Write data rows
        row = 3
        for payslip in payslips.sorted(lambda p: p.employee_id.name):
            # Get salary and bonus (V2 vs V1)
            if payslip.contract_id.ueipab_salary_v2 and payslip.contract_id.ueipab_salary_v2 > 0:
                # V2: Use direct contract field values
                salary = payslip.contract_id.ueipab_salary_v2 or 0.0
                bonus = (payslip.contract_id.ueipab_extrabonus_v2 or 0.0) + \
                        (payslip.contract_id.ueipab_bonus_v2 or 0.0) + \
                        (payslip.contract_id.cesta_ticket_usd or 0.0)
            else:
                # V1: Calculate from deduction_base using 70/30 split
                deduction_base = payslip.contract_id.ueipab_deduction_base or 0.0
                salary = deduction_base * 0.70
                bonus = (deduction_base * 0.30) + \
                        ((payslip.contract_id.wage or 0.0) - deduction_base)

            # Prorate by period
            period_days = (payslip.date_to - payslip.date_from).days + 1
            proration = period_days / 30.0
            salary_prorated = salary * proration
            bonus_prorated = bonus * proration

            # Get deduction lines (V2 with V1 fallback)
            ari_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_ARI_DED_V2')
            if not ari_line:
                ari_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_ARI_DED')

            sso_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SSO_DED_V2')
            if not sso_line:
                sso_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SSO_DED')

            faov_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_FAOV_DED_V2')
            if not faov_line:
                faov_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_FAOV_DED')

            paro_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_PARO_DED_V2')
            if not paro_line:
                paro_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_PARO_DED')

            net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET_V2')
            if not net_line:
                net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')

            # Get values
            ari = abs(ari_line[0].total) if ari_line else 0.0
            sso = abs(sso_line[0].total) if sso_line else 0.0
            faov = abs(faov_line[0].total) if faov_line else 0.0
            paro = abs(paro_line[0].total) if paro_line else 0.0
            net = net_line[0].total if net_line else 0.0

            gross = salary_prorated + bonus_prorated
            deductions = ari + sso + faov + paro

            # Convert to selected currency if needed
            if exchange_rate != 1.0:
                salary_prorated *= exchange_rate
                bonus_prorated *= exchange_rate
                gross *= exchange_rate
                ari *= exchange_rate
                sso *= exchange_rate
                faov *= exchange_rate
                paro *= exchange_rate
                deductions *= exchange_rate
                net *= exchange_rate

            # Write row
            worksheet.write(row, 0, payslip.employee_id.name, text_format)
            worksheet.write(row, 1, payslip.employee_id.identification_id or '', text_format)
            worksheet.write(row, 2, salary_prorated, currency_format)
            worksheet.write(row, 3, bonus_prorated, currency_format)
            worksheet.write(row, 4, gross, currency_format)
            worksheet.write(row, 5, ari, currency_format)
            worksheet.write(row, 6, sso, currency_format)
            worksheet.write(row, 7, faov, currency_format)
            worksheet.write(row, 8, paro, currency_format)
            worksheet.write(row, 9, deductions, currency_format)
            worksheet.write(row, 10, net, currency_format)

            # Add to totals
            total_salary += salary_prorated
            total_bonus += bonus_prorated
            total_gross += gross
            total_ari += ari
            total_sso += sso
            total_faov += faov
            total_paro += paro
            total_deductions += deductions
            total_net += net

            row += 1

        # Write totals
        worksheet.write(row, 0, 'TOTAL', workbook.add_format({'bold': True}))
        worksheet.write(row, 1, '', text_format)
        worksheet.write(row, 2, total_salary, total_format)
        worksheet.write(row, 3, total_bonus, total_format)
        worksheet.write(row, 4, total_gross, total_format)
        worksheet.write(row, 5, total_ari, total_format)
        worksheet.write(row, 6, total_sso, total_format)
        worksheet.write(row, 7, total_faov, total_format)
        worksheet.write(row, 8, total_paro, total_format)
        worksheet.write(row, 9, total_deductions, total_format)
        worksheet.write(row, 10, total_net, total_format)

        # Close workbook
        workbook.close()

        # Get file content
        output.seek(0)
        file_data = output.read()
        output.close()

        # Generate filename
        filename = 'Payroll_Disbursement_Detail'
        if self.batch_id:
            filename += f'_{self.batch_id.name.replace(" ", "_")}'
        elif self.date_from and self.date_to:
            filename += f'_{self.date_from}_to_{self.date_to}'
        filename += f'_{currency_name}.xlsx'

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_preview(self):
        """Preview payslips that will be included in the report.

        Opens a tree view showing which payslips match the current filters.
        Useful for verifying selection before printing.

        Returns:
            dict: Action to display payslip list
        """
        self.ensure_one()

        payslips = self._get_filtered_payslips()

        return {
            'name': _('Payslips to Include in Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payslips.ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
        }
