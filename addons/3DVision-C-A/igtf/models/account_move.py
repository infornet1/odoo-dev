from odoo import fields, api, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
from functools import reduce
import json


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_igtf = fields.Monetary(
        "IGTF", compute="_compute_amount_igtf", currency_field="company_currency_id")

    def _get_igtf_amount_in_currency(self, currency=None):
        amount_igtf = 0
        payments = self._get_reconciled_payments()
        amount_igtf += sum(
            payments.mapped(
                lambda p: p.currency_id._convert(
                    from_amount=p.igtf_tax,
                    to_currency=currency or self.currency_id,
                    company=self.company_id,
                    date=fields.datetime.now(),
                    round=True,
                )
            )
        )

        return amount_igtf

    def get_payments_for_fiscal_machine(self):
        res = super().get_payments_for_fiscal_machine()
        for invoice in res:
            for payment in invoice["payments"]:
                payment["is_igtf"] = self.env["account.journal"].browse(
                    payment["journal_id"]).is_igtf
        return res

    def _get_igtf(self, currency=None):
        self.ensure_one()

        # Early return for new/unsaved records (prevents SQL IN () error during onchange)
        # NewId records don't have real database IDs yet
        if not self.id or not isinstance(self.id, int):
            return 0

        # Early return if no receivable/payable lines with real database IDs
        receivable_payable_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
        )
        # Filter to only real integer IDs (exclude NewId)
        real_ids = [lid for lid in receivable_payable_lines.ids if isinstance(lid, int)]
        if not real_ids:
            return 0

        def filter_partial_lines(line):
            move = line["aml"].move_id
            return move.payment_id and move.payment_id.is_igtf

        def get_amount(line):
            return line["currency"]._convert(
                from_amount=line["amount"] * 0.03,
                to_currency=currency or self.currency_id,
                company=self.company_id,
                date=self.date or fields.date.today(),
                round=True,
            )

        partial_lines = self._get_all_reconciled_invoice_partials()
        conciliated_amount = 0
        filter_lines = filter(filter_partial_lines, partial_lines)
        conciliated_amount = sum(get_amount(line) for line in filter_lines)

        return conciliated_amount

    def _get_reconciled_payments_amount(self):
        self.ensure_one()

        def get_amount(payment):
            return payment.currency_id._convert(
                from_amount=payment.amount,
                to_currency=payment.currency_id,
                company=payment.company_id,
                date=payment.date,
                round=True
            )

        payments = self._get_reconciled_payments().filtered("is_igtf")
        amount_payments = sum(get_amount(payment) for payment in payments)

        return amount_payments

    @api.depends("amount_residual")
    def _compute_amount_igtf(self):
        for move in self:
            move.amount_igtf = move._get_igtf(move.company_currency_id)

    @api.depends(
        "line_ids.tax_base_amount",
        "line_ids.amount_currency",
        "partner_id",
        "line_ids.tax_line_id",
        "currency_id",
        "amount_total",
        "amount_untaxed",
        "line_ids.amount_residual",
    )
    def _compute_tax_totals(self):
        res = super()._compute_tax_totals()

        def format_amount(amount):
            return formatLang(self.env, amount, currency_obj=invoice.currency_id)

        for invoice in self:
            widget = invoice.tax_totals
            amount_igtf = invoice._get_igtf()
            amount_payments = invoice._get_reconciled_payments_amount()

            if not (widget and amount_igtf):
                return res

            aux_key = _("Untaxed Amount")
            tax_groups = widget["groups_by_subtotal"].get(aux_key, [])
            tax_groups.append({
                "tax_group_name": "IGTF 3%",
                "tax_group_amount": amount_igtf,
                "tax_group_base_amount": amount_payments,
                "formatted_tax_group_amount": format_amount(amount_igtf),
                "formatted_tax_group_base_amount": format_amount(amount_payments),
            })

            total_amount = widget["amount_total"] + amount_igtf

            widget.update({
                "amount_total": total_amount,
                "formatted_amount_total": format_amount(total_amount),
            }
            )
        invoice.tax_totals = widget

    @api.depends("move_type", "line_ids.amount_residual")
    def _compute_payments_widget_reconciled_info(self):
        super()._compute_payments_widget_reconciled_info()

        for move in self:
            igtf_move_ids = self.env["account.move"]
            payments_with_igtf = move._get_reconciled_payments().filtered(
                "is_igtf"
            )

            if move.invoice_payments_widget:
                for payment in payments_with_igtf:
                    igtf_move_ids |= self.env["account.move"].search(
                        [
                            ("invoice_origin", "=", payment.name),
                            ("company_id", "=", move.company_id.id),
                        ]
                    )

                widget = move.invoice_payments_widget

                if igtf_move_ids:
                    if widget and widget["content"]:
                        widget["content"] += [
                            {
                                "name": "IGTF payment",
                                "journal_name": ", ".join(
                                    igtf_move_ids.journal_id.mapped("name")
                                ),
                                "amount": sum(
                                    igtf_move_ids.mapped(
                                        lambda mv: mv.currency_id._convert(
                                            from_amount=mv.amount_total,
                                            to_currency=move.currency_id,
                                            company=move.company_id,
                                            date=fields.datetime.now(),
                                            round=True,
                                        )
                                    )
                                ),
                                "currency_id": move.currency_id.id,
                                "digits": [69, 2],
                                "position": move.currency_id.position,
                                "date": fields.datetime.now().strftime(
                                    "%Y-%m-%d"
                                ),
                                "ref": "Recargo por IGTF sobre "
                                + ", ".join(payments_with_igtf.mapped("name")),
                                "move_id": igtf_move_ids.mapped("id"),
                                "journal_ids": igtf_move_ids.mapped(
                                    "journal_id.id"
                                ),
                                "is_igtf": True,
                                "is_exchange": False,
                                "account_payment_id": igtf_move_ids.mapped("id"),
                                "igtf_payment_model": "account.move"
                            }
                        ]

                move.invoice_payments_widget = widget

    def action_register_payment(self):
        res = super().action_register_payment()
        amount_residual = sum(
            self.mapped(
                lambda m: m.currency_id._convert(
                    from_amount=m.amount_residual,
                    to_currency=self.env.company.currency_id,
                    company=self.env.company,
                    date=fields.date.today(),
                    round=True,
                )
            )
        )

        res["context"].update(
            {
                "move_type": set(self.mapped("move_type")).pop(),
                "active_amount": amount_residual,
            }
        )

        return res
