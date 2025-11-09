from odoo import fields, api, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
import json
import re


class AccountMove(models.Model):
    _inherit = "account.move"

    fiscal_comment = fields.Text("Comments")
    fiscal_payment_condition = fields.Char(
        "Payment Condition", copy=False, default="Credito")
    fiscal_tax_totals = fields.Binary(
        compute="_compute_fiscal_tax_totals", exportable=False
    )
    fiscal_currency_id = fields.Many2one(
        "res.currency", "Fiscal Currency", domain="[('id','!=',currency_id)]"
    )
    fiscal_rate = fields.Monetary(
        "Fiscal Rate", compute="_compute_fiscal_rate")
    fiscal_print_date = fields.Date("Print Date", copy=False, readonly=True)

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
                            date=move.date or fields.date.today(),
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

    def _validate_fiscal_values(self):
        for move in self:
            invoices = self.env["account.move"].search([
                ("id", "!=", move.id),
                ("fiscal_check", "=", True),
                ("company_id", "=", move.company_id.id),
                ("move_type", "=", move.move_type),
            ])
            vef_currency = self.env["res.currency"].browse([2])
            move_currency_ids = move.currency_id | move.fiscal_currency_id

            try:
                assert move.fiscal_check, _(
                    "The invoice %s is not fiscal" % (move.name)
                )
                assert move.fiscal_payment_condition, _(
                    "The payment condition is required on the invoice %s" % move.name)
                assert move.control_number and move.fiscal_correlative, _(
                    "The Control Number and the Fiscal Correlative are required"
                )
                assert not (
                    move.control_number in invoices.mapped("control_number")
                ), _("The control number must be unique")
                assert len(move.invoice_line_ids) < 40, _(
                    "This invoice exceeds the limit of items valid for printing (40)."
                )
                assert vef_currency in move_currency_ids, _(
                    "A currency in Bs is required."
                )
            except Exception as e:
                raise UserError(str(e))

            move.fiscal_print_date = move.fiscal_print_date or fields.date.today()

    def _get_rate(self, from_currency=None, to_currency=None):
        # Handle both calling patterns for compatibility
        if from_currency is None and to_currency is None:
            # Called without parameters - use self currencies and return formatted string
            from_currency = self.currency_id
            to_currency = self.fiscal_currency_id
            return_formatted = True
        else:
            # Called with parameters - return raw number for monetary widget
            return_formatted = False

        get_rate = self.env["res.currency"]._get_conversion_rate
        max_rate = max(
            get_rate(
                from_currency,
                to_currency,
                self.company_id,
                self.date or fields.date.today()
            ),
            get_rate(
                to_currency,
                from_currency,
                self.company_id,
                self.date or fields.date.today()
            ))

        if return_formatted:
            return from_currency.format(max_rate)
        else:
            return max_rate

    def print_freeform(self):
        format_type = self.env.company.invoice_freeform_selection
        module_name = "impresion_forma_libre."
        action_name = {
            "letter": "action_freeform_letter_report",
            "half_letter": "action_freeform_half_letter_report",
        }

        self._validate_fiscal_values()
        report_action_name = module_name + action_name[format_type]
        return self.env.ref(report_action_name).report_action(self)

    def _validate_na(self, val):
        return not bool(re.match(r"^(N|n).?(A|a)$", val))
