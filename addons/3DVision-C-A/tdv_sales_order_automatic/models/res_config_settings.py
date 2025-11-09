from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """
      This class inherits from the `res.config.settings` model in Odoo and adds
       two boolean fields to the
      configuration settings page: `create_invoice_delivery_validate` and
      `auto_send_invoice`.
      """
    _inherit = "res.config.settings"

    is_create_invoice_delivery_validate = fields.Boolean(
        string="Auto Post invoice", config_parameter=
        'automatic_invoice_and_post.is_create_invoice_delivery_validate',
        help="Create and post invoice on delivery validate")

    is_auto_send_invoice = fields.Boolean(string="Auto Send Invoice",
                                          config_parameter=
                                          'automatic_invoice_and_post.is_auto_'
                                          'send_invoice',
                                          help="Enable to send invoice to "
                                               "customer on delivery validate ")
    is_auto_confirm = fields.Boolean(string="Auto Confirm", 
                                    config_parameter='sale_order_automatic.is_auto_confirm')
                                    
    is_auto_delivery = fields.Boolean(string="Auto Delivery", 
                                      config_parameter='sale_order_automatic.is_auto_delivery')
    
