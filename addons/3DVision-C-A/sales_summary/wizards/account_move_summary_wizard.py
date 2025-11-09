from odoo import fields, api, models, _
from odoo.tools.misc import formatLang
from collections import defaultdict

SELECTION_OPTIONS = [("yes", _("Yes")), ("no", _("No"))]

class AccountMoveSummaryWizard(models.Model):

    _name = "account.move.summary.wizard"
    _description = "Wizard of account move summary"

    @api.model
    def _get_invoice_domain(self):
        return [
            ("company_id", "=", self.env.company.id),
            ("state", "=", "posted"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("move_type", "=", "out_invoice"),
        ]
    @api.model
    def _get_payment_domain(self):
        return [
            ("company_id", "=", self.env.company.id),
            ("state", "=", "posted"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("partner_type", "=", "customer"),
        ]

    date_from = fields.Date("From", default=fields.date.today())
    date_to = fields.Date("To", default=fields.date.today())
    has_invoices = fields.Selection(
        SELECTION_OPTIONS, "Has Invoices", default="yes", required=True
    )
    has_payments = fields.Selection(
        SELECTION_OPTIONS, "Has Payments", default="yes", required=True
    )
    has_journals = fields.Selection(
        SELECTION_OPTIONS, "Has Journals", default="yes", required=True
    )

    def generate_report(self):
        report_action = "sales_summary.report_action_account_move_summary"
        return self.env.ref(report_action).report_action(self)

    @api.model
    def get_invoices(self):
        invoices = self.env["account.move"].search(self._get_invoice_domain())
        for payment in self.get_payments():
            invoices |= self.get_reconciled_moves(payment)
        return invoices

    @api.model
    def get_payments(self):
        return self.env["account.payment"] \
                .search(self._get_payment_domain()).move_id \
                .filtered_domain([("journal_id.type", "in", ["cash","bank"])])

    @api.model
    def get_reconciled_moves(self, move):
        reconciled_moves = self.env["account.move"]
        for item in move._get_all_reconciled_invoice_partials():
            reconciled_moves |= item["aml"].move_id
        return reconciled_moves

    @api.model
    def get_cash_and_charges(self):

        def get_converted_amount(ml):
            return ml["currency"]._convert(
                from_amount=ml["amount"],
                to_currency=ml["aml"].company_id.currency_id,
                company=ml["aml"].company_id,
                date=ml["aml"].date,
                round=True,
            )

        amounts = defaultdict(int)
        payments = self.get_payments()
        for payment in payments:
            reconciled_ml = payment._get_all_reconciled_invoice_partials()
            amounts["cash"] += sum([
                get_converted_amount(ml) if ml["aml"].move_id.date >= self.date_from
                and ml["aml"].move_id.date <= self.date_to else 0
                for ml in reconciled_ml
            ])
            amounts["charges"] += sum([
                get_converted_amount(ml) if ml["aml"].move_id.date < self.date_from
                or ml["aml"].move_id.date > self.date_to else 0
                for ml in reconciled_ml
            ])
        return amounts

