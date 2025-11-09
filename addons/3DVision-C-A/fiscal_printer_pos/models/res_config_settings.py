from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_x_fiscal_command_baudrate = fields.Integer(
        "Baudrate",
        related="pos_config_id.x_fiscal_command_baudrate",
        store=True,
        readonly=False,
        default=9600
    )
    pos_x_fiscal_commands_time = fields.Integer(
        "Tiempo de espera",
        related="pos_config_id.x_fiscal_commands_time",
        store=True,
        readonly=False,
        default=750,
    )
    pos_x_fiscal_printer_id = fields.Many2one(
        string="Impresora fiscal",
        related="pos_config_id.x_fiscal_printer_id",
        readonly=False,
        store=True,
    )

    flag_21 = fields.Selection([('00', '00'), ('30', '30')], string="Flag 21", related="pos_config_id.flag_21",
                               store=True)

    connection_type = fields.Selection([('serial', 'Serial'), ('usb', 'USB'), ('usb_serial', 'USB Serial'), ('file', 'Archivo'), ('api', 'API')],
                                       related="pos_config_id.connection_type",
                                       store=True
                                       )

    api_url = fields.Char(related="pos_config_id.api_url",
                          store=True)

    x_fiscal_printer_currency_id = fields.Many2one(
        related="pos_config_id.x_fiscal_printer_currency_id",
        store=True
    )

    @api.constrains("pos_x_fiscal_commands_time")
    def _check_x_fiscal_commands_time(self):
        for rec in self:
            if rec.pos_x_fiscal_commands_time < 0:
                raise ValidationError(
                    _("El tiempo entre comandos no puede ser cero"))
