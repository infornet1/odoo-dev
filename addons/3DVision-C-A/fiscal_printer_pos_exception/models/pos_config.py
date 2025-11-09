from odoo import fields, api, models


class PosConfigInherit(models.Model):
    _inherit = "pos.config"

    default_customer_id = fields.Many2one(
        'res.partner', string='Default Customer')
    fiscal_auto_print = fields.Boolean('Imprimir Automaticamente')

    x_fiscal_command_baudrate = fields.Integer("Baudrate", default=9600)
    x_fiscal_commands_time = fields.Integer("Tiempo de espera", default=750,)
    x_fiscal_printer_id = fields.Many2one(
        "x.pos.fiscal.printer", "Impresora fiscal")
    x_fiscal_printer_code = fields.Char(related="x_fiscal_printer_id.serial")
    flag_21 = fields.Selection([('00', '00'), ('30', '30')],
                               string="Flag 21", related="x_fiscal_printer_id.flag_21")
    connection_type = fields.Selection([('serial', 'Serial'), ('usb', 'USB'), ('usb_serial', 'USB Serial'), (
        'file', 'Archivo'), ('api', 'API')], related="x_fiscal_printer_id.connection_type")
    api_url = fields.Char(related="x_fiscal_printer_id.api_url")
    x_fiscal_printer_flag_50 = fields.Char(
        related="x_fiscal_printer_id.flag_50")
    x_fiscal_printer_flag_63 = fields.Char(
        related="x_fiscal_printer_id.flag_63")
    x_fiscal_printer_usb_vendor_id = fields.Char(
        related="x_fiscal_printer_id.usb_vendor_id")
    x_fiscal_printer_usb_product_id = fields.Char(
        related="x_fiscal_printer_id.usb_product_id")
    x_fiscal_printer_z_report_number = fields.Char(
        related="x_fiscal_printer_id.display_current_z_report")
    x_fiscal_printer_currency_id = fields.Many2one(
        related="x_fiscal_printer_id.currency_id")
    x_fiscal_printer_currency_rate = fields.Float(
        related="x_fiscal_printer_id.currency_id.rate")
