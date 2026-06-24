# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .enrollment_journey import (
    STEP_STATES, DONE_STATES, SOPORTE_EMAIL, _email_wrapper, _cta_button,
)

_logger = logging.getLogger(__name__)

# Phase 3 notifications — staff-internal only (customers are served by the
# farewell page). Addresses verified against res.users in testing 2026-06-24.
JOSEFINA_EMAIL = 'josefina.rodriguez@ueipab.edu.ve'        # step 2 CC (exit docs)
GMAIL_SUSPEND_CC = 'lorena.reyes@ueipab.edu.ve,alejandra.lopez@ueipab.edu.ve'  # step 5 CC

# Which step clearances fire an email, and to whom. Steps 1/3/4 are silent.
STEP_NOTIFY = {
    2: {
        'cc': JOSEFINA_EMAIL,
        'subject': '[Egreso · Documentación] Familia %s',
        'header': 'Egreso · Preparar documentación de egreso',
        'banner': '📄 Solvencia confirmada — preparar la documentación de egreso',
        'banner_color': '#2471a3',
        'banner_bg': '#eaf2fb',
        'intro': ('La familia <strong>%s</strong> confirmó la solvencia administrativa '
                  '(paso 1). Por favor preparar y reunir toda la documentación de egreso '
                  'del/los estudiante(s) indicados a continuación.'),
    },
    5: {
        'cc': GMAIL_SUSPEND_CC,
        'subject': '[Egreso · Suspender Gmail] Familia %s',
        'header': 'Egreso · Suspender cuentas Gmail institucionales',
        'banner': '📧 Egreso confirmado — suspender cuentas @ueipab.edu.ve',
        'banner_color': '#7d3c00',
        'banner_bg': '#fef9e7',
        'intro': ('El egreso de la familia <strong>%s</strong> alcanzó el paso final. '
                  'Por favor suspender las cuentas institucionales @ueipab.edu.ve '
                  'del/los estudiante(s) indicados.'),
    },
}

# 5-step offboarding (egreso) checklist. Driven by this constant the same way
# enrollment.journey is driven by STEP_DEFS — reorder = no DB migration.
WITHDRAWAL_STEP_DEFS = [
    ('step1', 'Solvencia administrativa 2025-2026',
     'Carta de no deuda — mensualidades de julio y agosto del año escolar 2025-2026 canceladas.'),
    ('step2', 'Documentación de egreso preparada',
     'Reunir y preparar toda la documentación de egreso del/los estudiante(s).'),
    ('step3', 'Desincorporación de Akdemia',
     'Desincorporar al/los estudiante(s) de la plataforma Akdemia (edge.akdemia.com).'),
    ('step4', 'Liberación de SIGE',
     'Liberar al/los estudiante(s) del SIGE (Ministerio del Poder Popular para la Educación).'),
    ('step5', 'Suspensión de cuentas Gmail institucionales',
     'Suspender las cuentas @ueipab.edu.ve del/los estudiante(s).'),
]

# Steps 3-5 (Akdemia / SIGE / Gmail) require step 1 (solvencia) + step 2 (exit
# docs) to be done first — the legal/administrative gate.
WITHDRAWAL_GATE_STEPS = (1, 2)
N_STEPS = len(WITHDRAWAL_STEP_DEFS)


class EnrollmentWithdrawal(models.Model):
    _name = 'enrollment.withdrawal'
    _description = 'Enrollment Withdrawal / Egreso 2025-2026'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    journey_id = fields.Many2one(
        'enrollment.journey', string='Inscripción de origen',
        ondelete='set null', index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Representante',
        related='journey_id.partner_id', store=True, index=True, readonly=True)
    student_ids = fields.One2many(
        related='journey_id.student_ids', string='Estudiantes', readonly=True)
    exit_reason = fields.Text(
        string='Motivo de retiro', related='journey_id.decline_reason', readonly=True)

    state = fields.Selection([
        ('in_progress', 'En proceso'),
        ('completed',   'Completado'),
    ], string='Estado', compute='_compute_state', store=True, index=True)
    progress_pct = fields.Integer(
        string='Progreso %', compute='_compute_state', store=True)

    # 5-step offboarding checklist
    step1_state = fields.Selection(STEP_STATES, default='pending', string='1. Solvencia')
    step2_state = fields.Selection(STEP_STATES, default='pending', string='2. Documentación')
    step3_state = fields.Selection(STEP_STATES, default='pending', string='3. Akdemia')
    step4_state = fields.Selection(STEP_STATES, default='pending', string='4. SIGE')
    step5_state = fields.Selection(STEP_STATES, default='pending', string='5. Gmail')

    step1_cleared_by = fields.Many2one('res.users', readonly=True)
    step2_cleared_by = fields.Many2one('res.users', readonly=True)
    step3_cleared_by = fields.Many2one('res.users', readonly=True)
    step4_cleared_by = fields.Many2one('res.users', readonly=True)
    step5_cleared_by = fields.Many2one('res.users', readonly=True)

    step1_cleared_at = fields.Datetime(readonly=True)
    step2_cleared_at = fields.Datetime(readonly=True)
    step3_cleared_at = fields.Datetime(readonly=True)
    step4_cleared_at = fields.Datetime(readonly=True)
    step5_cleared_at = fields.Datetime(readonly=True)

    # Regulatory audit references (decision D3)
    solvencia_ref = fields.Char(string='Ref. carta de solvencia')   # step 1
    sige_ref = fields.Char(string='Ref./constancia SIGE')           # step 4

    @api.depends('partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Egreso — %s' % (rec.partner_id.name or '?')

    @api.depends('step1_state', 'step2_state', 'step3_state',
                 'step4_state', 'step5_state')
    def _compute_state(self):
        for rec in self:
            done = sum(1 for i in range(1, N_STEPS + 1)
                       if rec['step%d_state' % i] in DONE_STATES)
            rec.progress_pct = int(done * 100 / N_STEPS)
            rec.state = 'completed' if done == N_STEPS else 'in_progress'

    # -- email helpers ----------------------------------------------------

    def _backend_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '%s/web#model=enrollment.withdrawal&id=%d&view_type=form' % (base, self.id)

    def _student_rows_html(self):
        """Current-grade student table for egreso emails (not a 2026-2027 grade)."""
        students = self.student_ids
        if not students:
            return ('<p style="color:#8096b4;font-size:13px;font-style:italic;">'
                    'Sin estudiantes registrados.</p>')
        rows = ''.join(
            '<tr>'
            '<td style="padding:8px 12px;font-weight:600;color:#1a2c5b;">%s</td>'
            '<td style="padding:8px 12px;color:#5d7a9a;">%s</td>'
            '</tr>' % (s.name or '—', s.grade or '—')
            for s in students
        )
        return ("""
<table width="100%%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;background:#f8faff;border-radius:10px;overflow:hidden;margin:12px 0;">
  <tr style="background:#e8edf5;">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#1a2c5b;font-weight:700;
               text-transform:uppercase;letter-spacing:.5px;">Estudiante</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#1a2c5b;font-weight:700;
               text-transform:uppercase;letter-spacing:.5px;">Grado 2025-2026</th>
  </tr>
  %s
</table>""") % rows

    def _build_step_notification_html(self, idx):
        cfg = STEP_NOTIFY[idx]
        partner_name = self.partner_id.name or '—'
        reason = self.exit_reason or '<em style="color:#8096b4;">No especificado</em>'
        body = """
<div style="background:{bg};border-left:4px solid {color};padding:14px 18px;border-radius:0 10px 10px 0;margin-bottom:20px;">
  <p style="margin:0;font-size:15px;font-weight:700;color:{color};">{banner}</p>
</div>
<p style="font-size:14px;line-height:1.7;margin:0 0 14px;color:#4a5568;">{intro}</p>
<p style="font-size:13px;font-weight:600;color:#1a2c5b;margin:16px 0 6px;">Estudiante(s) en egreso:</p>
{student_rows}
<p style="font-size:13px;font-weight:600;color:#1a2c5b;margin:20px 0 6px;">Motivo de retiro:</p>
<div style="background:#fdf2e9;border:1px solid #f5cba7;border-radius:8px;padding:14px 16px;
            font-size:13px;color:#4a5568;line-height:1.7;">{reason}</div>
{cta}""".format(
            bg=cfg['banner_bg'], color=cfg['banner_color'], banner=cfg['banner'],
            intro=cfg['intro'] % partner_name,
            student_rows=self._student_rows_html(),
            reason=reason,
            cta=_cta_button(self._backend_url(), 'Ver expediente de egreso en Odoo →', '#7d3c00'),
        )
        return _email_wrapper(
            header_title=cfg['header'],
            header_subtitle='Egreso / Retiro 2025-2026 · Proceso interno',
            header_color=cfg['banner_color'],
            body_html=body,
        )

    def _notify_step(self, idx):
        """Fire the staff-internal email for a notified step (2 or 5)."""
        self.ensure_one()
        cfg = STEP_NOTIFY.get(idx)
        if not cfg:
            return
        self.env['mail.mail'].sudo().create({
            'subject': cfg['subject'] % (self.partner_id.name or '—'),
            'email_from': SOPORTE_EMAIL,
            'email_to': SOPORTE_EMAIL,
            'email_cc': cfg['cc'],
            'reply_to': SOPORTE_EMAIL,
            'body_html': self._build_step_notification_html(idx),
            'state': 'outgoing',
        })
        self.message_post(
            body='📧 Notificación de egreso (paso #%d) enviada a %s · CC %s.' % (
                idx, SOPORTE_EMAIL, cfg['cc']),
            message_type='comment', subtype_xmlid='mail.mt_note')
        try:
            self.env.ref('base.ir_cron_mail_scheduler_action').sudo().method_direct_trigger()
        except Exception:
            pass

    # -- staff one-click clearance + hard gate ----------------------------

    def _set_step(self, idx, state):
        """Mark step `idx` to `state`. Steps 3-5 are gated behind 1+2."""
        self.ensure_one()
        if not 1 <= idx <= N_STEPS:
            raise UserError('Paso de egreso inválido: %s' % idx)
        if state in DONE_STATES and idx >= 3:
            incomplete = [
                i for i in WITHDRAWAL_GATE_STEPS
                if self['step%d_state' % i] not in DONE_STATES
            ]
            if incomplete:
                raise UserError(
                    'Antes de desincorporar de plataformas/registros debe completar '
                    'la solvencia (paso 1) y la documentación de egreso (paso 2). '
                    'Pendiente(s): %s.' % ', '.join('#%d' % i for i in incomplete))
        prefix = 'step%d' % idx
        was_done = self[prefix + '_state'] in DONE_STATES
        vals = {prefix + '_state': state}
        if state in DONE_STATES:
            vals[prefix + '_cleared_by'] = self.env.uid
            vals[prefix + '_cleared_at'] = fields.Datetime.now()
        else:
            vals[prefix + '_cleared_by'] = False
            vals[prefix + '_cleared_at'] = False
        self.write(vals)
        label = WITHDRAWAL_STEP_DEFS[idx - 1][1]
        self.message_post(
            body='Egreso · paso #%d (%s) → %s por %s.' % (
                idx, label, dict(STEP_STATES).get(state, state), self.env.user.name),
            message_type='comment', subtype_xmlid='mail.mt_note')
        # Phase 3: notify on transition INTO a done state for steps 2 & 5 only
        # (skip re-confirmations so staff aren't double-emailed).
        if idx in STEP_NOTIFY and state in DONE_STATES and not was_done:
            self._notify_step(idx)

    def action_clear_step(self):
        self._set_step(self.env.context.get('step', 0), 'done_manual')

    def action_reopen_step(self):
        self._set_step(self.env.context.get('step', 0), 'pending')
