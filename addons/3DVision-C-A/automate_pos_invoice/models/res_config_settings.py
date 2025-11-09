
from odoo import models, fields, api
import logging

class ResConfigSettings(models.TransientModel):
  _inherit = 'res.config.settings'

  is_automatic_print = fields.Boolean(
    related="pos_config_id.is_automatic_print",
    readonly=False
  )

  is_download_pdf = fields.Boolean(
    related="pos_config_id.is_download_pdf",
    readonly=False
  )
