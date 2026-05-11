import uuid
import datetime

from odoo import api, fields, models


class PartnerCommunicationAck(models.Model):
    _name = 'partner.communication.ack'
    _description = 'Partner Communication Acknowledgment'
    _order = 'sent_date desc, partner_id'
    _rec_name = 'notice_label'

    notice_key   = fields.Char(string='Campaign Key', required=True, index=True)
    notice_label = fields.Char(string='Campaign Title')
    partner_id   = fields.Many2one('res.partner', string='Representante',
                                   required=True, ondelete='cascade', index=True)
    partner_name  = fields.Char(string='Nombre', readonly=True)
    partner_email = fields.Char(string='Email', readonly=True)
    token        = fields.Char(string='Token', copy=False, index=True, readonly=True)
    state        = fields.Selection([
        ('pending',     'Pendiente'),
        ('continuing',  'Continuará'),
        ('leaving',     'No continuará'),
    ], string='Decisión', default='pending', required=True)
    sent_date    = fields.Datetime(string='Enviado', default=fields.Datetime.now)
    ack_date     = fields.Datetime(string='Respondido', readonly=True)
    ack_ip       = fields.Char(string='IP', readonly=True)
    days_pending = fields.Integer(string='Días sin respuesta',
                                  compute='_compute_days_pending')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = str(uuid.uuid4())
            if vals.get('partner_id') and not vals.get('partner_name'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                vals.setdefault('partner_name', partner.name)
                vals.setdefault('partner_email', partner.email or '')
        return super().create(vals_list)

    def _compute_days_pending(self):
        now = datetime.datetime.now()
        for rec in self:
            if rec.state != 'pending' or not rec.sent_date:
                rec.days_pending = 0
            else:
                rec.days_pending = (now - rec.sent_date).days

    def _get_si_url(self):
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base}/partner-ack/{self.token}/si"

    def _get_no_url(self):
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base}/partner-ack/{self.token}/no"

    def action_mark_continuing(self):
        for rec in self:
            if rec.state == 'pending':
                rec.write({'state': 'continuing', 'ack_date': fields.Datetime.now(),
                           'ack_ip': 'manual-hr'})

    def action_mark_leaving(self):
        for rec in self:
            if rec.state == 'pending':
                rec.write({'state': 'leaving', 'ack_date': fields.Datetime.now(),
                           'ack_ip': 'manual-hr'})

    def action_reset_pending(self):
        for rec in self:
            rec.write({'state': 'pending', 'ack_date': False, 'ack_ip': False})
