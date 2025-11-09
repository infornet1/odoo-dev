# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict
import json

INVOICE_DOMAIN = """[
    ('company_id','=',company_id),
    ('move_type','in',['out_invoice','out_refund']),
    ('date','>=',date_from),
    ('date','<=',date_to),
    ('state','=','posted')
]"""

INVOICE_TYPE = [
    ("01", "01 - Invoice"),
    ("02", "02 - Debit Note"),
    ("03", "03 - Credit Note"),
]


class SaleBookLine(models.Model):
    _name = "tdv.sale.book.line"
    _description = "Fiscal Sales Book Lines developed by 3DVision"
    _order = "invoice_date desc, invoice_reference"

    sale_book_id = fields.Many2one("tdv.sale.book", "Sale Book")
    invoice_id = fields.Many2one(
        "account.move", "Invoice", domain=INVOICE_DOMAIN
    )

    company_id = fields.Many2one(related="sale_book_id.company_id")
    currency_id = fields.Many2one(related="sale_book_id.currency_id")
    date_from = fields.Date(related="sale_book_id.date_from")
    date_to = fields.Date(related="sale_book_id.date_to")
    partner_id = fields.Many2one(related="invoice_id.partner_id")
    is_legal_entity = fields.Boolean(related="partner_id.is_legal_entity", readonly=False)
    invoice_reference = fields.Char(related="invoice_id.fiscal_correlative", readonly=False)
    control_number = fields.Char(related="invoice_id.control_number", readonly=False)
    reversal_move_reference = fields.Char(related="invoice_id.reversed_entry_id.fiscal_correlative", string="Affected document", readonly=False)
    invoice_date = fields.Date("Invoice Date")
    invoice_type = fields.Selection(INVOICE_TYPE, "Document Type")
    amount_untaxed = fields.Monetary("Amount Untaxed", currency_field="currency_id")
    amount_tax = fields.Monetary("Tax", currency_field="currency_id")
    amount_exempt = fields.Monetary("Exempt Amount", currency_field="currency_id")
    amount_total = fields.Monetary("Amount Total", currency_field="currency_id")
    tax_totals = fields.Binary("Totals", compute="_compute_tax_totals", exportable=False)

    @api.depends("invoice_id")
    def _compute_tax_totals(self):
        for book_line in self:
            def convert(amount):
                if not (book_line.invoice_id and book_line.invoice_id.currency_id):
                    return amount

                return book_line.invoice_id.currency_id._convert(
                    from_amount=amount,
                    to_currency=book_line.currency_id,
                    company=book_line.company_id,
                    date=book_line.invoice_id.invoice_date or fields.date.today(),
                    round=True,
                )

            tax_totals = defaultdict(int, {"taxes": []})
            sign = 1 if book_line.invoice_id.move_type == "out_invoice" else -1
            lines = book_line.invoice_id.invoice_line_ids
            taxes = lines.mapped("tax_ids") \
                    .filtered_domain([("name", "not ilike", "exento")])

            for tax in taxes:
                aux_dict = defaultdict(int, {"name": tax.name})
                aux_dict["tax"] = tax.amount
                for line in lines.filtered(lambda l: l.tax_ids >= tax):
                    aux_dict["amount_untaxed"] += convert(sign * line.price_subtotal)
                    aux_dict["amount_tax"] += convert(sign * (line.price_subtotal * tax.amount / 100))
                tax_totals["taxes"].append(aux_dict)


            tax_totals["amount_exempt"] = convert(sign *
                sum(lines.filtered_domain([("tax_ids.name", "ilike", "exento")])
                    .mapped("price_subtotal"))
            )

            book_line.tax_totals = tax_totals


    @api.onchange("invoice_id", "currency_id")
    def onchange_invoice_or_currency(self):
        def convert(amount):
            if not (self.invoice_id and self.invoice_id.currency_id):
                return amount

            return self.invoice_id.company_currency_id._convert(
                from_amount=amount,
                to_currency=self.currency_id,
                company=self.company_id,
                date=self.invoice_id.invoice_date or fields.date.today(),
                round=True,
            )

        self.invoice_date = self.invoice_id.invoice_date
        self.invoice_type = (
            "01" if self.invoice_id.move_type == "out_invoice" else "03"
        )

        self._compute_tax_totals()
        self.amount_exempt = self.tax_totals["amount_exempt"] if self.tax_totals else 0
        self.amount_untaxed = convert(self.invoice_id.amount_untaxed_signed) - self.amount_exempt
        self.amount_tax = convert(self.invoice_id.amount_tax_signed)
        self.amount_total = convert(self.invoice_id.amount_total_signed)


    @api.constrains("invoice_date")
    def _constrains_invoice_date(self):
        for line in self:
            if line.invoice_id and not line.invoice_date:
                raise UserError(
                    _(
                        "The date on the invoice %s is required"
                        % line.invoice_id.name
                    )
                )