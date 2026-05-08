import uuid
import datetime

from odoo import api, fields, models


class HrNoticeAcknowledgment(models.Model):
    _name = 'hr.notice.acknowledgment'
    _description = 'HR Notice Acknowledgment'
    _order = 'sent_date desc, employee_id'
    _rec_name = 'notice_label'

    notice_key   = fields.Char(string='Notice Key', required=True, index=True,
                               help='Machine-readable key, e.g. attendance_guide_v1')
    notice_label = fields.Char(string='Notice Title',
                               help='Human-readable title shown in views and confirmation page')
    employee_id  = fields.Many2one('hr.employee', string='Employee',
                                   required=True, ondelete='cascade', index=True)
    token        = fields.Char(string='Token', copy=False, index=True, readonly=True)
    state        = fields.Selection([
        ('pending',      'Pending'),
        ('acknowledged', 'Acknowledged'),
    ], string='Status', default='pending', required=True)
    sent_date    = fields.Datetime(string='Sent On', default=fields.Datetime.now)
    ack_date     = fields.Datetime(string='Acknowledged On', readonly=True)
    ack_ip       = fields.Char(string='IP at Acknowledgment', readonly=True)

    # Summary computed for the list view
    days_pending = fields.Integer(string='Days Pending', compute='_compute_days_pending',
                                  help='Days elapsed since sent without acknowledgment')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = str(uuid.uuid4())
        return super().create(vals_list)

    def _compute_days_pending(self):
        now = datetime.datetime.now()
        for rec in self:
            if rec.state == 'acknowledged' or not rec.sent_date:
                rec.days_pending = 0
            else:
                rec.days_pending = (now - rec.sent_date).days

    def _get_ack_url(self):
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base}/notice-ack/{self.token}"

    def action_mark_acknowledged(self):
        """Manual override — HR can acknowledge on behalf of an employee."""
        for rec in self:
            if rec.state == 'pending':
                rec.write({
                    'state': 'acknowledged',
                    'ack_date': fields.Datetime.now(),
                    'ack_ip': 'manual-hr',
                })

    def action_reset_pending(self):
        """Reset to pending (e.g. if re-sending)."""
        for rec in self:
            rec.write({'state': 'pending', 'ack_date': False, 'ack_ip': False})
