from odoo import models
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
}

class PurchaseReportXlsxRetention(models.AbstractModel):
    _inherit = 'report.tdv_purchase_report.purchase_report_xlsx'

    def generate_xlsx_report(self, workbook, data, report):
        # Llamar al método original para generar el reporte básico
        super(PurchaseReportXlsxRetention, self).generate_xlsx_report(workbook, data, report)

        def get_numbers(reference):
            numbers = re.findall(r'\d+', reference or "")
            return [int(number) for number in numbers]

        border = workbook.add_format(STYLES["border"])
        header = workbook.add_format(STYLES["header"])
        merge_format = workbook.add_format(STYLES["merge_format"])

        # Calcular la posición real de inicio para las columnas de retención
        sheet = workbook.worksheets()[0]
        col = 4  # N°, Fecha, Cliente, RIF
        if report.show_nro_plan_import:
            col += 1
        if report.show_nro_exp:
            col += 1
        col += 5  # Nro Factura, Nro Control, Tipo Doc, Sin crédito fiscal, Total
        col += len(report.tax_totals) * 3
        row = 7  # Inicializamos la fila de inicio para la cabecera

        sheet.merge_range(row-1, col, row-1, col+3, "Retención IVA", merge_format)

        # Agregar nombres de columnas para las retenciones
        sheet.write(row, col, "N° Comprobante", header)
        sheet.write(row, col+1, "Fecha", header)
        sheet.write(row, col+2, "Porcentaje", header)
        sheet.write(row, col+3, "Monto", header)

        # Agregar datos de retenciones en cada línea del reporte
        for line in report.line_ids.sorted(key=lambda l: (l.invoice_date, get_numbers(l.invoice_reference))):
            row += 1
            col_data = col
            sheet.write(row, col_data, line.retention_id.correlative or "", border)
            sheet.write(row, col_data+1, line.retention_id.date.strftime("%d/%m/%Y")
                if line.retention_id and line.retention_id.date
                else "", border
            )
            sheet.write(row, col_data+2, f"{line.retention_line_id.ret_tax_id.tax} %"
                if line.retention_line_id and line.retention_line_id.ret_tax_id
                else "", border
            )
            sheet.write(row, col_data+3, line.amount_detained, border)

        # === Agregar total de retenciones en el resumen del libro ===
        # Sumar solo los montos de las líneas que tienen retención
        total_retenciones = sum(
            line.amount_detained for line in report.line_ids
            if line.retention_id and line.amount_detained
        )

        # Buscar la fila donde está 'Total' y 'Sin crédito fiscal' en la columna 7
        row_total = None
        row_sin_credito = None
        for r in range(sheet.dim_rowmax):
            cell = sheet.table.get((r, 7), None)
            if cell and cell.v == "Sin crédito fiscal":
                row_sin_credito = r
            if cell and cell.v == "Total":
                row_total = r
                break

        if row_total is not None:
            # Guardar valor actual de Total
            total_val = sheet.table[(row_total, 8)].v
            # Escribir 'Total Retenciones' justo antes de 'Total'
            sheet.write(row_total, 7, "Retención IVA", border)
            sheet.write(row_total, 8, total_retenciones, border)
            # Escribir 'Total' una fila más abajo
            sheet.write(row_total+1, 7, "Total", border)
            sheet.write(row_total+1, 8, total_val, border)
        else:
            # Si no se encuentra, lo agregamos al final
            last_row = sheet.dim_rowmax
            sheet.write(last_row, 7, "Retención IVA", border)
            sheet.write(last_row, 8, total_retenciones, border)
            sheet.write(last_row+1, 7, "Total", border)
            sheet.write(last_row+1, 8, report.amount_total, border)


