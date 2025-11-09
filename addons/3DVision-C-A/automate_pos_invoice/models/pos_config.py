# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'
    is_automatic_print = fields.Boolean(
        string="Automatic invoice print",
        default=False,
    )

    is_download_pdf = fields.Boolean(
        string="Download PDF",
        default=False,
    )
