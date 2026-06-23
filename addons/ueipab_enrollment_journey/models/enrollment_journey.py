# -*- coding: utf-8 -*-
import json
import logging
import re
import uuid
from urllib.parse import quote

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SOPORTE_EMAIL = 'soporte@ueipab.edu.ve'
# Internal staff inbox for S0 response notifications. These carry the Odoo
# backend link ("Ver expediente en Odoo →") and must NEVER reach customers,
# who are not yet involved in the Odoo business process.
PAGOS_EMAIL = 'pagos@ueipab.edu.ve'
# Admissions/finance follow-up team CC'd on the internal S0 notifications
# (both confirmed and declined).
INTERNAL_S0_CC = (
    'lorena.reyes@ueipab.edu.ve,'
    'arcides.arzola@ueipab.edu.ve,'
    'josefina.rodriguez@ueipab.edu.ve'
)
LOGO_URL = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
# Public annual-report page (static, nginx). The blast links here with
# ?j=<journey_url> so the report's CTA can route the parent back to their journey.
REPORT_URL = 'https://dev.ueipab.edu.ve/reporte-anual-2025-2026/'

STEP_STATES = [
    ('pending', 'Pendiente'),
    ('in_progress', 'En proceso'),
    ('done_auto', 'Completado (auto)'),
    ('done_manual', 'Completado (manual)'),
    ('blocked', 'Bloqueado'),
]

DONE_STATES = ('done_auto', 'done_manual')
BLOCK1_STEPS = (1, 2, 3)

STEP_DEFS = [
    ('step1', 'Cotización confirmada',
     'Tu cotización de inscripción ha sido registrada y confirmada por el equipo de ventas.'),
    ('step2', 'Acuerdo de Inscripción firmado',
     'Firma el Acuerdo de Inscripción (incluye los Términos y Condiciones del convenio) '
     'y entrégalo a Atención al Representante.'),
    ('step3', 'Contrato Educativo firmado',
     'Firma el Contrato de Servicio Educativo en nuestras instalaciones. '
     'El documento quedará en resguardo hasta completar el plan de pagos establecido.'),
    ('step4', 'Registro Akdemia completo',
     'Completa los pasos de inscripción en la plataforma Akdemia. '
     'Nuestro equipo de soporte verificará tu registro.'),
    ('step5', 'Cuenta Dawere habilitada',
     'El equipo de IT habilitará la cuenta de cada estudiante en Dawere. '
     'Recibirás las credenciales de acceso por correo.'),
    ('step6', 'Cuenta @ueipab.edu.ve actualizada',
     'Activamos o actualizamos la cuenta institucional de Google Workspace de cada estudiante.'),
    ('step7', 'Google Classroom',
     'Inscribimos a cada estudiante en los Google Classroom de sus profesores '
     'según su grado y sección.'),
    ('step8', 'Guía de Inglés entregada',
     'Confirma haber recibido la guía del programa de inglés para el año escolar 2026-2027.'),
    ('step9', 'Expediente físico actualizado',
     'Nuestro equipo verificará que el expediente físico de cada estudiante esté '
     'completo y actualizado con toda la documentación requerida.'),
]

BLOCK_DEFS = [
    ('🏛️ Inscripción Formal', list(range(1, 4))),
    ('💻 Activación de Plataformas', list(range(4, 8))),
    ('📁 Cierre Administrativo', list(range(8, 10))),
]


def _is_graduating_grade(grade):
    """True for 5° Año (final bachillerato year). Law guarantees graduation — not a re-enrollment decision."""
    if not grade:
        return False
    g = grade.lower().replace('°', '').replace('º', '').strip()
    return g.startswith('5') and 'a' in g


def _next_grade(grade):
    """Increments leading digit: '3° Grado' → '4° Grado', '2° Año' → '3° Año'."""
    if not grade:
        return ''
    m = re.match(r'^(\d+)(.*)', grade.strip())
    return ('%d%s' % (int(m.group(1)) + 1, m.group(2))) if m else grade


# ---------------------------------------------------------------------------
# Email HTML builders
# ---------------------------------------------------------------------------

def _email_wrapper(header_title, header_subtitle, header_color, body_html):
    """Shared branded wrapper for all S0 notification emails."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
</head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;color:#2c3e50;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4fa;padding:32px 16px;">
<tr><td>
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(26,44,91,0.13);">
  <!-- Header -->
  <tr>
    <td style="background:{header_color};padding:28px 32px;text-align:center;">
      <img src="{LOGO_URL}" width="72" height="72"
           style="border-radius:50%;border:3px solid #f0c400;margin-bottom:14px;display:block;margin-left:auto;margin-right:auto;"
           alt="UEIPAB"/>
      <div style="color:#f0c400;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;">
        U.E. Instituto Privado Andrés Bello
      </div>
      <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;line-height:1.3;">{header_title}</h1>
      <p style="margin:6px 0 0;color:#cdd9ee;font-size:13px;">{header_subtitle}</p>
    </td>
  </tr>
  <!-- Body -->
  <tr>
    <td style="padding:28px 32px;">
      {body_html}
    </td>
  </tr>
  <!-- Footer -->
  <tr>
    <td style="background:#f8faff;border-top:1px solid #e8edf5;padding:16px 32px;text-align:center;">
      <p style="margin:0;font-size:12px;color:#8096b4;line-height:1.7;">
        ¿Tiene dudas? Escríbanos a
        <a href="mailto:{SOPORTE_EMAIL}" style="color:#2471a3;text-decoration:none;">{SOPORTE_EMAIL}</a><br/>
        U.E. Instituto Privado Andrés Bello · El Tigre, Anzoátegui · RIF J-080086171
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _student_list_html(students):
    """Renders an inline student table for email bodies."""
    if not students:
        return '<p style="color:#8096b4;font-size:13px;font-style:italic;">Sin estudiantes registrados.</p>'
    rows = ''.join(
        f'<tr>'
        f'<td style="padding:8px 12px;font-weight:600;color:#1a2c5b;">{s["name"]}</td>'
        f'<td style="padding:8px 12px;color:#5d7a9a;">{s["grade_display"]}</td>'
        f'</tr>'
        for s in students
    )
    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;background:#f8faff;border-radius:10px;overflow:hidden;margin:12px 0;">
  <tr style="background:#e8edf5;">
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#1a2c5b;font-weight:700;
               text-transform:uppercase;letter-spacing:.5px;">Estudiante</th>
    <th style="padding:8px 12px;text-align:left;font-size:12px;color:#1a2c5b;font-weight:700;
               text-transform:uppercase;letter-spacing:.5px;">Grado 2026-2027</th>
  </tr>
  {rows}
</table>"""


def _cta_button(url, label, color='#1a2c5b'):
    return f"""
<div style="text-align:center;margin:24px 0 8px;">
  <a href="{url}"
     style="display:inline-block;background:{color};color:#ffffff;font-weight:700;
            font-size:15px;padding:14px 32px;border-radius:10px;text-decoration:none;
            letter-spacing:.3px;">
    {label}
  </a>
</div>"""


class EnrollmentJourney(models.Model):
    _name = 'enrollment.journey'
    _description = 'Enrollment Journey 2026-2027'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    partner_id = fields.Many2one('res.partner', string='Representante', required=True, index=True)
    order_id = fields.Many2one('sale.order', string='Cotización')
    access_token = fields.Char(string='Token', index=True, copy=False)
    academic_year = fields.Char(default='2026-2027')
    active = fields.Boolean(default=True)

    student_ids = fields.One2many('enrollment.journey.student', 'journey_id', string='Estudiantes')

    contract_number = fields.Char(string='Nro. de Control', copy=False, readonly=True)
    contract_date = fields.Date(string='Fecha del Contrato', copy=False)
    contract_retained = fields.Boolean(
        string='Contrato en custodia', default=False,
        help='El contrato fue firmado pero permanece retenido hasta completar el cronograma de pagos.')
    contract_released_date = fields.Date(
        string='Fecha de entrega del contrato', readonly=True, copy=False)

    # Step 0 — Continuation confirmation gate
    continuation_status = fields.Selection([
        ('pending',   'Pendiente de confirmación'),
        ('confirmed', 'Continúa'),
        ('declined',  'No continúa'),
    ], default='pending', string='Continuidad', index=True)
    decline_reason    = fields.Text('Motivo de retiro', readonly=True, copy=False)
    confirmation_date = fields.Datetime('Fecha de confirmación', readonly=True, copy=False)
    decline_date      = fields.Datetime('Fecha de retiro', readonly=True, copy=False)

    # Blast email tracking
    blast_sent_date = fields.Datetime('Email S0 enviado', readonly=True, copy=False)
    email_missing   = fields.Boolean('Sin email', default=False, copy=False)

    # WA escalation
    wa_sent_date  = fields.Datetime('WA enviado', readonly=True, copy=False)
    phone_missing = fields.Boolean('Sin teléfono', default=False, copy=False)
    email_bounced = fields.Boolean('Email rebotado', default=False)

    # Block 1 — Inscripción Formal
    step1_state = fields.Selection(STEP_STATES, default='pending', string='1. Cotización')
    step2_state = fields.Selection(STEP_STATES, default='pending', string='2. Acuerdo firmado')
    step3_state = fields.Selection(STEP_STATES, default='pending', string='3. Contrato firmado')
    # Block 2 — Activación de Plataformas
    step4_state = fields.Selection(STEP_STATES, default='pending', string='4. Akdemia')
    step5_state = fields.Selection(STEP_STATES, default='pending', string='5. Dawere')
    step6_state = fields.Selection(STEP_STATES, default='pending', string='6. Correo @ueipab')
    step7_state = fields.Selection(STEP_STATES, default='pending', string='7. Classroom')
    # Block 3 — Cierre Administrativo
    step8_state = fields.Selection(STEP_STATES, default='pending', string='8. Guía Inglés')
    step9_state = fields.Selection(STEP_STATES, default='pending', string='9. Expediente')

    step1_cleared_by = fields.Many2one('res.users', readonly=True)
    step2_cleared_by = fields.Many2one('res.users', readonly=True)
    step3_cleared_by = fields.Many2one('res.users', readonly=True)
    step4_cleared_by = fields.Many2one('res.users', readonly=True)
    step5_cleared_by = fields.Many2one('res.users', readonly=True)
    step6_cleared_by = fields.Many2one('res.users', readonly=True)
    step7_cleared_by = fields.Many2one('res.users', readonly=True)
    step8_cleared_by = fields.Many2one('res.users', readonly=True)
    step9_cleared_by = fields.Many2one('res.users', readonly=True)

    step1_cleared_at = fields.Datetime(readonly=True)
    step2_cleared_at = fields.Datetime(readonly=True)
    step3_cleared_at = fields.Datetime(readonly=True)
    step4_cleared_at = fields.Datetime(readonly=True)
    step5_cleared_at = fields.Datetime(readonly=True)
    step6_cleared_at = fields.Datetime(readonly=True)
    step7_cleared_at = fields.Datetime(readonly=True)
    step8_cleared_at = fields.Datetime(readonly=True)
    step9_cleared_at = fields.Datetime(readonly=True)

    current_step = fields.Integer(compute='_compute_progress', store=True)
    progress_pct = fields.Integer(compute='_compute_progress', store=True, string='Progreso %')
    journey_url = fields.Char(compute='_compute_journey_url', string='Página del Representante')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('access_token'):
                vals['access_token'] = str(uuid.uuid4())
        return super().create(vals_list)

    @api.depends('partner_id', 'academic_year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s — %s' % (rec.partner_id.name or '?', rec.academic_year)

    @api.depends('step1_state', 'step2_state', 'step3_state',
                 'step4_state', 'step5_state', 'step6_state',
                 'step7_state', 'step8_state', 'step9_state')
    def _compute_progress(self):
        for rec in self:
            done = 0
            current = 0
            for idx, (prefix, _t, _h) in enumerate(STEP_DEFS, start=1):
                if rec[prefix + '_state'] in DONE_STATES:
                    done += 1
                elif not current:
                    current = idx
            rec.progress_pct = int(done * 100 / len(STEP_DEFS))
            rec.current_step = current or len(STEP_DEFS)

    def _compute_journey_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.journey_url = '%s/enrollment-journey/%s' % (base, rec.access_token)

    # -- helpers -----------------------------------------------------------

    def _enrolling_students(self):
        """Students excluding graduating 5° Año — used in Step 0 display."""
        return [s for s in self.student_ids if not _is_graduating_grade(s.grade)]

    def _student_dicts(self, for_step0=False):
        """Returns list of dicts with display info for emails and Step 0 page."""
        students = self._enrolling_students() if for_step0 else list(self.student_ids)
        result = []
        for s in students:
            next_g = _next_grade(s.grade) if s.grade else ''
            grade_display = ('%s → %s' % (s.grade, next_g)) if next_g and s.grade != next_g else (s.grade or '')
            result.append({'name': s.name, 'grade': s.grade or '', 'grade_display': grade_display})
        return result

    def _backend_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '%s/web#model=enrollment.journey&id=%d&view_type=form' % (base, self.id)

    # -- Step 0 actions ----------------------------------------------------

    def action_reset_confirmation(self):
        """Staff resets continuation gate back to pending (e.g. parent submitted by mistake)."""
        for rec in self:
            rec.write({
                'continuation_status': 'pending',
                'decline_reason': False,
                'confirmation_date': False,
                'decline_date': False,
            })
            rec.message_post(
                body='🔄 Confirmación S0 restablecida a pendiente por %s.' % self.env.user.name,
                message_type='comment', subtype_xmlid='mail.mt_note')

    # -- Blast email (Moment 1) -------------------------------------------

    def action_send_blast_email(self):
        """Send Step 0 invitation email. Can be called from list (multi-record) or form."""
        sent = skipped = 0
        for rec in self:
            email = rec.partner_id.email
            if not email:
                rec.email_missing = True
                rec.message_post(
                    body='⚠️ Email S0 no enviado: el representante no tiene email registrado.',
                    message_type='comment', subtype_xmlid='mail.mt_note')
                skipped += 1
                continue
            self.env['mail.mail'].sudo().create({
                'subject': 'Proceso de Inscripción 2026-2027 — Confirme la continuidad de su(s) representado(s)',
                'email_from': SOPORTE_EMAIL,
                'email_to': email,
                'email_cc': SOPORTE_EMAIL,
                'reply_to': SOPORTE_EMAIL,
                'body_html': rec._build_blast_email_html(),
                'state': 'outgoing',
            })
            rec.blast_sent_date = fields.Datetime.now()
            rec.email_missing = False
            rec.message_post(
                body='📧 Email S0 enviado a %s.' % email,
                message_type='comment', subtype_xmlid='mail.mt_note')
            sent += 1
        try:
            self.env.ref('base.ir_cron_mail_scheduler_action').sudo().method_direct_trigger()
        except Exception:
            pass
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': 'Email S0',
                'message': '%d enviado(s), %d sin email.' % (sent, skipped),
                'type': 'success' if sent else 'warning',
                'sticky': False,
            },
        }

    def _report_cta_block(self, journey_url):
        """Secondary 'annual report' card embedded in the blast (timing option b).
        Links to the public report carrying ?j=<journey_url> so the report's own
        CTA can route the parent back to their personal journey."""
        report_url = '%s?j=%s' % (REPORT_URL, quote(journey_url or '', safe=''))
        return (
            '<table width="100%%" cellpadding="0" cellspacing="0" style="margin:18px 0 0;">'
            '<tr><td style="background:#f8faff;border:1px solid #e0e7f0;border-radius:12px;'
            'padding:18px 20px;text-align:center;">'
            '<p style="margin:0 0 4px;font-size:13px;font-weight:700;color:#1a2c5b;">'
            '📘 Antes de decidir, conozca nuestro año</p>'
            '<p style="margin:0 0 12px;font-size:13px;color:#5d7a9a;line-height:1.6;">'
            'Vea el <strong>Reporte Ejecutivo Académico 2025-2026</strong>: nuestros logros, '
            'el oro regional en robótica, la llegada de <strong>Glenda</strong> (IA) y nuestro '
            'ecosistema de aliados.</p>'
            '%s</td></tr></table>'
        ) % _cta_button(report_url, 'Ver el Reporte Anual 2025-2026 →', '#2471a3')

    def _build_blast_email_html(self):
        partner_name = self.partner_id.name or 'Representante'
        students = self._student_dicts(for_step0=True)
        journey_url = self.journey_url

        if students:
            bullet_rows = ''.join(
                '<tr>'
                '<td style="padding:7px 14px;font-size:14px;color:#1a2c5b;line-height:1.5;">'
                '<span style="color:#f0c400;font-weight:900;margin-right:6px;">•</span>'
                '<strong>%s</strong>'
                '%s'
                '</td>'
                '</tr>' % (
                    s['name'],
                    '&nbsp;&nbsp;<span style="color:#5d7a9a;font-size:13px;">%s</span>' % s['grade_display']
                    if s['grade_display'] else ''
                )
                for s in students
            )
            student_block = (
                '<p style="margin:20px 0 10px;font-size:15px;font-weight:700;color:#1a2c5b;">'
                '¿Continuarán con nosotros el próximo año escolar 2026-2027?</p>'
                '<table width="100%%" cellpadding="0" cellspacing="0" '
                'style="background:#f8faff;border-radius:10px;border:1px solid #e0e7f0;'
                'margin:0 0 20px;">%s</table>'
            ) % bullet_rows
        else:
            student_block = (
                '<p style="margin:20px 0 10px;font-size:15px;font-weight:700;color:#1a2c5b;">'
                '¿Continuarán con nosotros el próximo año escolar 2026-2027?</p>'
            )

        body = """
<p style="font-size:15px;line-height:1.7;margin:0 0 16px;color:#2c3e50;">
  Estimado/a representante <strong>{partner_name}</strong>:
</p>
<p style="font-size:14px;line-height:1.8;margin:0 0 8px;color:#4a5568;">
  Estimado(a) representante, por favor, sírvase indicar a través de esta breve encuesta
  si sus representados(as) continuarán cursando estudios en éste plantel educativo en el
  próximo período académico <strong>2026-2027</strong>. Esta información es importante
  para nuestra planificación y gestión de un servicio educativo diferencial.
</p>
{student_block}
<p style="font-size:14px;line-height:1.8;margin:0 0 20px;color:#4a5568;">
  Por favor, haga clic en el botón a continuación para responder. El proceso toma
  menos de un minuto y podrá seguir el avance de la inscripción desde esa misma página.
</p>
{cta}
{report_cta}
<p style="font-size:12px;color:#8096b4;margin:20px 0 0;border-top:1px solid #e8edf5;padding-top:14px;">
  Si tiene dificultades para acceder al enlace o tiene preguntas, responda directamente
  a este correo o escríbanos a
  <a href="mailto:{soporte}" style="color:#2471a3;">{soporte}</a>.
</p>""".format(
            partner_name=partner_name,
            student_block=student_block,
            cta=_cta_button(journey_url, 'Responder la encuesta (Sí │ No) continuará →', '#1a2c5b'),
            report_cta=self._report_cta_block(journey_url),
            soporte=SOPORTE_EMAIL,
        )
        return _email_wrapper(
            header_title='ENCUESTA DE CONTINUIDAD PERÍODO ACADÉMICO 2026-2027',
            header_subtitle='Proceso virtual asistido — U.E. Instituto Privado Andrés Bello',
            header_color='#1a2c5b',
            body_html=body,
        )

    # -- Response notification (Moment 2) ---------------------------------

    def _send_response_notification(self, response_type):
        """Auto-fires when parent POSTs confirm or decline from the public page.

        Splits into TWO emails so the customer never sees the Odoo backend:
          1) Internal staff copy → pagos@ ONLY, carries the "Ver expediente en
             Odoo →" button (backend link).
          2) Customer copy → parent, with the "Ver flujo de proceso inscripción
             asistido →" button (public journey page) and no Odoo references.
        """
        self.ensure_one()
        partner_email = self.partner_id.email or ''
        if response_type == 'confirmed':
            subject_internal = '[S0 Confirmada] Familia %s' % self.partner_id.name
            subject_customer = 'Confirmación recibida — Inscripción 2026-2027'
            internal_html = self._build_confirmed_notification_html(audience='internal')
            customer_html = self._build_confirmed_notification_html(audience='customer')
            internal_cc = INTERNAL_S0_CC
        else:
            subject_internal = '[S0 No Continúa] Familia %s' % self.partner_id.name
            subject_customer = 'Hemos recibido su respuesta — Inscripción 2026-2027'
            internal_html = self._build_declined_notification_html(audience='internal')
            customer_html = self._build_declined_notification_html(audience='customer')
            internal_cc = INTERNAL_S0_CC

        Mail = self.env['mail.mail'].sudo()
        # 1) Internal staff copy — pagos@ (+ admissions/finance CC on confirm)
        internal_vals = {
            'subject': subject_internal,
            'email_from': SOPORTE_EMAIL,
            'email_to': PAGOS_EMAIL,
            'body_html': internal_html,
            'state': 'outgoing',
        }
        if internal_cc:
            internal_vals['email_cc'] = internal_cc
        Mail.create(internal_vals)
        # 2) Customer copy — parent only, assisted-flow link, no Odoo references
        if partner_email:
            Mail.create({
                'subject': subject_customer,
                'email_from': SOPORTE_EMAIL,
                'email_to': partner_email,
                'reply_to': SOPORTE_EMAIL,
                'body_html': customer_html,
                'state': 'outgoing',
            })
        try:
            self.env.ref('base.ir_cron_mail_scheduler_action').sudo().method_direct_trigger()
        except Exception:
            pass

    def _build_confirmed_notification_html(self, audience='internal'):
        partner_name = self.partner_id.name or '—'
        confirmed_at = self.confirmation_date
        dt_str = confirmed_at.strftime('%d/%m/%Y %H:%M') if confirmed_at else '—'
        students = self._student_dicts(for_step0=True)

        if audience == 'customer':
            # No Odoo references — point the parent at their public assisted flow.
            lead_line = ('Puede seguir el avance de su inscripción desde su flujo '
                         'asistido en línea, cuando lo desee.')
            cta = _cta_button(self.journey_url,
                              'Ver flujo de proceso inscripción asistido →', '#27ae60')
        else:
            lead_line = ('El proceso de inscripción puede avanzar. Acceda al registro '
                         'en Odoo para continuar con los pasos del Bloque 1.')
            cta = _cta_button(self._backend_url(), 'Ver expediente en Odoo →', '#27ae60')

        body = """
<div style="background:#eafaf1;border-left:4px solid #27ae60;padding:14px 18px;border-radius:0 10px 10px 0;margin-bottom:20px;">
  <p style="margin:0;font-size:15px;font-weight:700;color:#1e8449;">
    ✅ La familia confirmó que SÍ continuará en 2026-2027
  </p>
</div>
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
  <tr>
    <td style="padding:6px 0;color:#5d7a9a;font-size:13px;width:40%;">Representante</td>
    <td style="padding:6px 0;font-weight:600;color:#1a2c5b;font-size:13px;">{partner_name}</td>
  </tr>
  <tr>
    <td style="padding:6px 0;color:#5d7a9a;font-size:13px;">Confirmado el</td>
    <td style="padding:6px 0;font-weight:600;color:#1a2c5b;font-size:13px;">{dt_str}</td>
  </tr>
</table>
<p style="font-size:13px;font-weight:600;color:#1a2c5b;margin:16px 0 6px;">
  Estudiantes confirmados para inscripción:
</p>
{student_list}
<p style="font-size:13px;color:#4a5568;margin:16px 0 4px;line-height:1.6;">
  {lead_line}
</p>
{cta}""".format(
            partner_name=partner_name,
            dt_str=dt_str,
            student_list=_student_list_html(students),
            lead_line=lead_line,
            cta=cta,
        )
        return _email_wrapper(
            header_title='Familia confirmó continuidad',
            header_subtitle='Inscripción 2026-2027 · Respuesta recibida',
            header_color='#1a5c2c',
            body_html=body,
        )

    def _build_declined_notification_html(self, audience='internal'):
        partner_name = self.partner_id.name or '—'
        declined_at = self.decline_date
        dt_str = declined_at.strftime('%d/%m/%Y %H:%M') if declined_at else '—'
        reason = self.decline_reason or '<em style="color:#8096b4;">No especificado</em>'
        students = self._student_dicts(for_step0=True)

        if audience == 'customer':
            cta = _cta_button(self.journey_url,
                              'Ver flujo de proceso inscripción asistido →', '#e67e22')
        else:
            cta = _cta_button(self._backend_url(), 'Ver expediente en Odoo →', '#e67e22')

        body = """
<div style="background:#fef9e7;border-left:4px solid #e67e22;padding:14px 18px;border-radius:0 10px 10px 0;margin-bottom:20px;">
  <p style="margin:0;font-size:15px;font-weight:700;color:#9c5a00;">
    ⚠️ La familia informó que NO continuará en 2026-2027
  </p>
</div>
<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
  <tr>
    <td style="padding:6px 0;color:#5d7a9a;font-size:13px;width:40%;">Representante</td>
    <td style="padding:6px 0;font-weight:600;color:#1a2c5b;font-size:13px;">{partner_name}</td>
  </tr>
  <tr>
    <td style="padding:6px 0;color:#5d7a9a;font-size:13px;">Respuesta registrada el</td>
    <td style="padding:6px 0;font-weight:600;color:#1a2c5b;font-size:13px;">{dt_str}</td>
  </tr>
</table>
<p style="font-size:13px;font-weight:600;color:#1a2c5b;margin:16px 0 6px;">Estudiantes afectados:</p>
{student_list}
<p style="font-size:13px;font-weight:600;color:#1a2c5b;margin:20px 0 6px;">Motivo indicado por el representante:</p>
<div style="background:#fdf2e9;border:1px solid #f5cba7;border-radius:8px;padding:14px 16px;
            font-size:13px;color:#4a5568;line-height:1.7;">
  {reason}
</div>
<div style="background:#fff8e6;border-left:4px solid #f0c400;padding:12px 16px;
            border-radius:0 8px 8px 0;margin:20px 0;font-size:13px;color:#7d5000;line-height:1.6;">
  <strong>Recordatorio — Solvencia administrativa:</strong><br/>
  Para formalizar el retiro, el representante debe contar con la solvencia administrativa
  correspondiente al pago total del año escolar 2025-2026 en curso (mensualidades de
  julio y agosto pendientes).
</div>
{cta}""".format(
            partner_name=partner_name,
            dt_str=dt_str,
            student_list=_student_list_html(students),
            reason=reason,
            cta=cta,
        )
        return _email_wrapper(
            header_title='Familia no continuará en 2026-2027',
            header_subtitle='Inscripción 2026-2027 · Respuesta recibida',
            header_color='#7d3c00',
            body_html=body,
        )

    # -- WA escalation (Moment 3) -----------------------------------------

    def action_send_wa(self):
        """Staff manually triggers WA escalation (e.g. after email bounce)."""
        self.ensure_one()
        partner = self.partner_id
        phone = partner.mobile or partner.phone
        if not phone:
            self.phone_missing = True
            self.message_post(
                body='⚠️ WA no enviado: el representante no tiene móvil ni teléfono registrado. '
                     'Actualice los datos de contacto en el perfil del Representante.',
                message_type='comment', subtype_xmlid='mail.mt_note')
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {
                    'title': 'Sin teléfono registrado',
                    'message': 'Actualice el móvil/teléfono del representante e intente de nuevo.',
                    'type': 'warning', 'sticky': True,
                },
            }

        students = self._enrolling_students()
        if students:
            names = ', '.join(s.name for s in students)
        else:
            names = 'su(s) representado(s)'

        journey_url = self.journey_url
        dry_run = self.env['ir.config_parameter'].sudo().get_param('ai_agent.dry_run', 'True')
        is_dry = str(dry_run).lower() in ('true', '1', 'yes')

        wa_text = (
            'Estimado/a Representante, le contactamos de parte de U.E. Instituto Privado '
            'Andrés Bello. Tiene pendiente confirmar la inscripción de %s para el año '
            'escolar 2026-2027. Por favor acceda al siguiente enlace para responder: %s '
            '— Si tiene dudas escríbanos a %s.' % (names, journey_url, SOPORTE_EMAIL)
        )

        if is_dry:
            self.message_post(
                body='📱 WA (dry_run activo — no enviado) → %s<br/><pre>%s</pre>' % (phone, wa_text),
                message_type='comment', subtype_xmlid='mail.mt_note')
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {
                    'title': 'WA en modo dry_run',
                    'message': 'Mensaje registrado en el chatter. Active WA (dry_run=False) para enviar.',
                    'type': 'info', 'sticky': False,
                },
            }

        try:
            config_path = '/opt/odoo-dev/config/whatsapp_massiva.json'
            with open(config_path) as fh:
                wa_cfg = json.load(fh)
            import requests as _req
            resp = _req.post(
                wa_cfg['base_url'].rstrip('/') + '/api/send/whatsapp',
                json={
                    'secret': wa_cfg['secret'],
                    'account': wa_cfg.get('account', wa_cfg.get('key_name', 'ueipab1')),
                    'recipient': phone,
                    'type': 'text',
                    'message': wa_text,
                },
                timeout=15,
            )
            resp.raise_for_status()
            self.wa_sent_date = fields.Datetime.now()
            self.phone_missing = False
            self.message_post(
                body='📱 WA enviado a %s.' % phone,
                message_type='comment', subtype_xmlid='mail.mt_note')
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'WA enviado', 'message': 'Mensaje enviado a %s.' % phone,
                           'type': 'success', 'sticky': False},
            }
        except Exception as exc:
            _logger.error('WA send failed for journey %s: %s', self.id, exc)
            self.message_post(
                body='⚠️ Error enviando WA a %s: %s' % (phone, exc),
                message_type='comment', subtype_xmlid='mail.mt_note')
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Error WA', 'message': str(exc), 'type': 'danger', 'sticky': True},
            }

    # -- staff one-click clearance ----------------------------------------

    def _set_step(self, idx, state):
        self.ensure_one()
        if state in DONE_STATES and idx >= 4:
            incomplete = [
                i for i in BLOCK1_STEPS
                if self['step%d_state' % i] not in DONE_STATES
            ]
            if incomplete:
                raise UserError(
                    'Completa primero el Bloque 1 — Inscripción Formal. '
                    'Los pasos %s aún no están completados.'
                    % ', '.join('#%d' % i for i in incomplete)
                )
        prefix = 'step%d' % idx
        vals = {prefix + '_state': state}
        if state in DONE_STATES:
            vals[prefix + '_cleared_by'] = self.env.uid
            vals[prefix + '_cleared_at'] = fields.Datetime.now()
            if idx == 3:
                vals['contract_retained'] = True
        elif idx == 3:
            vals['contract_retained'] = False
            vals['contract_released_date'] = False
        self.write(vals)

    def action_clear_step(self):
        self._set_step(self.env.context.get('step', 0), 'done_manual')

    def action_reopen_step(self):
        self._set_step(self.env.context.get('step', 0), 'in_progress')

    def action_release_contract(self):
        self.ensure_one()
        self.write({
            'contract_retained': False,
            'contract_released_date': fields.Date.context_today(self),
        })

    def action_open_journey_page(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.journey_url, 'target': 'new'}

    def action_print_contract(self):
        for rec in self:
            if not rec.contract_number:
                rec.contract_number = self.env['ir.sequence'].next_by_code('enrollment.contract')
            if not rec.contract_date:
                rec.contract_date = fields.Date.context_today(rec)
        return self.env.ref(
            'ueipab_enrollment_journey.action_report_enrollment_contract').report_action(self)

    def action_run_soft_checks(self):
        for rec in self:
            if rec.order_id and rec.order_id.state == 'sale' \
                    and rec.step1_state not in DONE_STATES:
                rec.step1_state = 'done_auto'
                rec.step1_cleared_at = fields.Datetime.now()
            if rec.step3_state in DONE_STATES and rec.contract_retained and rec.order_id:
                invoices = rec.order_id.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted'
                    and inv.move_type in ('out_invoice', 'out_refund')
                )
                if invoices and all(inv.amount_residual == 0 for inv in invoices):
                    rec.contract_retained = False
                    rec.contract_released_date = fields.Date.context_today(rec)


class EnrollmentJourneyStudent(models.Model):
    _name = 'enrollment.journey.student'
    _description = 'Enrollment Journey Student'

    journey_id = fields.Many2one('enrollment.journey', required=True, ondelete='cascade')
    name = fields.Char(string='Estudiante', required=True)
    cedula = fields.Char(string='Cédula/Cédula Escolar')
    grade = fields.Char(string='Grado/Año')
    institutional_email = fields.Char(string='Correo @ueipab')
    insurance_policy = fields.Char(string='Nº Póliza Seguro')
