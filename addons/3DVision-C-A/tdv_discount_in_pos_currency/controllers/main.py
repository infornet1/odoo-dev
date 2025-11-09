from odoo import http, fields
from odoo.http import request, route

class PosOrderDraftController(http.Controller):
    @route('/pos/draft/save', type='json', auth='user')
    def save_draft(self, uid, data, session_id=None):
        # Solo guardar borrador si el POS es restaurante
        if session_id:
            session = request.env['pos.session'].sudo().browse(session_id)
            if not session.config_id.iface_table_management:
                return {'result': 'skip'}
        if 'currency_amount' not in data:
            data['currency_amount'] = 0
        draft = request.env['pos.order.draft'].sudo().search([('uid', '=', uid)], limit=1)
        vals = {
            'data': data,
            'session_id': session_id,
            'user_id': request.env.user.id,
            'last_update': fields.Datetime.now(),
        }
        if draft:
            draft.write(vals)
        else:
            vals['uid'] = uid
            request.env['pos.order.draft'].sudo().create(vals)
        return {'result': 'ok'}

    @route('/pos/draft/load', type='json', auth='user')
    def load_drafts(self, session_id=None):
        # Solo cargar borradores si el POS es restaurante
        if session_id:
            session = request.env['pos.session'].sudo().browse(session_id)
            if not session.config_id.iface_table_management:
                return []
        domain = []
        if session_id:
            domain.append(('session_id', '=', session_id))
        drafts = request.env['pos.order.draft'].sudo().search(domain)
        result = []
        for d in drafts:
            data = d.data or {}
            if 'currency_amount' not in data:
                data['currency_amount'] = 0
            result.append({'uid': d.uid, 'data': data})
        return result

    @route('/pos/currency_amounts', type='json', auth='user')
    def get_currency_amounts(self, order_ids=None):
        if not order_ids:
            return {}
        orders = request.env['pos.order'].sudo().browse(order_ids)
        return {order.id: order.currency_amount for order in orders}

    @route('/pos/update_currency_amount', type='json', auth='user')
    def update_currency_amount(self, uid=None, amount=None):
        if not uid or amount is None:
            return {'result': 'error', 'msg': 'Missing uid or amount'}
        # Solo buscar órdenes en estado draft (nuevo)
        order = request.env['pos.order'].sudo().search([('uid', '=', uid), ('state', '=', 'draft')], limit=1)
        if not order:
            return {'result': 'error', 'msg': 'Order not found or not in draft state'}
        order.currency_amount = amount
        return {'result': 'ok', 'currency_amount': order.currency_amount} 