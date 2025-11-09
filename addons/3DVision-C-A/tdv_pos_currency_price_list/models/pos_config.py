# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    enable_currency_price_list_control = fields.Boolean(
        string='Enable Currency Control by Price List',
        default=False,
        help='Enables currency control based on the selected price list in the POS'
    )
    
    currency_control_pricelist_ids = fields.Many2many(
        'product.pricelist',
        'pos_config_currency_control_pricelist_rel',
        'pos_config_id',
        'pricelist_id',
        string='Price Lists for Currency Control',
        help='Price lists that will activate currency control in the POS'
    )
    
    special_currency_payment_method_ids = fields.Many2many(
        'pos.payment.method',
        'pos_config_special_currency_payment_method_rel',
        'pos_config_id',
        'payment_method_id',
        string='Currency Payment Methods',
        help='Special payment methods that will be used when currency control is active'
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    pos_enable_currency_price_list_control = fields.Boolean(
        related='pos_config_id.enable_currency_price_list_control',
        readonly=False,
        string='Enable Currency Control by Price List',
        help='Enables currency control based on the selected price list in the POS'
    )
    
    pos_currency_control_pricelist_ids = fields.Many2many(
        related='pos_config_id.currency_control_pricelist_ids',
        readonly=False,
        string='Price Lists for Currency Control',
        help='Price lists that will activate currency control in the POS'
    )
    
    pos_special_currency_payment_method_ids = fields.Many2many(
        related='pos_config_id.special_currency_payment_method_ids',
        readonly=False,
        string='Currency Payment Methods',
        help='Special payment methods that will be used when currency control is active'
    )
