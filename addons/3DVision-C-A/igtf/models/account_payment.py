from odoo import api, fields, models, _
from odoo.exceptions import UserError

IGTF_TAX = 0.03


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_igtf = fields.Boolean("Is IGTF", default=False, store=True)
    igtf_tax = fields.Monetary("IGTF (3%)", compute="_compute_igtf", store=True)
    amount_igtf = fields.Monetary(
        "Total  IGTF", compute="_compute_igtf", store=True
    )
    igtf_journal_id = fields.Many2one(
        "account.journal",
        "Payment Method (IGTF)",
        domain="[('type','in',['bank','cash'])]",
    )
    igtf_tax_wizard = fields.Monetary("IGTF from the Wizard", default=None)
    
    #ERROR OF ODOO in ACCOUNT_CHECK_PRINTING
    effective_date = fields.Date()

    @api.depends("journal_id", "amount")
    def _compute_igtf(self):
        for payment in self:
            if payment.is_igtf:
                payment.igtf_tax = (
                    payment.igtf_tax_wizard or payment.amount * IGTF_TAX
                )
                payment.amount_igtf = payment.amount + payment.igtf_tax
            else:
                payment.igtf_tax = None
                payment.amount_igtf = None

    def action_post(self):
        res = super().action_post()

        for payment in self:
            pos_session = (
                payment.pos_session_id
                if hasattr(payment, "pos_session_id")
                else False
            )
            payment.is_igtf = bool(payment.igtf_journal_id)

            if payment.is_igtf and not pos_session:
                if not self.env.company.igtf_account_id:
                    raise UserError(
                        _("An IGTF account has not been configured")
                    )

                def _convert(amount, to_currency=None):
                    return payment.currency_id._convert(
                        from_amount=amount,
                        to_currency=to_currency,
                        company=payment.company_id,
                        date=payment.date or fields.date.today(),
                        round=True,
                    )

                move = self.env["account.move"].create(
                    {
                        "ref": _("Surcharge on %s for IGTF" % payment.name),
                        "invoice_origin": payment.name,
                        "partner_id": payment.partner_id.id,
                        "journal_id": payment.igtf_journal_id.id,
                        "company_id": payment.company_id.id,
                        "currency_id": payment.igtf_journal_id.currency_id.id
                        or payment.company_id.currency_id.id,
                        "line_ids": [
                            (
                                0,
                                0,
                                {
                                    "account_id": payment.igtf_journal_id.inbound_payment_method_line_ids.filtered(
                                        lambda line: line.name == "Manual"
                                    ).payment_account_id.id
                                    or self.env.company.account_journal_payment_debit_account_id.id,
                                    "partner_id": payment.partner_id.id,
                                    "amount_currency": _convert(
                                        payment.igtf_tax,
                                        payment.igtf_journal_id.currency_id,
                                    )
                                    * (
                                        1
                                        if payment.payment_type == "inbound"
                                        else -1
                                    ),
                                    "debit": _convert(
                                        payment.igtf_tax,
                                        payment.company_id.currency_id,
                                    )
                                    if payment.payment_type == "inbound"
                                    else 0,
                                    "credit": 0
                                    if payment.payment_type == "inbound"
                                    else _convert(
                                        payment.igtf_tax,
                                        self.env.company.currency_id,
                                    ),
                                    "currency_id": payment.igtf_journal_id.currency_id.id
                                    or payment.company_id.currency_id.id,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "account_id": self.env.company.igtf_account_id.id,
                                    "partner_id": payment.partner_id.id,
                                    "amount_currency": -_convert(
                                        payment.igtf_tax,
                                        payment.igtf_journal_id.currency_id,
                                    )
                                    * (
                                        1
                                        if payment.payment_type == "inbound"
                                        else -1
                                    ),
                                    "debit": 0
                                    if payment.payment_type == "inbound"
                                    else _convert(
                                        payment.igtf_tax,
                                        payment.company_id.currency_id,
                                    ),
                                    "credit": _convert(
                                        payment.igtf_tax,
                                        payment.company_id.currency_id,
                                    )
                                    if payment.payment_type == "inbound"
                                    else 0,
                                    "currency_id": payment.igtf_journal_id.currency_id.id
                                    or payment.company_id.currency_id.id,
                                },
                            ),
                        ],
                    }
                )
                move.action_post()

        return res
