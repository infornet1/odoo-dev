# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PosController(http.Controller):

    def getOrderByPOSReference(self, pos_reference):
        return request.env['pos.order'].sudo().search([
            ('pos_reference', 'like', pos_reference)
        ])


    @http.route('/fp3dv', auth='user', type='json')
    def print_command_line(self, as_json: dict = {}, **kwargs):
        self.getOrderByPOSReference(as_json.get('name')).send_to_fiscal_printer()
        return {
            'response': {
                'error': False
            }
        }