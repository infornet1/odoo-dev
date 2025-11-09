from odoo import models
from odoo.tools.misc import format_amount
import re
from odoo.exceptions import UserError

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

class PurchaseReportXlsx(models.AbstractModel):
    _name = 'report.tdv_purchase_report.purchase_report_xlsx'
    _description = 'Report XLSX'
    _inherit = 'report.report_xlsx.abstract'


    def generate_xlsx_report(self, workbook, data, report):
        if not report.line_ids or not any(report.line_ids):
            raise UserError("Debe generar el informe antes de imprimir. Por favor, haga clic en 'Generar informe' primero.")

        def amount_format(amount,):
            return format_amount(self.env, amount, report.currency_id)

        def get_numbers(reference):
            numbers = re.findall(r'\d+', reference or "")
            return [int(number) for number in numbers]

        border = workbook.add_format(STYLES["border"])
        header = workbook.add_format(STYLES["header"])
        bold = workbook.add_format(STYLES["bold"])
        merge_format = workbook.add_format(STYLES["merge_format"])
        # merge_format1 = workbook.add_format(STYLES["merge_format1"])
        # merge_format2 = workbook.add_format(STYLES["merge_format2"])
        company_style = workbook.add_format(STYLES["company_style"])

        # Determinar cuántas columnas fijas hay antes de los impuestos
        fixed_cols = 4  # N°, Fecha, Cliente, RIF
        if report.show_nro_plan_import:
            fixed_cols += 1
        if report.show_nro_exp:
            fixed_cols += 1
        # Sumar las columnas fijas restantes
        fixed_cols += 5  # Nro Factura, Nro Control, Tipo Doc, Sin crédito fiscal, Total

        sheet = workbook.add_worksheet(report.name)

        company_style = workbook.add_format(STYLES["company_style"])
        border = workbook.add_format(STYLES["border"])
        bold = workbook.add_format(STYLES["bold"])

        start_date = report.date_from.strftime("%d/%m/%Y")
        end_date = report.date_to.strftime("%d/%m/%Y")
        company_address = report.company_id.partner_id.contact_address or ""
        company_vat = report.company_id.company_registry or report.company_id.vat or ""

        sheet.merge_range("A1:D2", report.company_id.name, company_style)
        sheet.merge_range("A3:G3", company_address, border)
        sheet.merge_range("A4:D4", "%s" % report.name, bold)
        sheet.merge_range("A5:B5", "RIF: %s" % company_vat, bold)
        sheet.merge_range("C5:D5", "Período: %s - %s" % (start_date, end_date), bold)

        row = 7
        col = 0

        # 1. Escribe los encabezados fijos
        header_fields = [
            "N°", "Fecha de Factura", "Cliente", "RIF"
        ]
        if report.show_nro_plan_import:
            header_fields.append("Número Plan. Import.")
        if report.show_nro_exp:
            header_fields.append("Número de Expediente")
        header_fields += [
            "Número de Factura", "Número de Control", "Tipo de Documento", "Sin crédito fiscal", "Total"
        ]

        # Escribe los encabezados fijos
        for idx, field in enumerate(header_fields):
            sheet.write(row, idx, field, header)

        # 2. Encabezados de impuestos (merge de 3 columnas por impuesto)
        tax_start_col = len(header_fields)
        tax_names = list(report.tax_totals.keys())
        for i, tax in enumerate(tax_names):
            start = tax_start_col + i * 3
            end = start + 2
            sheet.merge_range(row-1, start, row-1, end, tax, merge_format)
            sheet.write(row, start, "Base Imponible", header)
            sheet.write(row, start+1, "Alicuota", header)
            sheet.write(row, start+2, "Total", header)

        # 3. Escribe los datos
        for line_number, line in enumerate(report.line_ids.sorted(key=lambda l: (l.invoice_date, get_numbers(l.invoice_reference))), 1):
            row += 1
            col = 0
            values = [
                line_number,
                line.invoice_date.strftime("%d/%m/%Y") if line.invoice_date else "",
                line.partner_id.name or "",
                line.partner_id.vat or ""
            ]
            if report.show_nro_plan_import:
                values.append(getattr(line, 'import_plan_number', "") or "")
            if report.show_nro_exp:
                values.append(getattr(line, 'file_number', "") or "")
            values += [
                line.invoice_reference or "",
                line.control_number or "",
                MOVE_TYPE.get(line.invoice_type, ""),
                line.amount_exempt,
                line.amount_total
            ]
            # Escribe los valores fijos
            for v in values:
                sheet.write(row, col, v, border)
                col += 1

            # Escribe los impuestos (3 columnas por impuesto)
            for tax in tax_names:
                taxes = line.get_tax_totals_dict().get("taxes", [])
                tax_data = list(filter(lambda t: t["name"] == tax, taxes))
                if tax_data:
                    t = tax_data[0]
                    sheet.write(row, col, t["amount_untaxed"], border)
                    sheet.write(row, col+1, "%s%%" % t["tax"], border)
                    sheet.write(row, col+2, t["amount_tax"], border)
                else:
                    sheet.write(row, col, 0, border)
                    sheet.write(row, col+1, "0%", border)
                    sheet.write(row, col+2, 0, border)
                col += 3

        row += 5
        sheet.write(row, 7, "Resumen del Libro", header)
        sheet.write(row, 8, "Total", header)
        row += 1

        # Calcular bases imponibles por impuesto (sin 'sin crédito fiscal')
        base_imponible_por_impuesto = {}
        for line in report.line_ids:
            for tax in line.get_tax_totals_dict().get("taxes", []):
                tax_name = tax["name"]
                base_imponible_por_impuesto.setdefault(tax_name, 0)
                base_imponible_por_impuesto[tax_name] += tax["amount_untaxed"]

        # Mostrar Base Imponible (impuesto) y su impuesto, uno tras otro
        for tax_name in report.tax_totals.keys():
            # Base Imponible
            base = base_imponible_por_impuesto.get(tax_name, 0)
            sheet.write(row, 7, f"Base Imponible ({tax_name})", border)
            sheet.write(row, 8, base, border)
            row += 1
            # Impuesto
            impuesto = report.tax_totals.get(tax_name, 0)
            sheet.write(row, 7, tax_name, border)
            sheet.write(row, 8, impuesto, border)
            row += 1

        # # Subtotal
        # sheet.write(row, 7, "Subtotal", border)
        # sheet.write(row, 8, report.amount_untaxed, border)
        # row += 1

        # sheet.write(row, 7, "Impuestos", border)
        # sheet.write(row, 8, report.amount_tax, border)
        # row += 1

        # Sin crédito fiscal
        sheet.write(row, 7, "Sin crédito fiscal", border)
        sheet.write(row, 8, report.amount_exempt, border)
        row += 1
        # Total
        sheet.write(row, 7, "Total", border)
        sheet.write(row, 8, report.amount_total, border)

        sheet.set_column("A:A", 5)
        sheet.set_column("B:AZ", 25)
        sheet.set_column("H:H", 40)
