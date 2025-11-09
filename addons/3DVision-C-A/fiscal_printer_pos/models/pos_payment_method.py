from odoo import models, fields, api
from odoo.exceptions import ValidationError

PRINTER_CODE_SELECTION = [
    ("01", "01"),
    ("02", "02"),
    ("03", "03"),
    ("04", "04"),
    ("05", "05"),
    ("06", "06"),
    ("07", "07"),
    ("08", "08"),
    ("09", "09"),
    ("10", "10"),
    ("11", "11"),
    ("12", "12"),
    ("13", "13"),
    ("14", "14"),
    ("15", "15"),
    ("16", "16"),
    ("17", "17"),
    ("18", "18"),
    ("19", "19"),
    ("20", "20 (IGTF)"),
    ("21", "21 (IGTF)"),
    ("22", "22 (IGTF)"),
    ("23", "23 (IGTF)"),
    ("24", "24 (IGTF)"),
]


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
    # Allow manual input of x_printer_code if no journal_id is set, with default '01'
    x_printer_journal_code = fields.Selection(
        related="journal_id.fp_payment_method", store=True)
    x_printer_code = fields.Selection(
        string="Código en la impresora", default=lambda self: self.x_printer_journal_code or '01', selection=PRINTER_CODE_SELECTION)
    currency_rate = fields.Float(related="journal_id.currency_id.rate")
    # x_printer_code = fields.Selection(
    #     "Código en la impresora", related="journal_id.fp_payment_method", store=True)

    @api.constrains("x_printer_code")
    def _check_x_printer_code(self):
        for rec in self:
            if len(rec.x_printer_code) != 2:
                raise ValidationError(
                    "El código en la impresora sólo puede tener dos caracteres")
