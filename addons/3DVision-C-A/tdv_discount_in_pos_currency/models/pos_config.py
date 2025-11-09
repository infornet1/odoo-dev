from odoo import models, fields, api

class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_special_discount = fields.Boolean(
        string='Enable currency discount in POS',
        help='Allows enabling or disabling the currency discount in the Point of Sale',
        default=False
    )
    discount_percentage = fields.Float(
        string='Discount Percentage',
        help='Discount percentage to apply on the entered amount',
        default=0.0
    )
    special_discount_payment_method_ids = fields.Many2many(
        'pos.payment.method',
        'pos_config_special_discount_payment_method_rel',
        'config_id',
        'payment_method_id',
        string='Payment Methods for Currency Discount',
        help='Select the payment methods to be used for the currency discount in the POS.',
        default=lambda self: []
    )

    currency_discount_mode = fields.Selection([
        ('main', 'Use main currency for discount/ref'),
        ('secondary', 'Use secondary currency for discount/ref'),
    ],
        string='Currency mode for discount/ref',
        default=False,
        help='Choose if the discount/ref calculation is done with the main or secondary currency.'
    )

    display_discount_currency_id = fields.Many2one(
        'res.currency',
        string='Currency for Discount/Ref',
        help='Currency used for discounts and reference in POS.'
    )

    @api.onchange('currency_discount_mode', 'currency_id', 'company_id')
    def _onchange_currency_discount_mode(self):
        if self.currency_discount_mode == 'main' and self.currency_id:
            self.display_discount_currency_id = self.currency_id
        elif self.currency_discount_mode == 'secondary' and self.company_id and self.company_id.second_currency_id:
            self.display_discount_currency_id = self.company_id.second_currency_id
        else:
            self.display_discount_currency_id = False

    def write(self, vals):
        for rec in self:
            mode = vals.get('currency_discount_mode', rec.currency_discount_mode)
            if mode == 'main':
                vals['display_discount_currency_id'] = vals.get('currency_id', rec.currency_id.id)
            elif mode == 'secondary':
                vals['display_discount_currency_id'] = rec.company_id.second_currency_id.id if rec.company_id and rec.company_id.second_currency_id else False
        return super().write(vals)

    def get_fields_to_read(self):
        fields_to_read = super().get_fields_to_read()
        if 'currency_discount_mode' not in fields_to_read:
            fields_to_read.append('currency_discount_mode')
        if 'currency_amount' not in fields_to_read:
            fields_to_read.append('currency_amount')
        return fields_to_read

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_special_discount = fields.Boolean(
        related='pos_config_id.enable_special_discount', readonly=False
    )
    discount_percentage = fields.Float(
        related='pos_config_id.discount_percentage', readonly=False
    )
    special_discount_payment_method_ids = fields.Many2many(
        related='pos_config_id.special_discount_payment_method_ids', readonly=False
    )
    currency_discount_mode = fields.Selection(
        related='pos_config_id.currency_discount_mode', readonly=False
    )
    display_discount_currency_id = fields.Many2one(
        'res.currency',
        related='pos_config_id.display_discount_currency_id',
        readonly=False
    )

    @api.onchange('currency_discount_mode', 'currency_id', 'company_id')
    def _onchange_currency_discount_mode_settings(self):
        if self.currency_discount_mode == 'main' and self.currency_id:
            self.display_discount_currency_id = self.currency_id
        elif self.currency_discount_mode == 'secondary' and self.company_id and self.company_id.second_currency_id:
            self.display_discount_currency_id = self.company_id.second_currency_id
        else:
            self.display_discount_currency_id = False 