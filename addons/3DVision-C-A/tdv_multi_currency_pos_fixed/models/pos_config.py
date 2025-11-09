from odoo import fields, api, models, _
from odoo.exceptions import ValidationError

REPORT_CURRENCY_OPTIONS = [("main","Main"),("second","Secondary"),("both","Both")]

class PosConfig(models.Model):
    _inherit = "pos.config"

    second_currency_id = fields.Many2one(related="company_id.second_currency_id")
    report_currency_selection = fields.Selection(REPORT_CURRENCY_OPTIONS, default="both", required=True)

    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id', 'payment_method_ids')
    def _check_currencies(self):
        for config in self:
            if config.use_pricelist and config.pricelist_id not in config.available_pricelist_ids:
                raise ValidationError(_("The default pricelist must be included in the available pricelists."))

            if config.use_pricelist and any(config.available_pricelist_ids.mapped(lambda pricelist: pricelist.currency_id != config.currency_id)):
                raise ValidationError(_("All available pricelists must be in the same currency as the company or"
                                        " as the Sales Journal set on this point of sale if you use"
                                        " the Accounting application."))
            if config.invoice_journal_id.currency_id and config.invoice_journal_id.currency_id != config.currency_id:
                raise ValidationError(_("The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))