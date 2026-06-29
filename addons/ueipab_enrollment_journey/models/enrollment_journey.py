# -*- coding: utf-8 -*-
import base64
import hashlib
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
# Overridable per-env via ir.config_parameter 'enrollment.report_url' (prod sets
# its own host); this constant is the dev fallback.
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

QUOTE_STATES = [
    ('none',               'Sin cotización'),
    ('draft',              'Borrador'),
    ('sent',               'Enviada al representante'),
    ('accepted',           'Aceptada'),
    ('revision_requested', 'Revisión solicitada'),
]

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


def _s(value):
    """Coerce any API value to a stripped string ('' for None)."""
    return ('' if value is None else str(value)).strip()


def _normalize_cedula(value):
    """Reduce a cédula/VAT to comparable digits — strips V/E/J/G/P prefix,
    dashes, dots and spaces. 'V-14.641.877' → '14641877'. Used as the match
    key between Odoo partner.vat and Akdemia guardian unique_id."""
    if not value:
        return ''
    return re.sub(r'\D', '', str(value))


def _line_key(cedula, name):
    """Stable match key for a student line. Falls back to the normalized name
    when the cédula is blank (preescolar/young pupils often have no cédula
    escolar yet) so those students still match across re-syncs instead of being
    re-created every time."""
    c = _normalize_cedula(cedula)
    return c if c else 'n:' + _s(name).lower().strip()


# ---------------------------------------------------------------------------
# Email HTML builders
# ---------------------------------------------------------------------------

def _email_wrapper(header_title, header_subtitle, header_color, body_html,
                   contact_email=SOPORTE_EMAIL):
    """Shared branded wrapper for all S0 notification emails. ``contact_email``
    is the address shown in the footer "¿Tiene dudas?" link (defaults to
    soporte@; callers pass self._enroll_addr('contact') to use the configured
    enrollment inbox)."""
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
        <a href="mailto:{contact_email}" style="color:#2471a3;text-decoration:none;">{contact_email}</a><br/>
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
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    partner_id = fields.Many2one('res.partner', string='Representante', required=True, index=True)
    order_id = fields.Many2one('sale.order', string='Cotización')
    access_token = fields.Char(string='Token', index=True, copy=False)

    # Quotation lifecycle (accept / revision + version control)
    quote_state = fields.Selection(
        QUOTE_STATES, default='none', string='Estado cotización',
        index=True, copy=False, tracking=True)
    quote_sent_date     = fields.Datetime('Cotización enviada', readonly=True, copy=False)
    quote_accepted_date = fields.Datetime('Cotización aceptada', readonly=True, copy=False)
    quote_revision_reason = fields.Text('Motivo de revisión', readonly=True, copy=False)
    quote_version = fields.Integer('Versión actual', default=0, copy=False, readonly=True)
    quote_version_ids = fields.One2many(
        'enrollment.quote.version', 'journey_id', string='Versiones de cotización')
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

    # In-person assist (support team drives the process at the premises)
    enrollment_mode = fields.Selection([
        ('online',     'En línea (autogestión)'),
        ('presencial', 'Presencial (atendido en sede)'),
    ], default='online', string='Modalidad', index=True, copy=False)
    assisted_by = fields.Many2one(
        'res.users', string='Atendido por', copy=False,
        help='Agente de soporte que acompañó a la familia en sede.')

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

    # Checklist notes (per step) — for in-person assist (docs received, remarks)
    step1_note = fields.Text('Nota paso 1')
    step2_note = fields.Text('Nota paso 2')
    step3_note = fields.Text('Nota paso 3')
    step4_note = fields.Text('Nota paso 4')
    step5_note = fields.Text('Nota paso 5')
    step6_note = fields.Text('Nota paso 6')
    step7_note = fields.Text('Nota paso 7')
    step8_note = fields.Text('Nota paso 8')
    step9_note = fields.Text('Nota paso 9')

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

    def _ensure_quote(self):
        """Idempotently create the enrollment quotation when the family confirms
        continuity (S0 = 'Sí'). One quote per journey, sized to the enrolling
        (non-graduating) student count, priced at the llamado active on the day
        of confirmation. Returns the linked sale.order, or False if it cannot be
        built (no partner / quote engine error). Never raises — confirmation must
        not fail because of a quote hiccup."""
        self.ensure_one()
        if self.order_id:
            return self.order_id
        if not self.partner_id:
            return False
        n = len(self._enrolling_students()) or 1
        try:
            summ = self.env['sale.order'].sudo().create_ai_quote(
                self.partner_id.id, n, channel='manual')
            order = self.env['sale.order'].browse(summ['order_id'])
            self.order_id = order.id
            if self.quote_state == 'none':
                self.quote_state = 'draft'
            self.message_post(
                body='🧾 Cotización %s generada automáticamente al confirmar '
                     'continuidad (%d estudiante(s), %s, total %s %s). '
                     'Estado: borrador — revísela y use "Enviar cotización".' % (
                         order.name, n, summ['llamado_code'],
                         summ['amount_total'], summ['currency']),
                message_type='comment', subtype_xmlid='mail.mt_note')
            return order
        except Exception as exc:  # noqa: BLE001 — confirmation must survive
            _logger.warning('Auto-quote failed for journey %s: %s', self.id, exc)
            self.message_post(
                body='⚠️ No se pudo generar la cotización automáticamente al '
                     'confirmar continuidad: %s. Genérela manualmente.' % exc,
                message_type='comment', subtype_xmlid='mail.mt_note')
            return False

    # -- Quotation lifecycle: send / accept / revision / re-issue ----------

    def _render_quote_pdf(self):
        """Render the Acuerdo/Cotización report PDF (bytes) for this journey's
        order. Raises if no order."""
        self.ensure_one()
        pdf, _ftype = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'ueipab_sales.action_report_quotation_agreement', [self.order_id.id])
        return pdf

    def current_quote_version(self):
        """The version row the parent is currently looking at (issued or
        accepted), i.e. the one matching quote_version. False if none frozen."""
        self.ensure_one()
        return self.quote_version_ids.filtered(
            lambda v: v.version == self.quote_version
            and v.state in ('issued', 'accepted'))[:1]

    def _freeze_quote_version(self):
        """Freeze the CURRENT order PDF as an immutable version row + attachment
        (the retained 'mensaje de datos'). Supersedes any prior 'issued' row,
        bumps quote_version, returns the new version record. Never raises into
        the caller's flow on a render hiccup — returns False instead."""
        self.ensure_one()
        if not self.order_id:
            return False
        try:
            pdf = self._render_quote_pdf()
        except Exception as exc:  # noqa: BLE001
            _logger.warning('Quote PDF render failed for journey %s: %s', self.id, exc)
            return False
        sha = hashlib.sha256(pdf).hexdigest()
        new_ver = (self.quote_version or 0) + 1
        safe = (self.partner_id.name or 'UEIPAB').replace(' ', '_')
        att = self.env['ir.attachment'].sudo().create({
            'name': 'Cotizacion_%s_v%d.pdf' % (safe, new_ver),
            'type': 'binary',
            'datas': base64.b64encode(pdf),
            'mimetype': 'application/pdf',
            'res_model': 'enrollment.journey',
            'res_id': self.id,
        })
        # Any previously-issued (not yet accepted) version is now superseded.
        self.quote_version_ids.filtered(
            lambda v: v.state == 'issued').write({'state': 'superseded'})
        ver = self.env['enrollment.quote.version'].sudo().create({
            'journey_id': self.id,
            'version': new_ver,
            'order_id': self.order_id.id,
            'amount_total': self.order_id.amount_total,
            'currency_id': self.order_id.currency_id.id,
            'pdf_attachment_id': att.id,
            'pdf_sha256': sha,
            'issued_date': fields.Datetime.now(),
            'issued_by': self.env.uid,
            'state': 'issued',
        })
        self.quote_version = new_ver
        return ver

    def action_send_quote(self):
        """Staff action — initial send AND re-issue after a revision.
        Freezes a new version from the current order, sets state to 'sent',
        clears any prior acceptance/revision, and emails the parent the link."""
        self.ensure_one()
        if not self.order_id:
            raise UserError(
                'No hay cotización vinculada. Genere la cotización antes de enviarla.')
        ver = self._freeze_quote_version()
        if not ver:
            raise UserError(
                'No se pudo generar el PDF de la cotización. Revise la orden de venta.')
        self.write({
            'quote_state': 'sent',
            'quote_sent_date': fields.Datetime.now(),
            'quote_accepted_date': False,
            'quote_revision_reason': False,
        })
        self._send_quote_email()
        self.message_post(
            body='📤 Cotización %s (v%d, %s) enviada al representante para su '
                 'revisión y aceptación.' % (
                     self.order_id.name, ver.version, self.order_id.amount_total),
            message_type='comment', subtype_xmlid='mail.mt_note')
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': 'Cotización enviada',
                'message': 'v%d enviada al representante.' % ver.version,
                'type': 'success', 'sticky': False,
            },
        }

    def _record_acceptance(self, ip, user_agent, tyc):
        """Public flow: the parent accepted the current quote. Captures the
        Tier-2 e-signature evidence (IP, UA, UTC timestamp, T&C, PDF already
        hashed at freeze) and advances step 1. Returns True on success."""
        self.ensure_one()
        if self.quote_state != 'sent':
            return False
        ver = self.current_quote_version()
        now = fields.Datetime.now()
        if ver:
            ver.sudo().write({
                'state': 'accepted',
                'accept_ip': (ip or '')[:64],
                'accept_user_agent': (user_agent or '')[:512],
                'accept_timestamp_utc': now,
                'tyc_accepted': bool(tyc),
            })
        self.write({'quote_state': 'accepted', 'quote_accepted_date': now})
        # Quote accepted == step 1 "Cotización confirmada" complete.
        if self.step1_state not in DONE_STATES:
            self.write({'step1_state': 'done_auto', 'step1_cleared_at': now})
        self._send_quote_accepted_email()
        self.message_post(
            body='✅ El representante ACEPTÓ la cotización %s (v%s) — IP %s, '
                 'T&C %s, %s UTC. Paso 1 completado automáticamente.' % (
                     self.order_id.name if self.order_id else '—',
                     ver.version if ver else '?', ip or '—',
                     'aceptados' if tyc else 'NO aceptados',
                     now.strftime('%Y-%m-%d %H:%M:%S') if now else '—'),
            message_type='comment', subtype_xmlid='mail.mt_note')
        return True

    def _record_acceptance_presencial(self, staff_user_id, attested, signed_attachment_id=False):
        """In-person flow: the family signed the printed Acuerdo (wet signature)
        and a support agent records the acceptance on their behalf. Mirrors
        _record_acceptance but stores presencial evidence (staff attestation +
        optional scanned PDF) instead of the Tier-2 electronic metadata.
        Returns True on success."""
        self.ensure_one()
        if self.quote_state != 'sent':
            return False
        ver = self.current_quote_version()
        now = fields.Datetime.now()
        if ver:
            ver.sudo().write({
                'state': 'accepted',
                'accept_method': 'presencial',
                'accept_staff_user_id': staff_user_id,
                'presencial_attested': bool(attested),
                'tyc_accepted': True,  # wet signature on the printed T&C
                'accept_timestamp_utc': now,
                'signed_pdf_attachment_id': signed_attachment_id or False,
            })
        self.write({'quote_state': 'accepted', 'quote_accepted_date': now})
        if self.step1_state not in DONE_STATES:
            self.write({'step1_state': 'done_auto', 'step1_cleared_at': now})
        self._send_quote_accepted_email()
        staff = self.env['res.users'].browse(staff_user_id).name if staff_user_id else '—'
        self.message_post(
            body='✍️ Aceptación PRESENCIAL de la cotización %s (v%s) registrada por '
                 '%s — firma física %s%s. Paso 1 completado automáticamente.' % (
                     self.order_id.name if self.order_id else '—',
                     ver.version if ver else '?', staff,
                     'certificada' if attested else 'NO certificada',
                     ' · Acuerdo escaneado adjunto' if signed_attachment_id else ''),
            message_type='comment', subtype_xmlid='mail.mt_note')
        return True

    def _record_revision_request(self, reason, ip):
        """Public flow: the parent disagrees and requests a revision. Records
        the evidence on the current version, flips state, and escalates to
        soporte@ CC pagos@. Returns True on success."""
        self.ensure_one()
        if self.quote_state != 'sent':
            return False
        reason = (reason or '').strip()[:2000]
        now = fields.Datetime.now()
        ver = self.current_quote_version()
        if ver:
            ver.sudo().write({
                'revision_reason': reason or None,
                'revision_ip': (ip or '')[:64],
                'revision_timestamp_utc': now,
            })
        self.write({
            'quote_state': 'revision_requested',
            'quote_revision_reason': reason or None,
        })
        self._send_quote_revision_escalation(reason)
        self.message_post(
            body='🕓 El representante SOLICITÓ una revisión de la cotización %s '
                 '(v%s) — IP %s. Escalado a %s (CC %s).<br/>Motivo: %s' % (
                     self.order_id.name if self.order_id else '—',
                     ver.version if ver else '?', ip or '—',
                     self._enroll_addr('escalation'), PAGOS_EMAIL,
                     (reason.replace('<', '&lt;').replace('>', '&gt;')
                      if reason else '<em>sin detalle</em>')),
            message_type='comment', subtype_xmlid='mail.mt_note')
        return True

    # -- Quotation emails --------------------------------------------------

    def _trigger_mail_queue(self):
        try:
            self.env.ref('base.ir_cron_mail_scheduler_action').sudo() \
                .method_direct_trigger()
        except Exception:  # noqa: BLE001 — best-effort flush
            pass

    def _enroll_addr(self, key):
        """Enrollment-funnel email addresses, overridable per-env via
        ir.config_parameter so the whole funnel can move off soporte@ (e.g. to a
        dedicated inscripcion@ admissions inbox) WITHOUT code edits — avoiding
        support-queue congestion from the S0 blast. Defaults preserve the
        original soporte@/pagos@ behaviour until the params are set.

        Keys → params:
          from       → enrollment.notify_from   (From on all funnel emails)
          reply_to   → enrollment.reply_to      (Reply-To on parent-facing emails)
          contact    → enrollment.contact       ("escríbanos a …" link in bodies)
          escalation → enrollment.escalation_to  (revision-request recipient)
          internal   → enrollment.internal_to    (internal S0/quote staff inbox)
          blast_cc   → enrollment.blast_cc        (CC on the S0 blast; set '' to drop)
        """
        icp = self.env['ir.config_parameter'].sudo()
        spec = {
            'from':       ('enrollment.notify_from',   SOPORTE_EMAIL),
            'reply_to':   ('enrollment.reply_to',      SOPORTE_EMAIL),
            'contact':    ('enrollment.contact',       SOPORTE_EMAIL),
            'escalation': ('enrollment.escalation_to', SOPORTE_EMAIL),
            'internal':   ('enrollment.internal_to',   PAGOS_EMAIL),
            # Default '' = NO CC on the blast (the soporte@-congestion fix). Opt
            # in by setting enrollment.blast_cc to an address if a copy is wanted.
            'blast_cc':   ('enrollment.blast_cc',      ''),
        }
        param, default = spec[key]
        return icp.get_param(param, default)

    def _send_quote_email(self):
        """Customer email: the quote is ready to review + accept on the page."""
        self.ensure_one()
        email = self.partner_id.email
        if not email:
            self.message_post(
                body='⚠️ Cotización no enviada por email: el representante no '
                     'tiene email registrado. Comparta el enlace manualmente.',
                message_type='comment', subtype_xmlid='mail.mt_note')
            return
        self.env['mail.mail'].sudo().create({
            'subject': 'Su cotización de inscripción 2026-2027 está lista',
            'email_from': self._enroll_addr('from'),
            'email_to': email,
            'reply_to': self._enroll_addr('reply_to'),
            'body_html': self._build_quote_sent_email_html(),
            'state': 'outgoing',
        })
        self._trigger_mail_queue()

    def _build_quote_sent_email_html(self):
        partner_name = self.partner_id.name or 'Representante'
        students = self._student_dicts(for_step0=True)
        amount = self.order_id.amount_total if self.order_id else 0.0
        currency = self.order_id.currency_id.name if self.order_id else 'USD'
        body = """
<p style="font-size:15px;line-height:1.7;margin:0 0 16px;color:#2c3e50;">
  Estimado/a representante <strong>{partner_name}</strong>:
</p>
<p style="font-size:14px;line-height:1.8;margin:0 0 16px;color:#4a5568;">
  Hemos preparado la <strong>cotización de inscripción</strong> para el año escolar
  <strong>2026-2027</strong>. Puede revisarla, descargarla en PDF y — si está de acuerdo —
  <strong>aceptarla en línea</strong> desde su página de inscripción. Si necesita algún
  ajuste, puede solicitar una revisión desde la misma página.
</p>
{student_list}
<table width="100%%" cellpadding="0" cellspacing="0" style="margin:8px 0 4px;">
  <tr><td style="background:#eaf2fb;border:1px solid #cfe0f5;border-radius:10px;padding:14px 18px;
      text-align:center;font-size:15px;color:#1a2c5b;font-weight:700;">
      Total estimado: {amount:,.2f} {currency}
  </td></tr>
</table>
{cta}
<p style="font-size:12px;color:#8096b4;margin:20px 0 0;border-top:1px solid #e8edf5;padding-top:14px;">
  Si tiene dudas, responda a este correo o escríbanos a
  <a href="mailto:{soporte}" style="color:#2471a3;">{soporte}</a>.
</p>""".format(
            partner_name=partner_name,
            student_list=_student_list_html(students),
            amount=amount, currency=currency,
            cta=_cta_button(self.journey_url,
                            'Ver y aceptar mi cotización →', '#1a2c5b'),
            soporte=self._enroll_addr('contact'),
        )
        return _email_wrapper(
            header_title='SU COTIZACIÓN DE INSCRIPCIÓN 2026-2027',
            header_subtitle='Revise, descargue y acepte en línea — U.E. Instituto Privado Andrés Bello',
            header_color='#1a2c5b',
            body_html=body,
            contact_email=self._enroll_addr('contact'),
        )

    def _send_quote_accepted_email(self):
        """Two copies on acceptance: internal (pagos@) + a customer confirmation."""
        self.ensure_one()
        ver = self.current_quote_version()
        Mail = self.env['mail.mail'].sudo()
        # Internal copy → pagos@
        Mail.create({
            'subject': '[Cotización Aceptada] Familia %s' % self.partner_id.name,
            'email_from': self._enroll_addr('from'),
            'email_to': self._enroll_addr('internal'),
            'body_html': self._build_quote_accepted_html(ver, audience='internal'),
            'state': 'outgoing',
        })
        # Customer confirmation
        if self.partner_id.email:
            Mail.create({
                'subject': 'Cotización aceptada — Inscripción 2026-2027',
                'email_from': self._enroll_addr('from'),
                'email_to': self.partner_id.email,
                'reply_to': self._enroll_addr('reply_to'),
                'body_html': self._build_quote_accepted_html(ver, audience='customer'),
                'state': 'outgoing',
            })
        self._trigger_mail_queue()

    def _build_quote_accepted_html(self, ver, audience='internal'):
        partner_name = self.partner_id.name or '—'
        amount = self.order_id.amount_total if self.order_id else 0.0
        currency = self.order_id.currency_id.name if self.order_id else 'USD'
        ts = ver.accept_timestamp_utc.strftime('%d/%m/%Y %H:%M UTC') if (ver and ver.accept_timestamp_utc) else '—'
        if audience == 'customer':
            lead = ('Hemos registrado la aceptación de su cotización. El siguiente paso '
                    'es firmar el Acuerdo de Inscripción. Puede seguir su proceso desde '
                    'su página de inscripción.')
            cta = _cta_button(self.journey_url,
                              'Ver mi proceso de inscripción →', '#27ae60')
            evidence = ''
        else:
            lead = 'El representante aceptó la cotización en línea. Puede continuar con el Bloque 1.'
            cta = _cta_button(self._backend_url(), 'Ver expediente en Odoo →', '#27ae60')
            evidence = (
                '<div style="background:#f8faff;border:1px solid #e0e7f0;border-radius:8px;'
                'padding:12px 16px;margin:14px 0;font-size:12.5px;color:#5d7a9a;line-height:1.7;">'
                '<strong style="color:#1a2c5b;">Evidencia de aceptación (Ley de Mensajes de '
                'Datos y Firmas Electrónicas):</strong><br/>'
                'Versión: v%s · IP: %s · Fecha/hora: %s · T&amp;C: %s<br/>'
                'SHA-256 PDF: <code style="font-size:11px;">%s</code></div>' % (
                    ver.version if ver else '?', ver.accept_ip if ver else '—', ts,
                    'aceptados' if (ver and ver.tyc_accepted) else 'no',
                    ver.pdf_sha256 if ver else '—')
            )
        body = """
<div style="background:#eafaf1;border-left:4px solid #27ae60;padding:14px 18px;border-radius:0 10px 10px 0;margin-bottom:18px;">
  <p style="margin:0;font-size:15px;font-weight:700;color:#1e8449;">✅ Cotización aceptada</p>
</div>
<p style="font-size:14px;color:#2c3e50;margin:0 0 6px;"><strong>{partner_name}</strong></p>
<p style="font-size:14px;color:#1a2c5b;margin:0 0 12px;font-weight:700;">Total: {amount:,.2f} {currency}</p>
<p style="font-size:13px;color:#4a5568;line-height:1.7;margin:0 0 8px;">{lead}</p>
{evidence}
{cta}""".format(
            partner_name=partner_name, amount=amount, currency=currency,
            lead=lead, evidence=evidence, cta=cta)
        return _email_wrapper(
            header_title='Cotización aceptada',
            header_subtitle='Inscripción 2026-2027',
            header_color='#1a5c2c',
            body_html=body,
            contact_email=self._enroll_addr('contact'),
        )

    def _send_quote_revision_escalation(self, reason):
        """Escalation to soporte@ (creates a Freescout conv) CC pagos@."""
        self.ensure_one()
        reason_html = (reason.replace('<', '&lt;').replace('>', '&gt;')
                       if reason else '<em style="color:#8096b4;">No especificado</em>')
        amount = self.order_id.amount_total if self.order_id else 0.0
        currency = self.order_id.currency_id.name if self.order_id else 'USD'
        body = """
<div style="background:#fef9e7;border-left:4px solid #e67e22;padding:14px 18px;border-radius:0 10px 10px 0;margin-bottom:18px;">
  <p style="margin:0;font-size:15px;font-weight:700;color:#9c5a00;">
    🕓 El representante solicitó una revisión de su cotización
  </p>
</div>
<p style="font-size:14px;color:#2c3e50;margin:0 0 4px;"><strong>{partner_name}</strong></p>
<p style="font-size:13px;color:#5d7a9a;margin:0 0 4px;">Cotización: <strong>{order}</strong> (v{ver}) · Total: {amount:,.2f} {currency}</p>
<p style="font-size:13px;color:#5d7a9a;margin:0 0 4px;">Cédula: {vat} · Email: {email} · Tel: {phone}</p>
<p style="font-size:13px;font-weight:600;color:#1a2c5b;margin:16px 0 6px;">Motivo indicado:</p>
<div style="background:#fdf2e9;border:1px solid #f5cba7;border-radius:8px;padding:14px 16px;font-size:13px;color:#4a5568;line-height:1.7;">{reason_html}</div>
<p style="font-size:13px;color:#4a5568;line-height:1.7;margin:16px 0 8px;">
  <strong>Acción:</strong> contactar al representante, aclarar/ajustar la cotización y luego
  usar <strong>«Re-emitir cotización»</strong> en el expediente para enviar la nueva versión
  (mismo enlace y QR).
</p>
{cta}""".format(
            partner_name=self.partner_id.name or '—',
            order=self.order_id.name if self.order_id else '—',
            ver=self.quote_version, amount=amount, currency=currency,
            vat=self.partner_id.vat or '—',
            email=self.partner_id.email or '—',
            phone=self.partner_id.mobile or self.partner_id.phone or '—',
            reason_html=reason_html,
            cta=_cta_button(self._backend_url(), 'Ver expediente en Odoo →', '#e67e22'),
        )
        html = _email_wrapper(
            header_title='Solicitud de revisión de cotización',
            header_subtitle='Inscripción 2026-2027 · Atención al Representante',
            header_color='#7d3c00',
            body_html=body,
            contact_email=self._enroll_addr('contact'),
        )
        self.env['mail.mail'].sudo().create({
            'subject': '[Cotización - Revisión] Familia %s' % (self.partner_id.name or '—'),
            'email_from': self._enroll_addr('from'),
            'email_to': self._enroll_addr('escalation'),
            'email_cc': PAGOS_EMAIL,
            'reply_to': self._enroll_addr('reply_to'),
            'body_html': html,
            'state': 'outgoing',
        })
        self._trigger_mail_queue()

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

    def _withdrawal_url(self):
        """Deep-link to this journey's egreso (withdrawal) record so staff land on
        the offboarding checklist. Falls back to the journey form if no withdrawal
        exists yet."""
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        w = self.env['enrollment.withdrawal'].sudo().search(
            [('journey_id', '=', self.id)], limit=1)
        if w:
            return '%s/web#model=enrollment.withdrawal&id=%d&view_type=form' % (base, w.id)
        return self._backend_url()

    def _ensure_withdrawal(self):
        """Idempotently create the egreso/withdrawal record when a family declines.
        One withdrawal per journey (partner/students/exit_reason are related fields,
        so they populate from journey_id automatically). Returns the record."""
        self.ensure_one()
        W = self.env['enrollment.withdrawal'].sudo()
        existing = W.search([('journey_id', '=', self.id)], limit=1)
        if existing:
            return existing
        rec = W.create({'journey_id': self.id})
        self.message_post(
            body='🗂️ Expediente de egreso creado automáticamente — la familia no '
                 'continúa en 2026-2027.',
            message_type='comment', subtype_xmlid='mail.mt_note')
        return rec

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

    # -- In-person assist: staff drives the process at the premises --------

    def action_confirm_presencial(self):
        """Staff confirms S0 continuity on the family's behalf (in person).
        Mirrors the public /confirm route exactly: flips the gate, generates the
        auto-quote, and sends the response notification."""
        self.ensure_one()
        if self.continuation_status != 'pending':
            raise UserError('La continuidad ya fue %s; no se puede confirmar de nuevo.'
                            % dict(self._fields['continuation_status'].selection).get(
                                self.continuation_status, self.continuation_status))
        self.write({
            'continuation_status': 'confirmed',
            'confirmation_date': fields.Datetime.now(),
            'enrollment_mode': 'presencial',
            'assisted_by': self.assisted_by.id or self.env.uid,
        })
        self._ensure_quote()
        self._send_response_notification('confirmed')
        self.message_post(
            body='✅ Continuidad CONFIRMADA en sede por %s (modalidad presencial).'
                 % self.env.user.name,
            message_type='comment', subtype_xmlid='mail.mt_note')

    def action_decline_presencial(self):
        """Staff records an in-person decline; opens a small wizard for the reason."""
        self.ensure_one()
        if self.continuation_status != 'pending':
            raise UserError('La continuidad ya fue resuelta; no se puede registrar el retiro.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'No continúa (presencial)',
            'res_model': 'enrollment.presencial.decline.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_journey_id': self.id},
        }

    def action_mark_quote_accepted_presencial(self):
        """Staff records a wet-signature acceptance of the sent quote; opens the
        attestation/attachment wizard."""
        self.ensure_one()
        if self.quote_state != 'sent':
            raise UserError('Solo se puede registrar la aceptación cuando la cotización '
                            'está en estado "Enviada al representante".')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Aceptación presencial de la cotización',
            'res_model': 'enrollment.presencial.accept.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_journey_id': self.id},
        }

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
            blast_vals = {
                'subject': 'Proceso de Inscripción 2026-2027 — Confirme la continuidad de su(s) representado(s)',
                'email_from': rec._enroll_addr('from'),
                'email_to': email,
                'reply_to': rec._enroll_addr('reply_to'),
                'body_html': rec._build_blast_email_html(),
                'state': 'outgoing',
            }
            # CC the admissions inbox only if configured (enrollment.blast_cc).
            # Set the param to '' to drop the CC and avoid support-queue congestion
            # from a mass blast — the single biggest source of soporte@ overload.
            blast_cc = rec._enroll_addr('blast_cc')
            if blast_cc:
                blast_vals['email_cc'] = blast_cc
            self.env['mail.mail'].sudo().create(blast_vals)
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
        base_report = self.env['ir.config_parameter'].sudo().get_param(
            'enrollment.report_url', REPORT_URL)
        report_url = '%s?j=%s' % (base_report, quote(journey_url or '', safe=''))
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
            soporte=self._enroll_addr('contact'),
        )
        return _email_wrapper(
            header_title='ENCUESTA DE CONTINUIDAD PERÍODO ACADÉMICO 2026-2027',
            header_subtitle='Proceso virtual asistido — U.E. Instituto Privado Andrés Bello',
            header_color='#1a2c5b',
            body_html=body,
            contact_email=self._enroll_addr('contact'),
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
            # Auto-create the egreso expediente first so the internal email's
            # "Ver expediente de egreso →" button deep-links to the real record.
            self._ensure_withdrawal()
            subject_internal = '[S0 No Continúa] Familia %s' % self.partner_id.name
            subject_customer = 'Hemos recibido su respuesta — Inscripción 2026-2027'
            internal_html = self._build_declined_notification_html(audience='internal')
            customer_html = self._build_declined_notification_html(audience='customer')
            internal_cc = INTERNAL_S0_CC

        Mail = self.env['mail.mail'].sudo()
        # 1) Internal staff copy — pagos@ (+ admissions/finance CC on confirm)
        internal_vals = {
            'subject': subject_internal,
            'email_from': self._enroll_addr('from'),
            'email_to': self._enroll_addr('internal'),
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
                'email_from': self._enroll_addr('from'),
                'email_to': partner_email,
                'reply_to': self._enroll_addr('reply_to'),
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
            contact_email=self._enroll_addr('contact'),
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
            cta = _cta_button(self._withdrawal_url(),
                              'Ver expediente de egreso en Odoo →', '#e67e22')

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
            contact_email=self._enroll_addr('contact'),
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
            '— Si tiene dudas escríbanos a %s.' % (names, journey_url,
                                                   self._enroll_addr('contact'))
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

    # ------------------------------------------------------------------
    # Phase 1b — Akdemia student import (live fetch → snapshot)
    # ------------------------------------------------------------------
    @api.model
    def _akdemia_fetch_students(self):
        """Live paginated pull from the Akdemia REST API. Returns the list of
        student entries. Raises UserError on missing key / network / partial
        data. Mirrors scripts/akdemia_api_sync.fetch_students()."""
        icp = self.env['ir.config_parameter'].sudo()
        api_key = (icp.get_param('akdemia.api_key') or '').strip()
        if not api_key:
            raise UserError(
                'Falta configurar el parámetro del sistema "akdemia.api_key". '
                'Solicite la clave de la API de Akdemia y regístrela en Ajustes Técnicos.')
        base_url = (icp.get_param('akdemia.base_url')
                    or 'https://api-staging.akdemia.com').rstrip('/')
        try:
            per_page = int(icp.get_param('akdemia.per_page') or '200')
        except (TypeError, ValueError):
            per_page = 200
        try:
            min_students = int(icp.get_param('akdemia.min_students') or '200')
        except (TypeError, ValueError):
            min_students = 200

        import requests as _req
        session = _req.Session()
        session.headers['Authorization'] = 'Bearer %s' % api_key
        entries, page = [], 1
        try:
            while True:
                resp = session.get(
                    '%s/api/ext/v1/students' % base_url,
                    params={'per_page': per_page, 'page': page},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                batch = data.get('data') or []
                entries.extend(batch)
                meta = data.get('meta') or {}
                total_pages = meta.get('total_pages')
                # Drive the loop off the LOCAL counter + returned batch, never the
                # server-echoed meta.page (which, if the server ignores `page`,
                # could pin to 1 and loop forever). A short final batch or a
                # reached total_pages ends it; a hard cap is the last-resort stop.
                if not batch or len(batch) < per_page or (total_pages and page >= total_pages):
                    break
                if page >= 200:
                    break
                page += 1
        except Exception as exc:  # noqa: BLE001 — surface any transport/JSON error to staff
            _logger.warning('Akdemia fetch failed: %s', exc)
            raise UserError('No se pudo conectar con Akdemia: %s' % exc)

        if len(entries) < min_students:
            raise UserError(
                'Akdemia devolvió solo %d estudiantes (mínimo esperado %d). '
                'Datos parciales detectados — importación cancelada para proteger '
                'los expedientes.' % (len(entries), min_students))
        return entries

    @api.model
    def _akdemia_index_by_guardian(self, entries):
        """Build {normalized_guardian_cedula: [{name, cedula, grade, section}, ...]}
        from raw Akdemia entries. A student is indexed under every guardian's
        cédula so parent 2/3 also match."""
        index = {}
        for entry in entries:
            s = entry.get('student') or {}
            student = {
                'name': ('%s %s' % (_s(s.get('first_name')),
                                    _s(s.get('last_name')))).strip(),
                'cedula': _s(s.get('unique_id')),
                'grade': _s(s.get('course_name')),
                'section': _s(s.get('batch_name')),
            }
            if not student['name']:
                continue
            for g in entry.get('guardians', []) or []:
                key = _normalize_cedula(g.get('unique_id'))
                if not key:
                    continue
                bucket = index.setdefault(key, [])
                if not any(x['cedula'] == student['cedula']
                           and x['name'] == student['name'] for x in bucket):
                    bucket.append(student)
        return index

    @api.model
    def _akdemia_student_index(self, use_cache=False):
        """Return the guardian→students index. With use_cache, read the
        daily-cron-published ir.config_parameter 'akdemia.students_json' (≤24h
        stale, no API call); otherwise do a live fetch. Falls back to live on a
        missing/corrupt cache."""
        if use_cache:
            icp = self.env['ir.config_parameter'].sudo()
            cached = icp.get_param('akdemia.students_json')
            if cached:
                try:
                    parsed = json.loads(cached)
                except (ValueError, TypeError):
                    parsed = None
                    _logger.warning(
                        'akdemia.students_json is not valid JSON — '
                        'falling back to live fetch')
                if parsed is not None:
                    # Sanity floor: a degenerate/stale cache (empty or far fewer
                    # guardians than expected) silently degrades every import, so
                    # fall back to a live fetch rather than trust it.
                    try:
                        floor = int(icp.get_param('akdemia.min_cache_guardians', '50'))
                    except (TypeError, ValueError):
                        floor = 50
                    if isinstance(parsed, dict) and len(parsed) >= floor:
                        return parsed
                    _logger.warning(
                        'akdemia.students_json has %s guardians (< floor %s) — '
                        'falling back to live fetch',
                        len(parsed) if isinstance(parsed, dict) else 'invalid', floor)
        return self._akdemia_index_by_guardian(self._akdemia_fetch_students())

    def action_import_students(self):
        """Staff button. Live-fetch from Akdemia, match partner.vat → guardian
        cédula, and write/refresh student_ids. Idempotent; preserves staff-edited
        lines and never touches UEIPAB-side fields (insurance_policy /
        institutional_email). Pass context use_cache=True to read the daily cache
        instead of calling the API live."""
        use_cache = bool(self.env.context.get('use_cache'))
        index = self._akdemia_student_index(use_cache=use_cache)
        Student = self.env['enrollment.journey.student']
        is_batch = len(self) > 1
        last = (0, 0, 0, 0)
        errors = []
        for rec in self:
            vat = _normalize_cedula(rec.partner_id.vat)
            if not vat:
                msg = ('El representante "%s" no tiene cédula (campo NIF/VAT) '
                       'registrada. Asígnela antes de importar estudiantes.'
                       % (rec.partner_id.name or '—'))
                if not is_batch:
                    raise UserError(msg)
                errors.append(msg)
                continue
            # Isolate each record so one failure can't roll back the others' work.
            try:
                with self.env.cr.savepoint():
                    last = rec._import_students_one(index, Student)
            except Exception as exc:  # noqa: BLE001
                if not is_batch:
                    raise
                _logger.warning('Akdemia import failed for journey %s: %s', rec.id, exc)
                errors.append('%s: %s' % (rec.partner_id.name or rec.id, exc))

        if not is_batch:
            created, updated, unchanged, total = last
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {
                    'title': 'Importación Akdemia',
                    'message': '%d nuevos · %d actualizados · %d sin cambios'
                               % (created, updated, unchanged),
                    'type': 'success' if total else 'warning',
                    'sticky': False,
                },
            }
        body = 'Importación completada para %d expediente(s).' % (len(self) - len(errors))
        if errors:
            body += ' %d con problemas: %s' % (len(errors), ' | '.join(errors[:5]))
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': 'Importación Akdemia (lote)',
                'message': body,
                'type': 'warning' if errors else 'success',
                'sticky': bool(errors),
            },
        }

    def _import_students_one(self, index, Student):
        """Import one journey's students from the prebuilt guardian index.
        Idempotent; preserves staff-edited lines + UEIPAB-side fields. Returns
        (created, updated, unchanged, total)."""
        self.ensure_one()
        vat = _normalize_cedula(self.partner_id.vat)
        ak_students = index.get(vat, [])
        if not ak_students:
            self.message_post(
                body='📥 Importación Akdemia: no se encontraron estudiantes para '
                     'la cédula %s. Verifique que el representante esté registrado '
                     'en Akdemia como acudiente.' % vat,
                message_type='comment', subtype_xmlid='mail.mt_note')
            return (0, 0, 0, 0)

        # Key by cédula, falling back to name for blank-cédula students, so they
        # match across re-syncs instead of being re-created every run.
        existing = {_line_key(line.cedula, line.name): line for line in self.student_ids}

        created = updated = unchanged = 0
        seen = set()
        for st in ak_students:
            key = _line_key(st['cedula'], st['name'])
            seen.add(key)
            line = existing.get(key)
            if not line:
                Student.create({
                    'journey_id': self.id,
                    'name': st['name'],
                    'cedula': st['cedula'],
                    'grade': st['grade'],
                    'source': 'akdemia',
                    'staff_edited': False,
                })
                created += 1
            elif line.staff_edited:
                if (line.name or '') != st['name'] or (line.grade or '') != st['grade']:
                    self.message_post(
                        body='⚠️ Akdemia difiere de una línea editada manualmente '
                             '(%s): Akdemia indica nombre="%s", grado="%s". '
                             'No se sobrescribió — revise manualmente.'
                             % (line.name, st['name'], st['grade']),
                        message_type='comment', subtype_xmlid='mail.mt_note')
                unchanged += 1
            else:
                changes = {}
                if (line.name or '') != st['name']:
                    changes['name'] = st['name']
                if (line.grade or '') != st['grade']:
                    changes['grade'] = st['grade']
                if changes:
                    changes['source'] = 'akdemia'
                    # system refresh — bypass the staff_edited write-guard
                    line.with_context(akdemia_sync=True).write(changes)
                    updated += 1
                else:
                    unchanged += 1

        for k, line in existing.items():
            if k not in seen and line.source == 'akdemia':
                self.message_post(
                    body='ℹ️ El estudiante %s (cédula %s) ya no aparece en Akdemia '
                         'para este representante. Revise si corresponde retirarlo '
                         'del expediente.' % (line.name, line.cedula or '—'),
                    message_type='comment', subtype_xmlid='mail.mt_note')

        self.message_post(
            body='📥 %d estudiantes sincronizados desde Akdemia '
                 '(%d nuevos · %d actualizados · %d sin cambios).'
                 % (len(ak_students), created, updated, unchanged),
            message_type='comment', subtype_xmlid='mail.mt_note')
        return (created, updated, unchanged, len(ak_students))

    def _akdemia_import_diff(self, index):
        """Read-only: compute what action_import_students WOULD change for this
        journey, without writing. Returns a dict {vat, found, new, updates,
        conflicts, missing, unchanged}."""
        self.ensure_one()
        vat = _normalize_cedula(self.partner_id.vat)
        out = {'vat': vat, 'found': 0, 'new': [], 'updates': [],
               'conflicts': [], 'missing': [], 'unchanged': 0, 'error': None}
        if not vat:
            out['error'] = 'El representante no tiene cédula (NIF/VAT) registrada.'
            return out
        ak = index.get(vat, [])
        out['found'] = len(ak)
        existing = {_line_key(l.cedula, l.name): l for l in self.student_ids}
        seen = set()
        for st in ak:
            key = _line_key(st['cedula'], st['name'])
            seen.add(key)
            line = existing.get(key)
            differs = line and ((line.name or '') != st['name']
                                or (line.grade or '') != st['grade'])
            if not line:
                out['new'].append(st)
            elif line.staff_edited:
                out['conflicts'].append((line, st)) if differs else None
                out['unchanged'] += 1 if not differs else 0
            elif differs:
                out['updates'].append((line, st))
            else:
                out['unchanged'] += 1
        for key, line in existing.items():
            if key not in seen and line.source == 'akdemia':
                out['missing'].append(line)
        return out

    def action_preview_import(self):
        """Compute a read-only diff vs Akdemia and open the confirmation wizard
        showing exactly what will change before anything is written."""
        self.ensure_one()
        use_cache = bool(self.env.context.get('use_cache'))
        d = self._akdemia_import_diff(self._akdemia_student_index(use_cache=use_cache))

        def _rows(items, fmt):
            return ''.join('<li>%s</li>' % fmt(i) for i in items) or '<li><i>—</i></li>'

        if d['error']:
            body = '<p style="color:#c0392b;">⚠️ %s</p>' % d['error']
        else:
            body = (
                '<p><b>%d</b> estudiante(s) encontrados en Akdemia para la cédula '
                '<code>%s</code>.</p>'
                '<p>🟢 <b>Nuevos (%d):</b></p><ul>%s</ul>'
                '<p>🔵 <b>Actualizar (%d):</b></p><ul>%s</ul>'
                '<p>🟠 <b>Conflictos — editados a mano, NO se tocan (%d):</b></p><ul>%s</ul>'
                '<p>⚪ <b>Sin cambios:</b> %d</p>'
                '<p>🔴 <b>Ya no en Akdemia (%d):</b></p><ul>%s</ul>'
                % (
                    d['found'], d['vat'],
                    len(d['new']), _rows(d['new'], lambda s: '%s — %s' % (s['name'], s['grade'] or '?')),
                    len(d['updates']), _rows(d['updates'], lambda u: '%s: «%s → %s» / grado «%s → %s»' % (
                        u[0].name, u[0].name, u[1]['name'], u[0].grade or '—', u[1]['grade'] or '—')),
                    len(d['conflicts']), _rows(d['conflicts'], lambda c: '%s (Akdemia: %s / %s)' % (
                        c[0].name, c[1]['name'], c[1]['grade'] or '—')),
                    d['unchanged'],
                    len(d['missing']), _rows(d['missing'], lambda l: '%s (%s)' % (l.name, l.cedula or '—')),
                ))

        wiz = self.env['enrollment.student.import.preview'].sudo().create({
            'journey_id': self.id,
            'use_cache': use_cache,
            'summary_html': body,
            'new_count': len(d['new']),
            'update_count': len(d['updates']),
            'conflict_count': len(d['conflicts']),
            'missing_count': len(d['missing']),
            'unchanged_count': d['unchanged'],
            'has_changes': bool(d['new'] or d['updates']),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vista previa — Importar estudiantes',
            'res_model': 'enrollment.student.import.preview',
            'res_id': wiz.id, 'view_mode': 'form', 'target': 'new',
        }


class EnrollmentJourneyStudent(models.Model):
    _name = 'enrollment.journey.student'
    _description = 'Enrollment Journey Student'

    journey_id = fields.Many2one('enrollment.journey', required=True, ondelete='cascade')
    name = fields.Char(string='Estudiante', required=True)
    cedula = fields.Char(string='Cédula/Cédula Escolar')
    grade = fields.Char(string='Grado/Año')
    institutional_email = fields.Char(string='Correo @ueipab')
    insurance_policy = fields.Char(string='Nº Póliza Seguro')

    # Phase 1b — provenance + edit guard for the Akdemia sync
    source = fields.Selection([('manual', 'Manual'), ('akdemia', 'Akdemia')],
                              default='manual', string='Origen')
    staff_edited = fields.Boolean(
        default=False, string='Editado por staff',
        help='Marca que un humano corrigió esta línea; una re-sincronización con '
             'Akdemia no sobrescribirá su nombre/grado.')

    def write(self, vals):
        # A human edit to the identity fields flags the line so a later Akdemia
        # re-sync won't clobber the correction. The sync itself passes
        # context akdemia_sync=True to bypass this.
        if not self.env.context.get('akdemia_sync') and (
                'name' in vals or 'grade' in vals or 'cedula' in vals):
            vals.setdefault('staff_edited', True)
        return super().write(vals)


class EnrollmentStudentImportPreview(models.TransientModel):
    _name = 'enrollment.student.import.preview'
    _description = 'Vista previa de importación de estudiantes (Akdemia)'

    journey_id = fields.Many2one('enrollment.journey', required=True, ondelete='cascade')
    use_cache = fields.Boolean(default=False)
    summary_html = fields.Html(readonly=True, string='Resumen de cambios')
    new_count = fields.Integer(readonly=True, string='Nuevos')
    update_count = fields.Integer(readonly=True, string='Actualizar')
    conflict_count = fields.Integer(readonly=True, string='Conflictos')
    missing_count = fields.Integer(readonly=True, string='Ausentes')
    unchanged_count = fields.Integer(readonly=True, string='Sin cambios')
    has_changes = fields.Boolean(readonly=True)

    def action_confirm(self):
        """Apply the import the preview just described."""
        self.ensure_one()
        return self.journey_id.with_context(
            use_cache=self.use_cache).action_import_students()


class EnrollmentQuoteVersion(models.Model):
    """Immutable audit log — one row per issued quotation version. Freezes the
    exact PDF (retained 'mensaje de datos') + SHA-256 + the Tier-2 acceptance
    evidence (IP / UA / UTC timestamp / T&C). Never edited by hand."""
    _name = 'enrollment.quote.version'
    _description = 'Versión de cotización (auditoría)'
    _order = 'version desc, id desc'

    journey_id = fields.Many2one(
        'enrollment.journey', required=True, ondelete='cascade', index=True)
    version = fields.Integer(string='Versión', required=True)
    order_id = fields.Many2one('sale.order', string='Cotización')
    currency_id = fields.Many2one('res.currency', string='Moneda')
    amount_total = fields.Monetary(string='Total', currency_field='currency_id')
    pdf_attachment_id = fields.Many2one(
        'ir.attachment', string='PDF congelado', ondelete='set null')
    pdf_sha256 = fields.Char(string='SHA-256', readonly=True)
    issued_date = fields.Datetime(string='Emitida', readonly=True)
    issued_by = fields.Many2one('res.users', string='Emitida por', readonly=True)
    state = fields.Selection([
        ('issued',     'Emitida'),
        ('superseded', 'Reemplazada'),
        ('accepted',   'Aceptada'),
        ('rejected',   'Rechazada'),
    ], default='issued', string='Estado', index=True)

    # Tier-2 acceptance evidence
    accept_ip = fields.Char(string='IP de aceptación', readonly=True)
    accept_user_agent = fields.Char(string='User-Agent', readonly=True)
    accept_timestamp_utc = fields.Datetime(string='Aceptada (UTC)', readonly=True)
    tyc_accepted = fields.Boolean(string='T&C aceptados', readonly=True)

    # Acceptance method — electronic (public Tier-2) vs presencial (wet signature, staff)
    accept_method = fields.Selection([
        ('electronic', 'Electrónica (en línea)'),
        ('presencial', 'Presencial (firma física)'),
    ], string='Modo de aceptación', default='electronic', readonly=True)
    accept_staff_user_id = fields.Many2one(
        'res.users', string='Aceptación atendida por', readonly=True)
    presencial_attested = fields.Boolean(
        string='Firma física certificada por personal', readonly=True)
    signed_pdf_attachment_id = fields.Many2one(
        'ir.attachment', string='Acuerdo firmado (escaneado)', ondelete='set null')

    # Revision-request evidence
    revision_reason = fields.Text(string='Motivo de revisión', readonly=True)
    revision_ip = fields.Char(string='IP de revisión', readonly=True)
    revision_timestamp_utc = fields.Datetime(string='Revisión (UTC)', readonly=True)


class EnrollmentPresencialDeclineWizard(models.TransientModel):
    """Capture the reason when staff records an in-person S0 decline."""
    _name = 'enrollment.presencial.decline.wizard'
    _description = 'Retiro presencial — motivo'

    journey_id = fields.Many2one('enrollment.journey', required=True, ondelete='cascade')
    reason = fields.Text('Motivo del retiro', required=True)

    def action_apply(self):
        self.ensure_one()
        j = self.journey_id
        if j.continuation_status != 'pending':
            raise UserError('La continuidad ya fue resuelta.')
        j.write({
            'continuation_status': 'declined',
            'decline_reason': (self.reason or '').strip()[:2000] or None,
            'decline_date': fields.Datetime.now(),
            'enrollment_mode': 'presencial',
            'assisted_by': j.assisted_by.id or self.env.uid,
        })
        j._send_response_notification('declined')
        j.message_post(
            body='✖️ Retiro (no continúa) registrado en sede por %s (modalidad presencial).'
                 % self.env.user.name,
            message_type='comment', subtype_xmlid='mail.mt_note')
        return {'type': 'ir.actions.act_window_close'}


class EnrollmentPresencialAcceptWizard(models.TransientModel):
    """Record a wet-signature acceptance of the sent quote, on the family's
    behalf, with a required staff attestation + optional scanned signed PDF."""
    _name = 'enrollment.presencial.accept.wizard'
    _description = 'Aceptación presencial de la cotización'

    journey_id = fields.Many2one('enrollment.journey', required=True, ondelete='cascade')
    attested = fields.Boolean(
        'Doy fe de que el representante firmó en físico el Acuerdo y sus Términos y Condiciones',
        required=True)
    signed_pdf = fields.Binary('Acuerdo firmado (escaneado, opcional)')
    signed_pdf_filename = fields.Char('Nombre del archivo')

    def action_apply(self):
        self.ensure_one()
        if not self.attested:
            raise UserError('Debe certificar que el representante firmó el Acuerdo en físico '
                            'antes de registrar la aceptación.')
        j = self.journey_id
        att_id = False
        if self.signed_pdf:
            att = self.env['ir.attachment'].create({
                'name': self.signed_pdf_filename or ('Acuerdo_firmado_%s.pdf' % (
                    j.order_id.name if j.order_id else j.id)),
                'type': 'binary',
                'datas': self.signed_pdf,
                'res_model': 'enrollment.journey',
                'res_id': j.id,
                'mimetype': 'application/pdf',
            })
            att_id = att.id
        ok = j._record_acceptance_presencial(
            staff_user_id=self.env.uid, attested=self.attested,
            signed_attachment_id=att_id)
        if not ok:
            raise UserError('No se pudo registrar la aceptación: la cotización no está en '
                            'estado "Enviada".')
        return {'type': 'ir.actions.act_window_close'}
