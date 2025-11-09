# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


DATE_EXPIRE = fields.date(2025, 9, 15)

class AccountMove(models.Model):
    _inherit = 'account.move'


    def print_freeform(self):
        # if fields.date.today() >= DATE_EXPIRE:
        #     raise ValidationError(_("Your license has expired, contact 3Dvision to renew it"))
        return super().print_freeform()

    def _get_rate_ueipab(self, from_currency, to_currency):
        return self.env["res.currency"]._get_conversion_rate(
            from_currency,
            to_currency,
            self.company_id,
            self.fiscal_print_date or fields.Date.today(),
        )

    @api.depends("tax_totals")
    def _compute_fiscal_tax_totals(self):
        for move in self:
            if move.tax_totals:

                def _format(amount, currency=None):
                    return formatLang(
                        self.env,
                        amount,
                        currency_obj=currency or move.fiscal_currency_id,
                    )

                def _convert(amount, currency=None):
                    if move.currency_id:
                        return move.currency_id._convert(
                            from_amount=amount,
                            to_currency=currency or move.fiscal_currency_id,
                            company=move.company_id,
                            date=move.fiscal_print_date or fields.date.today(),
                            round=True,
                        )
                    return amount

                ref_json = {}
                tax_totals = move.tax_totals
                converted_subtotals = []
                converted_subtotal_groups = {}

                for item in tax_totals["subtotals"]:
                    converted_subtotals += [
                        {
                            **item,
                            "amount": _convert(item["amount"]),
                            "formatted_amount": _format(
                                _convert(item["amount"])
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
                                "tax_group_amount": _convert(
                                    tax["tax_group_amount"]
                                ),
                                "tax_group_base_amount": _convert(
                                    tax["tax_group_base_amount"]
                                ),
                                "formatted_tax_group_amount": _format(
                                    _convert(tax["tax_group_amount"])
                                ),
                                "formatted_tax_group_base_amount": _format(
                                    _convert(tax["tax_group_base_amount"])
                                ),
                            }
                        )

                converted_amounts = {
                    "amount_total": _convert(tax_totals["amount_total"]),
                    "amount_untaxed": _convert(tax_totals["amount_untaxed"]),
                    "amount_untaxed": 335.26,
                    "groups_by_subtotal": converted_subtotal_groups,
                }

                ref_json.update(
                    {
                        **tax_totals,
                        **converted_amounts,
                        "subtotals": converted_subtotals,
                        "formatted_amount_total": _format(
                            converted_amounts["amount_total"]
                        ),
                        "formatted_amount_untaxed": _format(
                            converted_amounts["amount_untaxed"]
                        ),
                    }
                )

                move.fiscal_tax_totals = ref_json
            else:
                move.fiscal_tax_totals = None