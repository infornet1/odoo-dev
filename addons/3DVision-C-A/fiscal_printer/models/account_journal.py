from odoo import models, api, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    fp_payment_method = fields.Selection(
        string="Tipo de metodo",
        selection=[
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
        ],
        default="01",
    )
