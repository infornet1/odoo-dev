from odoo import models, api, fields
from functools import partial


class AccountMoveRetentionWizard(models.TransientModel):

    _name = "account.move.retention.wizard"
    _description = "Wizard for the theoretical report of retentions"

    invoice_name = fields.Char(
        string="Bill",
        default=lambda self: self.env.context.get("invoice_name")
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        default=lambda self: self.env.context.get("partner_id")
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.context.get("move_currency_id")
    )
    invoice_amount = fields.Monetary(
        string="Bill amount",
        currency_field="currency_id",
        default=lambda self: self.env.context.get("invoice_amount_due")
    )
    iva_amount = fields.Monetary(
        string="IVA Retention",
        currency_field="currency_id",
        default=lambda self: self.env.context.get("iva")
    )
    islr_amount = fields.Monetary(
        string="ISLR Retention",
        currency_field="currency_id",
        default=lambda self: self.env.context.get("islr")
    )
    iae_amount = fields.Monetary(
        string="IAE Retention",
        currency_field="currency_id",
        default=lambda self: self.env.context.get("iae")
    )
    amount_total = fields.Monetary(
        string="Total to pay",
        currency_field="currency_id",
        compute="_compute_amount_total"
    )
    ref_currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.ref("base.VEF")
    )
    ref_invoice_amount = fields.Monetary(
        string="Bill amount (Referential)",
        currency_field="ref_currency_id",
        compute="_compute_reference_amounts"
    )
    ref_iva_amount = fields.Monetary(
        string="IVA Retention (Referential)",
        currency_field="ref_currency_id",
        compute="_compute_reference_amounts"
    )
    ref_islr_amount = fields.Monetary(
        string="ISLR Retention (Referential)",
        currency_field="ref_currency_id",
        compute="_compute_reference_amounts"
    )
    ref_iae_amount = fields.Monetary(
        string="IAE Retention (Referential)",
        currency_field="ref_currency_id",
        compute="_compute_reference_amounts"
    )
    ref_amount_total = fields.Monetary(
        string="Total to pay (Referential)",
        currency_field="ref_currency_id",
        compute="_compute_reference_amounts",
        readonly=True
    )

    invoice_date = fields.Date(
        string="Fecha",
        default=lambda self: self.env.context.get("invoice_date")
    )

    @api.depends("invoice_amount", "iva_amount", "islr_amount", "iae_amount")
    def _compute_amount_total(self):
        for wizard in self:
            wizard.amount_total = wizard.invoice_amount \
                - wizard.iva_amount \
                - wizard.islr_amount \
                - wizard.iae_amount

    @api.depends(
        "currency_id",
        "ref_currency_id",
        "invoice_amount",
        "iva_amount",
        "islr_amount",
        "iae_amount")
    def _compute_reference_amounts(self):

        for wizard in self:
            convert = partial(
                wizard.currency_id._convert,
                to_currency=wizard.ref_currency_id,
                company=self.env.company,
                date=wizard.invoice_date,
                round=True
            )
            wizard.ref_invoice_amount = convert(wizard.invoice_amount)
            wizard.ref_iva_amount = convert(wizard.iva_amount)
            wizard.ref_islr_amount = convert(wizard.islr_amount)
            wizard.ref_iae_amount = convert(wizard.iae_amount)
            wizard.ref_amount_total = convert(wizard.amount_total)

    def print_report(self):
        # return self.env["ir.actions.report.xml"].render(
        #     "account.account.report_invoice",
        #     {
        #         "data": self.env["account.invoice"].browse(self.ids),
        #     }
        action = "retenciones.action_account_move_retention_report"
        return self.env.ref(action).report_action(self)
