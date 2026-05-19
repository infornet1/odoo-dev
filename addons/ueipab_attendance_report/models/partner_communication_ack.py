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
    partner_phone = fields.Char(string='Teléfono WA', readonly=True)
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

    # ── Audit trail ────────────────────────────────────────────────────────────
    vote_channel = fields.Selection([
        ('email_link', 'Enlace de correo'),
        ('whatsapp',   'WhatsApp (Glenda)'),
        ('phone',      'Teléfono (staff)'),
        ('in_person',  'Presencial'),
    ], string='Canal de voto', readonly=True)
    recorded_by  = fields.Many2one('res.users', string='Registrado por',
                                   readonly=True, ondelete='set null')
    vote_notes   = fields.Text(string='Notas de auditoría')
    bounce_wa_sent = fields.Boolean(string='WA de rebote enviado', default=False)

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

    def _record_decision(self, decision, channel=None, notes=None, user_id=None):
        """Central write method used by controller, wizard, and Glenda handler."""
        vals = {
            'state':        decision,
            'ack_date':     fields.Datetime.now(),
            'vote_channel': channel or 'email_link',
        }
        if notes:
            vals['vote_notes'] = notes
        if user_id:
            vals['recorded_by'] = user_id
        self.write(vals)

    def action_mark_continuing(self):
        for rec in self:
            if rec.state == 'pending':
                rec._record_decision('continuing', channel='in_person',
                                     user_id=self.env.user.id)

    def action_mark_leaving(self):
        for rec in self:
            if rec.state == 'pending':
                rec._record_decision('leaving', channel='in_person',
                                     user_id=self.env.user.id)

    def action_reset_pending(self):
        for rec in self:
            rec.write({
                'state': 'pending', 'ack_date': False, 'ack_ip': False,
                'vote_channel': False, 'recorded_by': False,
                'vote_notes': False, 'bounce_wa_sent': False,
            })
