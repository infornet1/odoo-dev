from odoo import api, models, fields, _
from odoo.tools import float_compare
from odoo.exceptions import UserError

class PosSession(models.Model):
    _inherit = "pos.session"

    second_currency_id = fields.Many2one(related="config_id.second_currency_id")

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        res.append("second.currency")
        return res


    def _loader_params_product_product(self):
        res = super()._loader_params_product_product()
        res.get("search_params").get("fields").append("ref_list_price")
        return res


    def _get_pos_ui_second_currency(self, params):
        try:
            res = self.env["res.currency"].search_read(**params["search_params"])[0]
            res["rate"] = self.env["res.currency"]._get_conversion_rate(
                from_currency=self.currency_id,
                to_currency=self.second_currency_id,
                company=self.company_id or self.env.company,
                date=fields.Date.today(),
            )
        except Exception as e:
            print(str(e))
            raise UserError(_("You must establish a secondary currency to enter the POS"))

        return res


    def _loader_params_second_currency(self):
        return {
            "search_params": {
                "domain": [("id", "=", self.config_id.second_currency_id.id)],
                "fields": ["name", "symbol", "position", "rounding", "rate", "decimal_places"],
            },
        }

    def _loader_params_pos_payment_method(self):
        res = super()._loader_params_pos_payment_method()
        res.get("search_params").get("fields").append("currency_id")
        return res

    def _get_pos_ui_pos_payment_method(self, params):
        res = super()._get_pos_ui_pos_payment_method(params)
        for item in res:
            item["currency_id"] = self.env["res.currency"].search_read(**{
                "domain": [("id", "=", (item["currency_id"] and item["currency_id"][0]) or self.currency_id.id)],
                "fields": ["name", "symbol", "position", "rounding", "rate", "decimal_places"],
            })[0]
        return res

    # def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
    #     amounts["amount"] = self.currency_id._convert(
    #         from_amount=amounts["amount"],
    #         to_currency=payment_method.currency_id or self.currency_id,
    #         company=self.company_id,
    #         date=fields.Date.today(),
    #         round=True,
    #     )
    #     return super()._create_combine_account_payment(payment_method, amounts, diff_amount)

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        outstanding_account = payment_method.outstanding_account_id or self.company_id.account_journal_payment_debit_account_id
        destination_account = self._get_receivable_account(payment_method)

        if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
            # revert the accounts because account.payment doesn't accept negative amount.
            outstanding_account, destination_account = destination_account, outstanding_account

        # Obtener amount_full_precision y tasa
        payments = self.env['pos.payment'].search([
            ('session_id', '=', self.id),
            ('payment_method_id', '=', payment_method.id)
        ])
        amount_full_precision = sum(payments.mapped('amount_full_precision'))
        rate = payment_method.currency_id.rate or 1
        amount_bcv = amount_full_precision * rate

        account_payment = self.env['account.payment'].create({
            'amount': abs(amount_bcv),
            'journal_id': payment_method.journal_id.id,
            'currency_id': payment_method.currency_id.id or self.currency_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id':  destination_account.id,
            'ref': _('Combine %s POS payments from %s') % (payment_method.name, self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
        })

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(account_payment, payment_method, diff_amount)

        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == account_payment.destination_account_id)

    def _create_split_account_payment(self, payment, amounts):
        payment_method = payment.payment_method_id
        if not payment_method.journal_id:
            return self.env['account.move.line']
        outstanding_account = payment_method.outstanding_account_id or self.company_id.account_journal_payment_debit_account_id
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        destination_account = accounting_partner.property_account_receivable_id

        if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
            # revert the accounts because account.payment doesn't accept negative amount.
            outstanding_account, destination_account = destination_account, outstanding_account

        # Obtener amount_full_precision y tasa para el pago individual
        amount_full_precision = payment.amount_full_precision
        rate = payment_method.currency_id.rate or 1
        amount_bcv = amount_full_precision * rate

        account_payment = self.env['account.payment'].create({
            'amount': abs(amount_bcv),
            'partner_id': payment.partner_id.id,
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'ref': _('%s POS payment of %s in %s') % (payment_method.name, payment.partner_id.display_name, self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
        })
        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == account_payment.destination_account_id)

    def get_closing_control_data(self):
        res = super().get_closing_control_data()
        payment_methods = res.get("other_payment_methods")
        currency_fields = ["name", "symbol", "position", "rounding", "rate", "decimal_places"]
        company_currency = self.env.company.currency_id.read(fields=currency_fields)
        for method in payment_methods:
            currency = self.env["pos.payment.method"].browse([method["id"]]).currency_id.read(fields=currency_fields)
            method["currency"] = currency and currency[0] or company_currency[0]
            # Sumar amount_full_precision de todos los pagos de la sesión para este método
            payments = self.env['pos.payment'].search([
                ('session_id', '=', self.id),
                ('payment_method_id', '=', method["id"])
            ])
            method["amount_full_precision"] = sum(payments.mapped('amount_full_precision'))

            print("\n\nEl metodo",method)

        return res