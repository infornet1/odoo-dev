from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ve')
    def _get_ve_template_data(self):
        return {
            'code_digits': '9',
            'property_account_receivable_id': 'account_activa_account_101003001',
            'property_account_payable_id': 'account_activa_account_201001001',
            'property_account_expense_categ_id': 'account_activa_account_601003001',
            'property_account_income_categ_id': 'account_activa_account_401001001',
        }

    @template('ve', 'res.company')
    def _get_ve_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ve',
                'bank_account_code_prefix': '101002',
                'cash_account_code_prefix': '101001',
                'transfer_account_code_prefix': '106001002',
                'transfer_account_id': 'account_activa_account_106001002',
                'account_default_pos_receivable_account_id': 'account_activa_account_106001003',
                'income_currency_exchange_account_id': 'account_activa_account_901001001',
                'expense_currency_exchange_account_id': 'account_activa_account_901001002',
                'account_journal_payment_debit_account_id': 'account_activa_account_106001007',
                'account_journal_payment_credit_account_id': 'account_activa_account_206001001',
                'account_journal_suspense_account_id': 'account_activa_account_106001001',           
                'account_sale_tax_id': 'tax3sale',
                'account_purchase_tax_id': 'tax3purchase',
            },
        }