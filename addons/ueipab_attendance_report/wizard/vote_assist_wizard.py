from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VoteAssistWizard(models.TransientModel):
    _name        = 'vote.assist.wizard'
    _description = 'Registrar voto asistido (teléfono / presencial)'

    ack_id = fields.Many2one(
        'partner.communication.ack', string='Registro de voto',
        required=True, readonly=True,
    )
    partner_name = fields.Char(related='ack_id.partner_name', readonly=True)
    notice_label = fields.Char(related='ack_id.notice_label', readonly=True)

    decision = fields.Selection([
        ('continuing', 'Opción A — $218,88/mes'),
        ('leaving',    'Opción B — $236,58/mes'),
    ], string='Decisión del representante', required=True)

    vote_channel = fields.Selection([
        ('phone',      'Teléfono (llamada entrante o saliente)'),
        ('in_person',  'Presencial (oficina administrativa)'),
    ], string='Canal', required=True, default='phone')

    vote_notes = fields.Text(
        string='Notas de auditoría',
        help='Ej: llamada entrante 10:32am, confirmado verbalmente; '
             'representante se presentó en oficina con cédula.',
    )

    def action_confirm(self):
        self.ensure_one()
        ack = self.ack_id
        if ack.state != 'pending':
            raise UserError(_(
                'Este representante ya registró su voto (%s). '
                'Use "Reiniciar a Pendiente" si necesita corregir.'
            ) % dict(ack._fields['state'].selection).get(ack.state, ack.state))

        notes = self.vote_notes or ''
        channel_label = dict(self._fields['vote_channel'].selection).get(
            self.vote_channel, self.vote_channel)
        audit_note = f'[{channel_label}] Registrado por {self.env.user.name}'
        if notes:
            audit_note += f' — {notes}'

        ack._record_decision(
            decision=self.decision,
            channel=self.vote_channel,
            notes=audit_note,
            user_id=self.env.user.id,
        )
        return {'type': 'ir.actions.act_window_close'}
