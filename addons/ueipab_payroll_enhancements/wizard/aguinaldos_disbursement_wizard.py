# -*- coding: utf-8 -*-
"""
Aguinaldos Disbursement Report Wizard

Wizard to generate the Aguinaldos (Christmas Bonus) Disbursement Report.
Allows selection of batch and currency for report generation.
Supports PDF and Excel export formats.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class AguinaldosDisbursementWizard(models.TransientModel):
    """Wizard for generating Aguinaldos Disbursement Report."""

    _name = 'hr.payslip.aguinaldos.disbursement.wizard'
    _description = 'Aguinaldos Disbursement Report Wizard'

    # Batch Selection
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        required=True,
        domain="[('slip_ids', '!=', False)]",
        help='Select the Aguinaldos batch to generate the report for.'
    )

    # Currency Selection
    currency_id = fields.Many2one(
        'res.currency',
        string='Report Currency',
        default=lambda self: self.env.ref('base.USD'),
        required=True,
        help='Currency for displaying amounts in the report. '
             'Select VEB to show amounts in Bolivares.'
    )

    # Output format selection
    output_format = fields.Selection([
        ('pdf', 'PDF Report'),
        ('excel', 'Excel Spreadsheet (.xlsx)'),
    ], string='Output Format', required=True, default='pdf',
       help='Choose export format: PDF for printing or Excel for data analysis')

    # Payslip Filter
    include_draft = fields.Boolean(
        string='Include Draft Payslips',
        default=True,
        help='Include draft (unconfirmed) payslips in the report.'
    )

    # Computed Fields
    payslip_count = fields.Integer(
        string='Payslips',
        compute='_compute_payslip_info'
    )

    total_aguinaldo = fields.Float(
        string='Total Aguinaldos',
        compute='_compute_payslip_info',
        digits=(12, 2)
    )

    @api.depends('payslip_run_id', 'include_draft')
    def _compute_payslip_info(self):
        """Compute payslip count and total for preview."""
        for wizard in self:
            if wizard.payslip_run_id:
                payslips = wizard._get_filtered_payslips()
                wizard.payslip_count = len(payslips)

                # Sum AGUINALDOS lines
                total = 0.0
                for slip in payslips:
                    aguinaldo_line = slip.line_ids.filtered(
                        lambda l: l.salary_rule_id.code == 'AGUINALDOS'
                    )
                    if aguinaldo_line:
                        total += aguinaldo_line[0].total
                wizard.total_aguinaldo = total
            else:
                wizard.payslip_count = 0
                wizard.total_aguinaldo = 0.0

    def _get_filtered_payslips(self):
        """Get payslips based on wizard filters."""
        self.ensure_one()
        if not self.payslip_run_id:
            return self.env['hr.payslip']

        # Filter by state
        if self.include_draft:
            states = ['draft', 'done', 'paid']
        else:
            states = ['done', 'paid']

        return self.payslip_run_id.slip_ids.filtered(
            lambda s: s.state in states
        )

    def action_generate_report(self):
        """Generate the Aguinaldos Disbursement Report (PDF or Excel)."""
        self.ensure_one()

        payslips = self._get_filtered_payslips()

        if not payslips:
            raise UserError(_(
                'No payslips found in the selected batch with the current filters.'
            ))

        # Check if payslips have AGUINALDOS lines
        has_aguinaldos = any(
            slip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'AGUINALDOS')
            for slip in payslips
        )

        if not has_aguinaldos:
            raise UserError(_(
                'No AGUINALDOS salary rule lines found in the selected payslips. '
                'This report is designed for Aguinaldos (Christmas Bonus) batches only.'
            ))

        # Route based on output format
        if self.output_format == 'excel':
            return self._action_export_excel(payslips)
        else:
            return self._action_export_pdf(payslips)

    def _action_export_pdf(self, payslips):
        """Generate PDF report."""
        self.ensure_one()

        # Prepare data for report
        data = {
            'payslip_ids': payslips.ids,
            'batch_name': self.payslip_run_id.name,
            'currency_id': self.currency_id.id,
            'include_draft': self.include_draft,
            'payslip_count': len(payslips),
        }

        # Return report action
        return self.env.ref(
            'ueipab_payroll_enhancements.action_report_aguinaldos_disbursement'
        ).report_action(payslips, data=data)

    def _action_export_excel(self, payslips):
        """Generate Excel spreadsheet export.

        Args:
            payslips: hr.payslip recordset

        Returns:
            dict: File download action
        """
        self.ensure_one()

        if not xlsxwriter:
            raise UserError(_(
                'xlsxwriter library is not installed. '
                'Please install it with: pip install xlsxwriter'
            ))

        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Aguinaldos')

        # Define formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#c41e3a',
        })

        subtitle_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#2e7d32',
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#c41e3a',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
        })

        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'align': 'right',
            'border': 1,
        })

        text_format = workbook.add_format({
            'align': 'left',
            'border': 1,
        })

        text_center_format = workbook.add_format({
            'align': 'center',
            'border': 1,
        })

        total_label_format = workbook.add_format({
            'bold': True,
            'align': 'right',
            'border': 1,
            'bg_color': '#f5f5f5',
        })

        total_format = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00',
            'align': 'right',
            'border': 1,
            'bg_color': '#f5f5f5',
            'font_color': '#2e7d32',
        })

        # Set column widths
        worksheet.set_column('A:A', 5)   # #
        worksheet.set_column('B:B', 15)  # Cedula
        worksheet.set_column('C:C', 35)  # Employee
        worksheet.set_column('D:D', 30)  # Work Email
        worksheet.set_column('E:E', 18)  # Salary Base
        worksheet.set_column('F:F', 18)  # Aguinaldo

        # Get currency info
        currency_symbol = self.currency_id.symbol
        currency_name = self.currency_id.name

        # Get exchange rate if VEB
        usd_currency = self.env.ref('base.USD')
        exchange_rate = 1.0
        if self.currency_id != usd_currency:
            batch = self.payslip_run_id
            if batch and batch.exchange_rate and batch.exchange_rate > 0:
                exchange_rate = batch.exchange_rate
            elif payslips and payslips[0].exchange_rate_used and payslips[0].exchange_rate_used > 0:
                exchange_rate = payslips[0].exchange_rate_used
            else:
                latest_date = max(payslips.mapped('date_to'))
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', self.currency_id.id),
                    ('name', '<=', latest_date)
                ], limit=1, order='name desc')
                if rate_record:
                    exchange_rate = rate_record.company_rate

        # Write title
        worksheet.merge_range('A1:F1', 'RELACION DE PAGO - AGUINALDOS', title_format)
        worksheet.merge_range('A2:F2', 'Bono Navideno Diciembre 2025', subtitle_format)

        # Write batch info
        info_format = workbook.add_format({'align': 'center', 'font_size': 10})
        batch_info = f"Lote: {self.payslip_run_id.name} | Moneda: {currency_name}"
        if exchange_rate != 1.0:
            batch_info += f" @ {exchange_rate:,.4f} VEB/USD"
        worksheet.merge_range('A3:F3', batch_info, info_format)

        # Write headers (row 4, index 4)
        headers = ['#', 'CEDULA', 'EMPLEADO', 'EMAIL', f'SALARIO BASE ({currency_symbol})', f'AGUINALDO ({currency_symbol})']
        for col, header in enumerate(headers):
            worksheet.write(4, col, header, header_format)

        # Initialize totals
        total_salary_ref = 0.0
        total_aguinaldo = 0.0

        # Write data rows
        row = 5
        sequence = 1
        for payslip in payslips.sorted(lambda p: p.employee_id.name or ''):
            # Get AGUINALDOS line amount
            aguinaldo_line = payslip.line_ids.filtered(
                lambda l: l.salary_rule_id.code == 'AGUINALDOS'
            )
            aguinaldo_amount = aguinaldo_line[0].total if aguinaldo_line else 0.0

            # Get salary reference from contract (V2 salary)
            salary_ref = payslip.contract_id.ueipab_salary_v2 or 0.0

            # Apply exchange rate
            salary_display = salary_ref * exchange_rate
            aguinaldo_display = aguinaldo_amount * exchange_rate

            # Write row
            worksheet.write(row, 0, sequence, text_center_format)
            worksheet.write(row, 1, payslip.employee_id.identification_id or 'N/A', text_center_format)
            worksheet.write(row, 2, payslip.employee_id.name, text_format)
            worksheet.write(row, 3, payslip.employee_id.work_email or '', text_format)
            worksheet.write(row, 4, salary_display, currency_format)
            worksheet.write(row, 5, aguinaldo_display, currency_format)

            # Add to totals
            total_salary_ref += salary_display
            total_aguinaldo += aguinaldo_display

            row += 1
            sequence += 1

        # Write totals row
        employee_count = len(payslips)
        worksheet.write(row, 0, '', total_label_format)
        worksheet.write(row, 1, '', total_label_format)
        worksheet.write(row, 2, f'TOTAL ({employee_count} empleados)', total_label_format)
        worksheet.write(row, 3, '', total_label_format)
        worksheet.write(row, 4, total_salary_ref, total_format)
        worksheet.write(row, 5, total_aguinaldo, total_format)

        # Add summary section
        row += 2
        summary_header = workbook.add_format({'bold': True, 'font_size': 11})
        summary_text = workbook.add_format({'font_size': 10})

        worksheet.write(row, 0, 'RESUMEN:', summary_header)
        row += 1
        worksheet.write(row, 0, f'Total Empleados: {employee_count}', summary_text)
        row += 1
        worksheet.write(row, 0, f'Total Aguinaldos: {currency_symbol} {total_aguinaldo:,.2f}', summary_text)

        if exchange_rate != 1.0:
            row += 1
            worksheet.write(row, 0, f'(USD {total_aguinaldo/exchange_rate:,.2f} @ {exchange_rate:,.4f})', summary_text)

        row += 2
        worksheet.write(row, 0, 'CONCEPTO:', summary_header)
        row += 1
        worksheet.write(row, 0, 'LOTTT Art. 131-132: 1 mes de salario', summary_text)
        row += 1
        worksheet.write(row, 0, 'Adicional UEIPAB: 1 mes adicional', summary_text)
        row += 1
        worksheet.write(row, 0, 'Total: 2 meses de salario base', summary_text)

        # Close workbook
        workbook.close()

        # Get file content
        output.seek(0)
        file_data = output.read()
        output.close()

        # Generate filename
        batch_name = self.payslip_run_id.name.replace(' ', '_').replace('/', '-')
        filename = f'Aguinaldos_{batch_name}_{currency_name}.xlsx'

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
