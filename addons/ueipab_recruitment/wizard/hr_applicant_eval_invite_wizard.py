import logging
from datetime import date

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

_LOGO_URL        = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
_RRHH_EMAIL      = 'recursoshumanos@ueipab.edu.ve'
_FROM_EMAIL      = 'soporte@ueipab.edu.ve'
_FROM_NAME       = 'Recursos Humanos - Colegio Andrés Bello'
_DEFAULT_ADDRESS = 'Calle 15 sur Nro 4 al lado de la Casa Nva Esparta frente al automercado 3F'

_MONTHS_ES = [
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]
_DAYS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def _fmt_date(d):
    if not d:
        return '—'
    day_name = _DAYS_ES[d.weekday()]
    return f"{day_name.capitalize()}, {d.day} de {_MONTHS_ES[d.month]} de {d.year}"


class HrApplicantEvalInviteWizard(models.TransientModel):
    _name = 'hr.applicant.eval.invite.wizard'
    _description = 'Enviar Invitación de Evaluación Presencial'

    applicant_id      = fields.Many2one('hr.applicant', required=True, readonly=True)
    partner_name      = fields.Char(related='applicant_id.partner_name', readonly=True, string='Candidato')
    job_name          = fields.Char(related='applicant_id.job_id.name',  readonly=True, string='Cargo')

    appointment_date  = fields.Date('Fecha de Evaluación', required=True)
    appointment_time  = fields.Char('Hora', default='9:00 AM', required=True)
    address           = fields.Char('Dirección', default=_DEFAULT_ADDRESS, required=True)
    duration_minutes  = fields.Integer('Duración (min)', default=30)

    candidate_email   = fields.Char('Email del Candidato')
    candidate_phone   = fields.Char('Teléfono / WhatsApp')
    has_phone         = fields.Boolean(compute='_compute_has_phone')
    send_whatsapp     = fields.Boolean('Enviar también por WhatsApp / Glenda')

    @api.depends('candidate_phone')
    def _compute_has_phone(self):
        for rec in self:
            rec.has_phone = bool((rec.candidate_phone or '').strip())

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        app_id = self.env.context.get('default_applicant_id')
        if app_id:
            app = self.env['hr.applicant'].browse(app_id)
            res['candidate_email'] = app.email_from or ''
            phone = app.partner_mobile or app.partner_phone or ''
            res['candidate_phone'] = phone
            res['send_whatsapp'] = bool(phone)
        return res

    # ── Send ─────────────────────────────────────────────────────────────────

    def action_send(self):
        self.ensure_one()
        sent_wa = False

        if self.send_whatsapp and self.candidate_phone:
            sent_wa = self._send_whatsapp()

        if self.candidate_email:
            self._send_email(sent_wa)

        # Update applicant state
        self.applicant_id.sudo().write({
            'ueipab_evaluation_mode': 'in_person',
            'ueipab_eval_state':      'eval_invited',
        })

        channels = []
        if self.candidate_email:
            channels.append('email')
        if sent_wa:
            channels.append('WhatsApp')
        label = ' + '.join(channels) if channels else 'ningún canal'

        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   '✅ Invitación enviada',
                'message': f"Invitación enviada por {label} a {self.partner_name}.",
                'type':    'success',
                'sticky':  False,
            },
        }

    # ── Email ─────────────────────────────────────────────────────────────────

    def _send_email(self, with_wa: bool):
        html = self._build_email_html(with_wa)
        subject = (
            f"Invitación a Evaluación Presencial — "
            f"{self.job_name or 'UEIPAB'} | UEIPAB"
        )
        mail = self.env['mail.mail'].sudo().create({
            'subject':        subject,
            'email_to':       self.candidate_email,
            'email_from':     f'"{_FROM_NAME}" <{_FROM_EMAIL}>',
            'reply_to':       _RRHH_EMAIL,
            'email_cc':       _RRHH_EMAIL,
            'body_html':      html,
            'state':          'outgoing',
        })
        _logger.info(
            "Eval invite email queued: mail.mail id=%s to=%s applicant=%s",
            mail.id, self.candidate_email, self.applicant_id.id,
        )

    def _build_email_html(self, with_wa: bool) -> str:
        name        = (self.partner_name or '—').upper()
        first_name  = name.split()[0] if name != '—' else 'Candidato/a'
        job         = self.job_name or '—'
        date_str    = _fmt_date(self.appointment_date)
        time_str    = self.appointment_time or '—'
        address     = self.address or '—'
        duration    = self.duration_minutes or 30

        mailto_subj = f"Confirmo asistencia a evaluación — {name}"
        mailto_body = (
            f"Confirmo mi asistencia a la evaluación técnica presencial "
            f"del {date_str} a las {time_str}."
        )
        mailto_link = (
            f"mailto:{_RRHH_EMAIL}"
            f"?subject={mailto_subj.replace(' ', '%20')}"
            f"&body={mailto_body.replace(' ', '%20')}"
        )

        if with_wa:
            cta_block = f"""
<p style="text-align:center;font-size:13px;color:#555;
           background:#e8f5e9;border-radius:6px;padding:12px 16px;margin:16px 0;">
  💬 Le enviamos un mensaje de <strong>WhatsApp</strong> para confirmar su asistencia.
  Responda al mensaje de Glenda con <strong>"Sí"</strong> para quedar confirmado/a.
</p>"""
        else:
            cta_block = f"""
<p style="text-align:center;margin:20px 0 6px;">
  <a href="{mailto_link}"
     style="display:inline-block;background:#1a73e8;color:#ffffff !important;
            padding:12px 32px;border-radius:6px;text-decoration:none;
            font-size:14px;font-weight:700;font-family:Arial,sans-serif;">
    ✅ Confirmar Asistencia
  </a>
</p>
<p style="text-align:center;font-size:11px;color:#aaa;margin:4px 0 16px;">
  Haga clic para enviarnos su confirmación por correo
</p>"""

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#f0f4f8;padding:20px 0;">
<tr><td align="center">
<div style="max-width:580px;margin:0 auto;background:#ffffff;
            border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);
            overflow:hidden;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);
              padding:32px 24px;text-align:center;color:#ffffff;">
    <img src="{_LOGO_URL}" width="64" height="64"
         style="border-radius:50%;border:3px solid rgba(255,255,255,.3);
                display:block;margin:0 auto 12px;object-fit:cover;">
    <h1 style="margin:0 0 4px;font-size:20px;font-weight:700;">
      📅 Evaluación Técnica Presencial
    </h1>
    <p style="margin:0;font-size:13px;opacity:.85;">
      U.E.I.P.A.B. — Recursos Humanos
    </p>
  </div>

  <!-- Body -->
  <div style="padding:28px 32px;">

    <!-- Badge -->
    <div style="text-align:center;margin-bottom:20px;">
      <span style="display:inline-block;background:#e8f0fe;color:#1a73e8;
                   border:1px solid #c5d8fd;border-radius:12px;padding:5px 16px;
                   font-size:12px;font-weight:600;">
        📋 Evaluación Programada
      </span>
    </div>

    <p style="margin:0 0 16px;font-size:14px;color:#333;">
      Estimado/a <strong>{first_name}</strong>,
    </p>
    <p style="margin:0 0 20px;font-size:14px;color:#555;line-height:1.6;">
      Hemos revisado su perfil y nos complace invitarle a participar en la
      <strong>evaluación técnica presencial</strong> para el cargo indicado a continuación.
    </p>

    <!-- Details table -->
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;margin-bottom:20px;font-size:14px;">
      <tr>
        <td style="padding:10px 12px;background:#f8f9fa;border-radius:6px 6px 0 0;
                   color:#555;width:40%;font-weight:600;">👤 Candidato</td>
        <td style="padding:10px 12px;background:#f8f9fa;border-radius:6px 6px 0 0;
                   color:#222;">{name}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;color:#555;font-weight:600;">💼 Cargo</td>
        <td style="padding:10px 12px;color:#222;">{job}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;background:#f8f9fa;color:#555;font-weight:600;">📅 Fecha</td>
        <td style="padding:10px 12px;background:#f8f9fa;color:#222;font-weight:700;">{date_str}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;color:#555;font-weight:600;">⏰ Hora</td>
        <td style="padding:10px 12px;color:#222;font-weight:700;">{time_str}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;background:#f8f9fa;color:#555;font-weight:600;">📍 Dirección</td>
        <td style="padding:10px 12px;background:#f8f9fa;color:#222;">{address}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;color:#555;font-weight:600;">⏱️ Duración</td>
        <td style="padding:10px 12px;color:#222;">{duration} minutos</td>
      </tr>
    </table>

    <!-- Important note -->
    <div style="background:#fff8e1;border-left:4px solid #f0ad4e;border-radius:4px;
                padding:14px 16px;margin-bottom:20px;">
      <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#856404;">
        📌 Recuerde traer:
      </p>
      <ul style="margin:0;padding-left:18px;font-size:13px;color:#555;line-height:1.8;">
        <li>Cédula de identidad <strong>original</strong></li>
        <li>Presentarse <strong>5 minutos antes</strong> de la hora indicada</li>
      </ul>
    </div>

    <!-- Reschedule note -->
    <div style="background:#e8f0fe;border-left:4px solid #1a73e8;border-radius:4px;
                padding:12px 16px;margin-bottom:20px;">
      <p style="margin:0;font-size:13px;color:#1a3c6e;">
        📅 <strong>Nota:</strong> Si necesita cambiar su horario, por favor responda
        a este correo electrónico solicitando el cambio.
      </p>
    </div>

    {cta_block}

  </div>

  <!-- Footer -->
  <div style="background:#f8f9fa;padding:14px 24px;text-align:center;
              border-top:1px solid #eee;">
    <p style="margin:0;font-size:11px;color:#aaa;">
      Mensaje de U.E.I.P.A.B. — Consultas: {_RRHH_EMAIL}
    </p>
  </div>

</div>
</td></tr>
</table>
</body>
</html>"""

    # ── WhatsApp ──────────────────────────────────────────────────────────────

    def _send_whatsapp(self) -> bool:
        name       = self.partner_name or 'Candidato/a'
        first_name = name.split()[0]
        job        = self.job_name or 'el cargo'
        date_str   = _fmt_date(self.appointment_date)
        time_str   = self.appointment_time or '—'
        address    = self.address or '—'
        duration   = self.duration_minutes or 30
        phone      = self.candidate_phone.strip()

        msg = (
            f"Hola {first_name}, soy Glenda, asistente de UEIPAB 👋\n\n"
            f"Ha sido seleccionado/a para una evaluación técnica presencial "
            f"para el cargo de *{job}*.\n\n"
            f"📅 *Fecha:* {date_str}\n"
            f"⏰ *Hora:* {time_str}\n"
            f"📍 *Lugar:* {address}\n"
            f"⏱️ *Duración:* {duration} minutos\n\n"
            f"📌 *Importante:* traiga su cédula de identidad original y "
            f"preséntese 5 minutos antes.\n\n"
            f"¿Confirma su asistencia? Responda *Sí* para confirmar "
            f"o escríbanos si necesita reprogramar la fecha."
        )

        try:
            ICP = self.env['ir.config_parameter'].sudo()
            dry_run = ICP.get_param('ai_agent.dry_run', 'True').lower() == 'true'
            if dry_run:
                _logger.info(
                    "WA invite DRY RUN — would send to %s: %s", phone, msg[:80]
                )
                return False

            wa = self.env['ai.agent.whatsapp.service']
            result = wa.send_message(phone_number=phone, message=msg)
            if result:
                _logger.info(
                    "WA eval invite sent: phone=%s applicant=%s",
                    phone, self.applicant_id.id,
                )
                return True
        except Exception:
            _logger.exception(
                "WA eval invite failed for applicant=%s phone=%s",
                self.applicant_id.id, phone,
            )
        return False
