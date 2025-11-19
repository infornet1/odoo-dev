# -*- coding: utf-8 -*-
"""
XLSX Export Controller for Relación de Liquidación Report

Generates Excel spreadsheet with liquidation breakdown details.
"""

from odoo import http
from odoo.http import request, content_disposition
import io
import xlsxwriter


class LiquidacionBreakdownXLSXController(http.Controller):
    """Controller for XLSX export of liquidation breakdown reports."""

    @http.route('/liquidacion/breakdown/xlsx/<int:wizard_id>', type='http', auth='user')
    def download_liquidacion_breakdown_xlsx(self, wizard_id, **kwargs):
        """Generate and download XLSX report.

        Args:
            wizard_id: ID of liquidacion.breakdown.wizard record

        Returns:
            Excel file download
        """
        # Get wizard
        wizard = request.env['liquidacion.breakdown.wizard'].browse(wizard_id)

        if not wizard.exists():
            return request.not_found()

        # Get currency
        currency = wizard.currency_id

        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        section_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'left',
            'bg_color': '#70AD47',
            'font_color': 'white',
            'border': 1
        })

        section_deduction_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'left',
            'bg_color': '#E74C3C',
            'font_color': 'white',
            'border': 1
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'bg_color': '#E8F5E9',
            'border': 1
        })

        money_format = workbook.add_format({
            'num_format': f'{currency.symbol}#,##0.00',
            'align': 'right',
            'border': 1
        })

        text_format = workbook.add_format({
            'align': 'left',
            'border': 1,
            'text_wrap': True
        })

        formula_format = workbook.add_format({
            'align': 'left',
            'border': 1,
            'font_size': 9,
            'italic': True,
            'text_wrap': True
        })

        total_format = workbook.add_format({
            'bold': True,
            'num_format': f'{currency.symbol}#,##0.00',
            'align': 'right',
            'bg_color': '#FFF3CD',
            'border': 2
        })

        total_label_format = workbook.add_format({
            'bold': True,
            'align': 'right',
            'bg_color': '#FFF3CD',
            'border': 2
        })

        # Get report model
        report_model = request.env['report.ueipab_payroll_enhancements.liquidacion_breakdown']

        # Generate sheet for each payslip
        for payslip in wizard.payslip_ids:
            # Get breakdown data
            breakdown = report_model._generate_breakdown(payslip, currency)

            # Create worksheet (use employee name)
            sheet_name = payslip.employee_id.name[:31]  # Excel sheet name limit
            worksheet = workbook.add_worksheet(sheet_name)

            # Set column widths
            worksheet.set_column('A:A', 5)   # Number
            worksheet.set_column('B:B', 50)  # Concept/Formula
            worksheet.set_column('C:C', 30)  # Detail
            worksheet.set_column('D:D', 15)  # Amount

            row = 0

            # HEADER
            worksheet.merge_range(row, 0, row, 3, 'RELACIÓN DE LIQUIDACIÓN', header_format)
            row += 1
            worksheet.merge_range(row, 0, row, 3, 'Liquidation Breakdown Report', header_format)
            row += 2

            # EMPLOYEE INFO
            worksheet.write(row, 0, 'Empleado:', title_format)
            worksheet.merge_range(row, 1, row, 3, breakdown['employee'].name, text_format)
            row += 1

            worksheet.write(row, 0, 'Cédula:', title_format)
            worksheet.merge_range(row, 1, row, 3, breakdown['employee'].identification_id or 'N/A', text_format)
            row += 1

            worksheet.write(row, 0, 'Departamento:', title_format)
            worksheet.write(row, 1, breakdown['employee'].department_id.name or 'N/A', text_format)
            worksheet.write(row, 2, 'Cargo:', title_format)
            worksheet.write(row, 3, breakdown['employee'].job_id.name or 'N/A', text_format)
            row += 1

            worksheet.write(row, 0, 'Fecha Ingreso:', title_format)
            worksheet.write(row, 1, breakdown['contract'].date_start.strftime('%d/%m/%Y'), text_format)
            worksheet.write(row, 2, 'Fecha Liquidación:', title_format)
            worksheet.write(row, 3, breakdown['payslip'].date_to.strftime('%d/%m/%Y'), text_format)
            row += 1

            worksheet.write(row, 0, 'Período Servicio:', title_format)
            service_text = f"{breakdown['service_months_total']} meses ({breakdown['service_years']} año(s), {breakdown['service_months']} mes(es))"
            worksheet.merge_range(row, 1, row, 3, service_text, text_format)
            row += 2

            # SECTION 1: BENEFITS
            worksheet.merge_range(row, 0, row, 3, '1. PRESTACIONES SOCIALES (BENEFICIOS)', section_format)
            row += 1

            # Benefits header
            worksheet.write(row, 0, '#', title_format)
            worksheet.write(row, 1, 'Concepto / Fórmula / Cálculo', title_format)
            worksheet.write(row, 2, 'Detalle', title_format)
            worksheet.write(row, 3, f'Monto ({currency.name})', title_format)
            row += 1

            # Benefits data
            for benefit in breakdown['benefits']:
                worksheet.write(row, 0, benefit['number'], text_format)

                # Concept with formula
                concept_text = f"{benefit['name']}\n{benefit['formula']}\n{benefit['calculation']}"
                worksheet.write(row, 1, concept_text, formula_format)
                worksheet.set_row(row, 45)  # Increase row height for wrapped text

                worksheet.write(row, 2, benefit['detail'], text_format)
                worksheet.write(row, 3, benefit['amount'], money_format)
                row += 1

            # Benefits subtotal
            worksheet.merge_range(row, 0, row, 2, 'SUBTOTAL PRESTACIONES:', total_label_format)
            worksheet.write(row, 3, breakdown['total_benefits'], total_format)
            row += 2

            # SECTION 2: DEDUCTIONS
            worksheet.merge_range(row, 0, row, 3, '2. DEDUCCIONES', section_deduction_format)
            row += 1

            if breakdown['deductions']:
                # Deductions header
                worksheet.write(row, 0, '#', title_format)
                worksheet.write(row, 1, 'Concepto / Fórmula / Cálculo', title_format)
                worksheet.merge_range(row, 2, row, 3, f'Monto ({currency.name})', title_format)
                row += 1

                # Deductions data
                for deduction in breakdown['deductions']:
                    worksheet.write(row, 0, deduction['number'], text_format)

                    # Concept with formula
                    concept_text = f"{deduction['name']}\n{deduction['formula']}\n{deduction['calculation']}"
                    worksheet.write(row, 1, concept_text, formula_format)
                    worksheet.set_row(row, 45)

                    worksheet.merge_range(row, 2, row, 3, deduction['amount'], money_format)
                    row += 1

                # Deductions subtotal
                worksheet.merge_range(row, 0, row, 2, 'TOTAL DEDUCCIONES:', total_label_format)
                worksheet.write(row, 3, breakdown['total_deductions'], total_format)
                row += 2
            else:
                worksheet.merge_range(row, 0, row, 3, 'No hay deducciones aplicables', text_format)
                row += 2

            # FINAL TOTAL
            worksheet.merge_range(row, 0, row, 2, 'TOTAL PRESTACIONES:', total_label_format)
            worksheet.write(row, 3, breakdown['total_benefits'], total_format)
            row += 1

            worksheet.merge_range(row, 0, row, 2, 'TOTAL DEDUCCIONES:', total_label_format)
            worksheet.write(row, 3, breakdown['total_deductions'], total_format)
            row += 1

            net_label_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'right',
                'bg_color': '#FFD700',
                'border': 2
            })
            net_value_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'num_format': f'{currency.symbol}#,##0.00',
                'align': 'right',
                'bg_color': '#FFD700',
                'border': 2
            })

            worksheet.merge_range(row, 0, row, 2, 'NETO A RECLAMAR:', net_label_format)
            worksheet.write(row, 3, breakdown['net_amount'], net_value_format)
            row += 2

            # NOTES
            notes_format = workbook.add_format({
                'font_size': 9,
                'align': 'left',
                'text_wrap': True,
                'bg_color': '#F8F9FA'
            })

            notes = []
            notes.append(f"• Salario Diario Base: {currency.symbol}{breakdown['daily_salary'] * 30:.2f} / 30 = {currency.symbol}{breakdown['daily_salary']:.2f}")
            notes.append(f"• Salario Diario Integral: {currency.symbol}{breakdown['integral_daily']:.2f}")

            if breakdown['bono_rate'] > 15:
                notes.append(f"• Tasa Bono Vacacional: 15 + ({breakdown['total_seniority_years']:.2f} - 1) = {breakdown['bono_rate']:.1f} días/año")

            if breakdown['original_hire_date'] and breakdown['original_hire_date'] != breakdown['contract'].date_start:
                notes.append(f"• Antigüedad calculada desde fecha original de contratación ({breakdown['original_hire_date'].strftime('%d/%m/%Y')})")

            if currency.name == 'VEB':
                notes.append(f"• Tipo de Cambio: {breakdown['exchange_rate']:.2f} VEB/USD")

            notes.append(f"• Estructura: {breakdown['structure_name']}")

            from datetime import datetime
            notes.append(f"• Fecha de Emisión: {datetime.now().strftime('%d de %B %Y')}")

            notes_text = '\n'.join(notes)
            worksheet.merge_range(row, 0, row + 3, 3, notes_text, notes_format)

        # Close workbook and get data
        workbook.close()
        output.seek(0)
        xlsx_data = output.read()
        output.close()

        # Generate filename
        if len(wizard.payslip_ids) == 1:
            filename = f"Relacion_Liquidacion_{wizard.payslip_ids[0].employee_id.name.replace(' ', '_')}_{currency.name}.xlsx"
        else:
            filename = f"Relacion_Liquidacion_Multiple_{currency.name}.xlsx"

        # Return file
        response = request.make_response(
            xlsx_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )

        return response
