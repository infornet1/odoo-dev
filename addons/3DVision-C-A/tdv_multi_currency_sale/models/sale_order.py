from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
import json


class SaleOrder(models.Model):
    _inherit = "sale.order"

    second_currency_id = fields.Many2one(
        "res.currency",
        "Second Currency",
        default=lambda self: self.env.company.second_currency_id,
        domain='[("id", "!=", currency_id)]',
    )
    company_currency_id = fields.Many2one(
        string="Company Currency", related="company_id.currency_id"
    )
    second_company_currency_id = fields.Many2one(
        string="Second Company Currency",
        related="company_id.second_currency_id",
    )
    second_amount_untaxed = fields.Monetary(
        "Second Untaxed Amount",
        currency_field="second_currency_id",
        compute="_compute_second_amounts",
    )
    second_amount_tax = fields.Monetary(
        "Second Taxed",
        currency_field="second_currency_id",
        compute="_compute_second_amounts",
    )
    second_amount_total = fields.Monetary(
        "Second Total",
        currency_field="second_currency_id",
        compute="_compute_second_amounts",
    )
    amount_total_in_company_currency = fields.Monetary(
        "Total in Company Currency",
        currency_field="company_currency_id",
        compute="_compute_second_amounts",
    )
    second_amount_total_in_company_currency = fields.Monetary(
        "Total in Company Second Currency",
        currency_field="second_company_currency_id",
        compute="_compute_second_amounts",
    )
    second_tax_totals = fields.Binary(
        compute="_compute_second_tax_totals", exportable=False
    )
    rate_string = fields.Char("Rate", compute="_compute_rate_string")
    second_currency_rate = fields.Char("Second Rate", compute="_compute_rate_string", exportable=False)
    show_second_currency_rate = fields.Boolean("Show Second Currency Rate", default=True)

    def _convert(self, amount, to_currency=None):
        self.ensure_one()
        if self.currency_id:
            return self.currency_id._convert(
                from_amount=amount,
                to_currency=to_currency or self.second_currency_id,
                company=self.company_id,
                date=self.date_order or fields.date.today(),
                round=True,
            )
        return amount

    @api.depends(
        "currency_id", "second_currency_id", "date_order", "amount_total"
    )
    def _compute_second_amounts(self):
        for order in self:
            order.second_amount_untaxed = order._convert(order.amount_untaxed)
            order.second_amount_tax = order._convert(order.amount_tax)
            order.second_amount_total = order._convert(order.amount_total)
            order.amount_total_in_company_currency = order._convert(
                order.amount_total, order.company_currency_id
            )
            order.second_amount_total_in_company_currency = order._convert(
                order.amount_total, order.second_company_currency_id
            )

    @api.depends("currency_id", "second_currency_id", "date_order")
    def _compute_rate_string(self):
        for order in self:
            rate_string = ""
            order.second_currency_rate = ""
            if order.currency_id and order.second_currency_id:
                rate = self.env["res.currency"]._get_conversion_rate(
                    from_currency=order.currency_id,
                    to_currency=order.second_currency_id,
                    company=order.company_id,
                    date=order.date_order or fields.date.today(),
                )
                inverse_rate = self.env["res.currency"]._get_conversion_rate(
                    from_currency=order.second_currency_id,
                    to_currency=order.currency_id,
                    company=order.company_id,
                    date=order.date_order or fields.date.today(),
                )

                rate_string = (
                    "("
                    + formatLang(self.env, 1, currency_obj=order.currency_id)
                    + " = "
                    + formatLang(
                        self.env, rate, currency_obj=order.second_currency_id
                    )
                    + ")"
                )
                report_rate = max([rate, inverse_rate])
                order.second_currency_rate = formatLang(self.env, report_rate,
                    currency_obj=order.currency_id if rate <= inverse_rate else order.second_currency_id
                    )
            order.rate_string = rate_string

    @api.depends("tax_totals", "second_currency_id", "date_order")
    def _compute_second_tax_totals(self):
        for order in self:
            ref_json = None
            if order.tax_totals:
                ref_json = {}
                tax_totals = order.tax_totals
                lang_env = self.with_context(lang=order.partner_id.lang).env
                converted_subtotals = []
                converted_subtotal_groups = {}

                for item in tax_totals["subtotals"]:
                    converted_subtotals += [
                        {
                            **item,
                            "amount": order._convert(item["amount"]),
                            "formatted_amount": formatLang(
                                lang_env,
                                order._convert(item["amount"]),
                                currency_obj=order.second_currency_id,
                            ),
                        }
                    ]

                for key, value in tax_totals["groups_by_subtotal"].items():
                    converted_subtotal_groups[key] = []
                    for tax in value:
                        converted_subtotal_groups[key].append(
                            {
                                **tax,
                                "tax_group_name": tax["tax_group_name"],
                                "tax_group_amount": order._convert(
                                    tax["tax_group_amount"]
                                ),
                                "tax_group_base_amount": order._convert(
                                    tax["tax_group_base_amount"]
                                ),
                                "formatted_tax_group_amount": formatLang(
                                    lang_env,
                                    order._convert(
                                        tax["tax_group_amount"],
                                    ),
                                    currency_obj=order.second_currency_id,
                                ),
                                "formatted_tax_group_base_amount": formatLang(
                                    lang_env,
                                    order._convert(
                                        tax["tax_group_base_amount"],
                                    ),
                                    currency_obj=order.second_currency_id,
                                ),
                            }
                        )

                converted_amounts = {
                    "amount_total": order._convert(
                        tax_totals["amount_total"],
                    ),
                    "amount_untaxed": order._convert(
                        tax_totals["amount_untaxed"],
                    ),
                    "groups_by_subtotal": converted_subtotal_groups,
                }

                ref_json.update(
                    {
                        **tax_totals,
                        **converted_amounts,
                        "subtotals": converted_subtotals,
                        "formatted_amount_total": formatLang(
                            lang_env,
                            converted_amounts["amount_total"],
                            currency_obj=order.second_currency_id,
                        ),
                        "formatted_amount_untaxed": formatLang(
                            lang_env,
                            converted_amounts["amount_untaxed"],
                            currency_obj=order.second_currency_id,
                        ),
                    }
                )

            order.second_tax_totals = ref_json
