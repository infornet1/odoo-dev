from odoo import models
from odoo.tools.misc import format_amount
import re

STYLES = {
    "border": {
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    },
    "header": {
        "bold": True,
        "bg_color": "#999999",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
    },
    "bold": {
        "bold": True,
        "bg_color": "#999999",
        "align": "center",
        "valign": "vcenter",
        "border": 1,
    },
    "merge_format": {
        "bold": 1,
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "fg_color": "yellow",
    },
    "merge_format1": {
        "bold": 1,
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "fg_color": "green",
    },
    "merge_format2": {
        "bold": 1,
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "fg_color": "red",
    },
    "company_style": {
        "font_size": 16,
        "bold": True,
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    }
}

MOVE_TYPE = {
    False: "",
    "01": "01 - Factura",
    "02": "02 - Nota de débito",
    "03": "03 - Nota de crédito",
}

class SalesBookReport(models.AbstractModel):
    _name = 'report.tdv_sales_book_report.xlsx_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Sales book report'


    def generate_xlsx_report(self, workbook, data, report):

        def amount_format(amount):
            # return format_amount(self.env, amount, report.currency_id)
            return amount

        def validate_format(line, amount, entity_flag):
            if not line.is_legal_entity == entity_flag:
                amount = 0
            return amount

        def get_numbers(reference):
            numbers = re.findall(r'\d+', reference or "")
            return [int(number) for number in numbers]

        border = workbook.add_format(STYLES["border"])
        header = workbook.add_format(STYLES["header"])
        bold = workbook.add_format(STYLES["bold"])
        merge_format = workbook.add_format(STYLES["merge_format"])
        merge_format1 = workbook.add_format(STYLES["merge_format1"])
        merge_format2 = workbook.add_format(STYLES["merge_format2"])
        company_style = workbook.add_format(STYLES["company_style"])

        row = 7
        line_number = 0
        start_date = report.date_from.strftime("%d/%m/%Y")
        end_date = report.date_to.strftime("%d/%m/%Y")
        company_address = report.company_id.partner_id.contact_address or ""
        company_vat = report.company_id.company_registry or report.company_id.vat or ""
        tax_lines = list(item["taxes"] for item in report.line_ids.mapped("tax_totals"))
        taxes_name = set()

        for tax in tax_lines:
            taxes_name.update(t["name"] for t in tax)

        tax_padding = len(taxes_name) * 3
        start_natural = 10
        end_natural = (start_natural + tax_padding) - 1
        start_legal = end_natural + 1
        end_legal = (start_legal + tax_padding) - 1

        sheet = workbook.add_worksheet(report.name)
        sheet.merge_range("A1:D2", report.company_id.name, company_style)
        sheet.merge_range("A3:D3", company_address, border)
        sheet.merge_range("A4:D4", "%s" %report.name, bold)
        sheet.merge_range("A5:B5", "RIF: %s" %company_vat, bold)
        sheet.merge_range("C5:D5", "Periodo: %s - %s" %(start_date, end_date), bold)

        if taxes_name:
            sheet.merge_range(5, start_natural, 5, end_natural, "Persona Natural", merge_format1)
            sheet.merge_range(5, start_legal, 5, end_legal, "Persona Juridica", merge_format2)

        sheet.write(row, 0, "N°", header)
        sheet.write(row, 1, "Fecha de Factura", header)
        sheet.write(row, 2, "Cliente", header)
        sheet.write(row, 3, "RIF", header)
        sheet.write(row, 4, "Numero de Factura", header)
        sheet.write(row, 5, "Numero de Control", header)
        sheet.write(row, 6, "Tipo de Documento", header)
        sheet.write(row, 7, "Documento Afectado", header)
        sheet.write(row, 8, "Total Factura", header)
        sheet.write(row, 9, "Sin credito fiscal", header)

        for tax in taxes_name:
            sheet.merge_range(6, start_natural, 6, start_natural + 2, tax, merge_format)
            sheet.write(row, start_natural, "Base Imponible", header)
            sheet.write(row, start_natural + 1, "Alicuota", header)
            sheet.write(row, start_natural + 2, "Total", header)

            sheet.merge_range(6, start_legal, 6, start_legal + 2, tax, merge_format)
            sheet.write(row, start_legal, "Base Imponible", header)
            sheet.write(row, start_legal + 1, "Alicuota", header)
            sheet.write(row, start_legal + 2, "Total", header)

            start_natural += 3
            start_legal += 3


        for line in report.line_ids.sorted(key=lambda l: (l.invoice_date, get_numbers(l.invoice_reference))):
            row += 1
            line_number += 1
            sheet.write(row, 0, line_number, border)
            sheet.write(row, 1, line.invoice_date.strftime("%d/%m/%Y") or "", border)
            sheet.write(row, 2, line.partner_id.name, border)
            sheet.write(row, 3, line.partner_id.vat or "", border)
            sheet.write(row, 4, line.invoice_reference or "", border)
            sheet.write(row, 5, line.control_number or "", border)
            sheet.write(row, 6, MOVE_TYPE[line.invoice_type], border)
            sheet.write(row, 7, line.reversal_move_reference or "", border)
            sheet.write(row, 8, amount_format(line.amount_total), border)
            sheet.write(row, 9, amount_format(line.amount_exempt), border)

            tax_col = 10
            for name in taxes_name:
                tax = list(filter(lambda t: t["name"] == name, line.tax_totals["taxes"]))
                if tax:
                    tax = tax.pop()
                    sheet.write(row, tax_col, validate_format(line, tax["amount_untaxed"], False), border)
                    sheet.write(row, tax_col + 1, "%s%%" %tax["tax"] if not line.is_legal_entity else "0%", border)
                    sheet.write(row, tax_col + 2, validate_format(line, tax["amount_tax"], False), border)
                    sheet.write(row, tax_col + tax_padding, validate_format(line, tax["amount_untaxed"], True), border)
                    sheet.write(row, tax_col + tax_padding + 1, "%s%%" %tax["tax"] if line.is_legal_entity else "0%", border)
                    sheet.write(row, tax_col + tax_padding + 2, validate_format(line, tax["amount_tax"], True), border)
                else:
                    sheet.write(row, tax_col, validate_format(line,0, True), border)
                    sheet.write(row, tax_col + 1, "0%", border)
                    sheet.write(row, tax_col + 2, validate_format(line,0, True), border)
                    sheet.write(row, tax_col + tax_padding, validate_format(line,0, True), border)
                    sheet.write(row, tax_col + tax_padding + 1, "0%", border)
                    sheet.write(row, tax_col + tax_padding + 2, validate_format(line,0, True), border)
                tax_col += 3


        row += 5
        sheet.write(row, 7, "Resumen del Libro", header)
        sheet.write(row, 8, "Total", header)
        row += 1

        if report.tax_totals:
            for tax, amount in report.tax_totals["natural"].items():
                sheet.write(row, 7, "%s (Natural)" %tax, border)
                sheet.write(row, 8, amount_format(amount), border)
                row += 1

            for tax, amount in report.tax_totals["legal"].items():
                sheet.write(row, 7, "%s (Juridico)" %tax, border)
                sheet.write(row, 8, amount_format(amount), border)
                row += 1

        sheet.write(row, 7, "Base Imponible", border)
        sheet.write(row+1, 7, "Sin credito fiscal", border)
        sheet.write(row+2, 7, "Impuestos", border)
        sheet.write(row+3, 7, "Total", border)
        sheet.write(row, 8, amount_format(report.amount_untaxed), border)
        sheet.write(row+1, 8, amount_format(report.amount_exempt), border)
        sheet.write(row+2, 8, amount_format(report.amount_tax), border)
        sheet.write(row+3, 8, amount_format(report.amount_total), border)

        sheet.set_column("A:A", 5)
        sheet.set_column("B:AZ", 25)