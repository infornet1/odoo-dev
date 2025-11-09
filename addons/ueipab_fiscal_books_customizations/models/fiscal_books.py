from odoo import models, fields, api

class SaleBook(models.Model):
    _inherit = "tdv.sale.book"

    def _get_invoice_domain(self):
        return [
            ("company_id", "=", self.company_id.id),
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("fiscal_print_date", ">=", self.date_from),
            ("fiscal_print_date", "<=", self.date_to),
            ("state", "=", "posted"),
        ]


class SaleBookLine(models.Model):
    _inherit = "tdv.sale.book.line"

    def onchange_invoice_or_currency(self):
        super().onchange_invoice_or_currency()
        self.invoice_date = self.invoice_id.fiscal_print_date
