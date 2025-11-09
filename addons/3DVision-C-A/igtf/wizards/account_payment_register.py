from odoo import fields, api, models, _
from odoo.exceptions import UserError

IGTF_TAX = 0.03


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    applies_to_igtf = fields.Boolean(
        "Apply to IGTF", compute="_compute_applies_igtf"
    )
    is_igtf = fields.Boolean("Is IGTF", default=False)
    igtf_journal_id = fields.Many2one(
        "account.journal",
        "Payment Method (IGTF)",
        domain="[('type','in',['bank','cash'])]",
        readonly=False,
    )
    igtf_tax = fields.Monetary(
        "IGTF (3%)", currency_field="currency_id", compute="_compute_igtf"
    )
    amount_igtf = fields.Monetary(
        "Total con IGTF", currency_field="currency_id", compute="_compute_igtf"
    )

    @api.depends("journal_id")
    def _compute_applies_igtf(self):
        for wizard in self:
            available_move_types = ["out_invoice", "out_refund"]

            wizard.applies_to_igtf = bool(
                self.env.context.get("move_type") in available_move_types
                and wizard.journal_id.is_igtf
            )

    @api.depends("journal_id", "amount", "is_igtf")
    def _compute_igtf(self):
        for wizard in self:
            if wizard.is_igtf:

                def _convert(
                    amount, from_currency=wizard.currency_id, to_currency=None
                ):
                    return from_currency._convert(
                        from_amount=amount,
                        to_currency=to_currency
                        or wizard.company_id.currency_id,
                        company=wizard.company_id,
                        date=wizard.payment_date or fields.date.today(),
                        round=True,
                    )

                wizard_amount_in_currency = _convert(wizard.amount)

                if wizard_amount_in_currency < self.env.context.get(
                    "active_amount"
                ):
                    wizard.igtf_tax = wizard.amount * IGTF_TAX
                else:
                    wizard.igtf_tax = (
                        _convert(
                            amount=self.env.context.get("active_amount"),
                            from_currency=self.env.company.currency_id,
                            to_currency=wizard.currency_id,
                        )
                        * IGTF_TAX
                    )

                wizard.amount_igtf = wizard.amount + wizard.igtf_tax

            else:
                wizard.igtf_tax = None
                wizard.amount_igtf = None

    def _init_payments(self, to_process, **kwargs):
        for payment in to_process:
            payment["create_vals"].update(
                {
                    "is_igtf": self.is_igtf,
                    "igtf_journal_id": self.igtf_journal_id.id,
                    "igtf_tax_wizard": payment["create_vals"].get(
                        "amount", self.amount
                    )
                    * IGTF_TAX,
                }
            )
        return super()._init_payments(to_process, **kwargs)

    def action_create_payments(self):
        if self.is_igtf and not self.igtf_journal_id:
            raise UserError(_("You must assign a payment method for the IGTF"))
        return super().action_create_payments()
