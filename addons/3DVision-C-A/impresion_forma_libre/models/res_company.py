from odoo import models, fields, api

FREEFORM_OPTIONS = [
    ("letter", "Letter"),
    ("half_letter", "Half Letter"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    invoice_freeform_selection = fields.Selection(
        FREEFORM_OPTIONS,
        "Format of Freeform",
        default="half_letter",
        required=True,
    )
