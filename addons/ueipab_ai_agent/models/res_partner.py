from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    telegram_chat_id = fields.Char(
        string='Telegram Chat ID',
        readonly=True,
        copy=False,
        index=True,
        help='Populated automatically when the contact opts in via the Glenda Telegram deep-link (FAM_token). '
             'Used for Telegram-first campaign blasts.',
    )
