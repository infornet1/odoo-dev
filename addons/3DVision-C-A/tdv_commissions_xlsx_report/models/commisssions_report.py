# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError
from collections import defaultdict

PAYMENT_MODE = {"total": "Pagado", "partial": "Parcial", "sale": "Venta"}

CLIENT_COL = 0
DATE_COL = 1
INVOICE_COL = 2
BASE_COL = 3
PAID_COL = 4
TOTAL_COL = 5
PERCENT_COL = 6
REFERENCE_COL = 7


class CommissionsReport(models.AbstractModel):
    _name = "report.tdv_commissions_xlsx_report.commissions"
    _inherit = "report.report_xlsx.abstract"
    _description = "report for commissions"

    def generate_xlsx_report(self, workbook, data, commissions):
        for commission in commissions:
            if commission.state != "done":
                raise UserError("The document should be confirmed!!")
            partner_dict = defaultdict(
                lambda: defaultdict(
                    lambda: defaultdict(
                        lambda: {"total": 0, "base": 0, "payment": 0, "lines": []}
                    )
                )
            )
            # one sheet by partner
            for line in commission.sale_commission_line_ids:
                if (
                    line.move_line_id
                    not in partner_dict[line.partner_id][
                        line.move_line_id.move_id.partner_id
                    ][line.move_line_id.move_id]["lines"]
                ):
                    partner_dict[line.partner_id][line.move_line_id.move_id.partner_id][
                        line.move_line_id.move_id
                    ]["base"] += line.subtotal
                    partner_dict[line.partner_id][line.move_line_id.move_id.partner_id][
                        line.move_line_id.move_id
                    ]["lines"].append(line.move_line_id)
                partner_dict[line.partner_id][line.move_line_id.move_id.partner_id][
                    line.move_line_id.move_id
                ]["total"] += line.total_amount
                partner_dict[line.partner_id][line.move_line_id.move_id.partner_id][
                    line.move_line_id.move_id
                ]["payment"] += (line.payment_amount * line.subtotal)

            for partner, customers in partner_dict.items():
                row = 5
                sheet = workbook.add_worksheet(partner.name)
                bold = workbook.add_format({"bold": True, "bg_color": "#999999"})
                subtotal = workbook.add_format({"bold": True, "bg_color": "#F4FF83"})
                normal = workbook.add_format()
                red = workbook.add_format({"font_color": "red"})
                total = 0
                base = 0
                payment = 0
                sheet.write(1, 0, "Vendedor", bold)
                sheet.write(1, 1, partner.name)
                sheet.write(2, 0, "Modalidad de Pago", bold)
                sheet.write(2, 1, PAYMENT_MODE[partner.generation_mode])

                sheet.write(4, CLIENT_COL, "Cliente", bold)
                sheet.write(4, DATE_COL, "Fecha", bold)
                sheet.write(4, INVOICE_COL, "Factura", bold)
                sheet.write(4, BASE_COL, "Base Imponible Factura", bold)
                sheet.write(4, PAID_COL, "Pagado en Factura", bold)
                sheet.write(4, TOTAL_COL, "Total Comision", bold)
                sheet.write(4, PERCENT_COL, "% Aplicado", bold)
                sheet.write(4, REFERENCE_COL, "Referencia", bold)
                for customer, invoices in customers.items():
                    is_first = True
                    customer_data = {"base": 0, "paid": 0, "total": 0}
                    for invoice, values in invoices.items():
                        style = normal if invoice.move_type == "out_invoice" else red
                        if is_first:
                            sheet.write(row, CLIENT_COL, customer.name)
                            is_first = False
                        sheet.write(
                            row,
                            DATE_COL,
                            invoice.invoice_date.strftime("%d/%m/%Y"),
                            style,
                        )
                        sheet.write(row, INVOICE_COL, invoice.name, style)
                        sheet.write(row, BASE_COL, values["base"], style)
                        sheet.write(row, PAID_COL, values["payment"], style)
                        sheet.write(row, TOTAL_COL, values["total"], style)
                        percent = round((values["total"] * 100) / values["base"], 2)
                        sheet.write(row, PERCENT_COL, percent, style)
                        sheet.write(
                            row, REFERENCE_COL, invoice.payment_reference, style
                        )
                        customer_data["base"] += values["base"]
                        customer_data["paid"] += values["payment"]
                        customer_data["total"] += values["total"]
                        total += values["total"]
                        base += values["base"]
                        payment += values["payment"]
                        row += 1
                    sheet.write(row, CLIENT_COL, "Subtotal", subtotal)
                    sheet.write(row, DATE_COL, "", subtotal)
                    sheet.write(row, INVOICE_COL, "", subtotal)
                    sheet.write(row, BASE_COL, customer_data["base"], subtotal)
                    sheet.write(row, PAID_COL, customer_data["paid"], subtotal)
                    sheet.write(row, TOTAL_COL, customer_data["total"], subtotal)
                    sheet.write(row, PERCENT_COL, "", subtotal)
                    row += 1
                sheet.write(row, CLIENT_COL, "Total", bold)
                sheet.write(row, DATE_COL, "", bold)
                sheet.write(row, INVOICE_COL, "", bold)
                sheet.write(row, BASE_COL, base, bold)
                sheet.write(row, PAID_COL, payment, bold)
                sheet.write(row, TOTAL_COL, total, bold)
                sheet.write(row, PERCENT_COL, "", bold)
                sheet.set_column("A:C", 20)
                sheet.set_column("D:D", 25)
                sheet.set_column("E:H", 20)
