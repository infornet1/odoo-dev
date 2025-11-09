# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict

PURCHASE_TYPE = [
    ("all", "All"),
    ("fiscal", "Control number"),
    ("no_fiscal", "No control number"),
]


class PurchaseReport(models.Model):
    _name = "tdv.purchase.report"
    _description = "Purchase Report"

    name = fields.Char("Name", required=True)
    date_from = fields.Date("Date From", required=True)
    date_to = fields.Date("Date To", required=True)
    purchase_type = fields.Selection(
        PURCHASE_TYPE, "Purchase Type", default="all"
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        "Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many(
        "tdv.purchase.report.line", "purchase_report_id", "Purchase Book Lines")
    amount_untaxed = fields.Monetary(
        "Amount Untaxed",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True)
    amount_exempt = fields.Monetary(
        "Exempt Amount",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True)
    amount_tax = fields.Monetary(
        "Taxes",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True)
    amount_total = fields.Monetary(
        "Total",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True)
    tax_totals = fields.Binary("Tax Totals", compute="_compute_tax_totals")

    state = fields.Selection([
        ("draft", "Draft"),
        ("registered", "Registered"),
        ("cancelled", "Cancelled"),
    ], string="State", default="draft", required=True)

    show_nro_plan_import = fields.Boolean(string="Show Import Plan Number in XLSX", default=False)
    show_nro_exp = fields.Boolean(string="Show File Number in XLSX", default=False)

    @api.depends(
        "currency_id",
        "line_ids",
        "line_ids.amount_untaxed",
        "line_ids.amount_exempt",
        "line_ids.amount_tax",
        "line_ids.amount_total")
    def _compute_amounts(self):
        for book in self:
            book.amount_untaxed = sum(book.line_ids.mapped("amount_untaxed"))
            book.amount_exempt = sum(book.line_ids.mapped("amount_exempt"))
            book.amount_tax = sum(book.line_ids.mapped("amount_tax"))
            book.amount_total = sum(book.line_ids.mapped("amount_total"))

    @api.depends(
        "currency_id",
        "line_ids",
        "line_ids.amount_untaxed",
        "line_ids.amount_exempt",
        "line_ids.amount_tax",
        "line_ids.amount_total")
    def _compute_tax_totals(self):
        for book in self:
            if not book.line_ids:
                book.tax_totals = False
                continue
            tax_totals = defaultdict(int)
            # Usar el método seguro para obtener el dict
            tax_list = book.line_ids.mapped(lambda l: l.get_tax_totals_dict().get("taxes", []))

            for taxes in tax_list:
                for tax in taxes:
                    tax_totals[tax["name"]] += tax["amount_tax"]

            book.tax_totals = tax_totals


    @api.onchange("currency_id")
    def _onchange_currency_id(self):
        self.line_ids.mapped(lambda line: line.onchange_invoice_or_currency())

    def _get_invoice_domain(self):
        return [
            ("company_id", "=", self.company_id.id),
            ("move_type", "in", ["in_invoice", "in_refund"]),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("state", "=", "posted"),
        ]

    def generate(self):
        domain = self._get_invoice_domain()
        if self.purchase_type != "all":
            domain.append(
                ("control_number", "!=", False)
                if self.purchase_type == "fiscal"
                else ("control_number", "=", False)
            )
        line_invoices = self.line_ids.invoice_id.filtered_domain(domain)
        self.line_ids.filtered(
            lambda line: line.invoice_id not in line_invoices
        ).unlink()
        invoices = self.env["account.move"].search(domain) - line_invoices
        new_lines = self.env["tdv.purchase.report.line"].create(
            [
                {
                    "purchase_report_id": self.id,
                    "currency_id": self.currency_id.id,
                    "company_id": self.company_id.id,
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                    "invoice_id": invoice.id,
                }
                for invoice in invoices
            ]
        )
        if new_lines:
            new_lines.mapped(lambda line: line.onchange_invoice_or_currency())
        self.write({'state': 'registered'})
        return True

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You cannot delete a report that is not in Draft status.'))
        return super().unlink()

    def action_set_to_draft(self):
        # No permitir volver a borrador
        raise UserError(_('Cannot return to Draft status.'))

    @api.constrains("date_to", "date_from")
    def _constrains_date(self):
        for book in self:
            if not (book.date_from and book.date_to):
                raise UserError(_("The dates are required for registration"))

    def print_report(self):
        if not self.line_ids:
            raise UserError(_("You must generate the report before printing. Please click 'Generate Report' first."))
        return super().print_report()