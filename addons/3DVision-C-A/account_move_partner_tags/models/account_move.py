# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    move_partner_tags = fields.Many2many(string='Partner Tags', related='partner_id.category_id')
