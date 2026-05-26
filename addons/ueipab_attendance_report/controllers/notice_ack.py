import datetime
import logging
import re

import requests as _requests

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

_WA_RE = re.compile(r'^\+?[0-9\s\-]{7,20}$')

# Notice keys that require the WA-number confirmation form instead of
# an immediate one-click ACK.
_WA_FORM_KEYS = {'glenda_calibracion_v1'}

# Notice keys that send a confirmation email to the employee on ACK.
_EMAIL_CONFIRM_KEYS = {
    'ari_guide_2026_v1': {
        'subject':    '✅ Confirmaste haber leído la Guía AR-I ISLR | Colegio Andrés Bello',
        'portal_url': 'https://odoo.ueipab.edu.ve/my/ari',
        'label':      'Guía de Usuario — Portal AR-I ISLR',
    },
}


class NoticeAckController(http.Controller):

    # ── Generic one-click ACK (existing behaviour) ────────────────────────────

    @http.route('/notice-ack/<string:token>', type='http', auth='public', website=False)
    def notice_ack(self, token, **kwargs):
        Ack = request.env['hr.notice.acknowledgment'].sudo()
        ack = Ack.search([('token', '=', token)], limit=1)

        if not ack:
            return self._respond(self._page_invalid())

        # Delegate to WA-form flow for calibration notices
        if ack.notice_key in _WA_FORM_KEYS:
            return self._glenda_form_get(ack)

        if ack.state == 'acknowledged':
            return self._respond(self._page_already_done(ack))

        ip = self._client_ip()
        ack.write({'state': 'acknowledged', 'ack_date': datetime.datetime.now(), 'ack_ip': ip})
        if ack.notice_key in _EMAIL_CONFIRM_KEYS:
            self._send_ack_confirmation_email(ack)
        return self._respond(self._page_success(ack))

    # ── Glenda calibration: GET (show form) ───────────────────────────────────

    def _glenda_form_get(self, ack):
        if ack.state == 'acknowledged':
            return self._respond(self._page_glenda_already_done(ack))
        # Pre-fill with employee's mobile or work phone
        emp = ack.employee_id
        prefill = emp.mobile_phone or emp.work_phone or ''
        return self._respond(self._page_glenda_form(ack, prefill, error=None))

    # ── Glenda calibration: POST (save WA + ACK) ──────────────────────────────

    @http.route('/glenda-calibracion/<string:token>', type='http',
                auth='public', website=False, methods=['POST'], csrf=False)
    def glenda_calibracion_post(self, token, **kwargs):
        Ack = request.env['hr.notice.acknowledgment'].sudo()
        ack = Ack.search([('token', '=', token)], limit=1)

        if not ack:
            return self._respond(self._page_invalid())

        if ack.state == 'acknowledged':
            return self._respond(self._page_glenda_already_done(ack))

        wa_raw = (kwargs.get('wa_number') or '').strip()

        # Basic validation
        if not wa_raw or not _WA_RE.match(wa_raw):
            prefill = ack.employee_id.mobile_phone or ''
            return self._respond(
                self._page_glenda_form(ack, wa_raw or prefill,
                                       error='Por favor ingresa un número de WhatsApp válido.')
            )

        # Normalise: strip spaces/dashes, ensure +58 prefix for VE numbers
        wa_clean = re.sub(r'[\s\-]', '', wa_raw)
        if wa_clean.startswith('04') and len(wa_clean) == 11:
            wa_clean = '+58' + wa_clean[1:]
        elif wa_clean.startswith('04') and len(wa_clean) > 7:
            wa_clean = '+58' + wa_clean[1:]

        ip  = self._client_ip()
        emp = ack.employee_id
        old_mobile = (emp.mobile_phone or '').strip()

        ack.write({
            'state':     'acknowledged',
            'ack_date':  datetime.datetime.now(),
            'ack_ip':    ip,
            'wa_number': wa_clean,
        })

        # Compare with existing mobile — update if new or different
        number_changed = bool(old_mobile and old_mobile != wa_clean)
        if not old_mobile or number_changed:
            emp.write({'mobile_phone': wa_clean})

        # Determine ACK status for HR notification
        if number_changed:
            ack_status = 'updated'    # had a number, it changed
        elif not old_mobile:
            ack_status = 'registered' # no number on file, now saved
        else:
            ack_status = 'confirmed'  # number matched exactly

        # Always notify HR of every ACK (unified email covers all scenarios)
        self._notify_hr_ack_confirmed(emp, wa_clean, ack_status, old_mobile)

        # Send WA welcome message to the confirmed number
        self._send_glenda_wa_welcome(wa_clean, emp.name)

        return self._respond(self._page_glenda_success(ack, wa_clean, number_changed))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _client_ip(self):
        return (
            request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '')
            .split(',')[0].strip()
            or request.httprequest.remote_addr
        )

    def _respond(self, html):
        return request.make_response(
            html, headers=[('Content-Type', 'text/html; charset=utf-8')]
        )

    # ── Employee ACK confirmation email ──────────────────────────────────────

    def _send_ack_confirmation_email(self, ack):
        """Send a gentle confirmation receipt to the employee + CC recursoshumanos@.

        Called for notice keys listed in _EMAIL_CONFIRM_KEYS immediately after
        the ACK is written. Best-effort — never raises.
        """
        try:
            cfg        = _EMAIL_CONFIRM_KEYS[ack.notice_key]
            emp        = ack.employee_id
            to_email   = emp.work_email or emp.user_id.email or ''
            if not to_email:
                _logger.warning(
                    "_send_ack_confirmation_email: no email for employee %s (%s)",
                    emp.name, ack.notice_key,
                )
                return

            dt         = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
            first_name = emp.name.split()[0].capitalize()
            portal_url = cfg['portal_url']
            label      = cfg['label']

            body = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0f4f8;">
<tr><td align="center" style="padding:28px 12px;">
<table width="540" cellpadding="0" cellspacing="0" border="0"
       style="max-width:540px;width:100%;border-radius:14px;overflow:hidden;
              box-shadow:0 6px 32px rgba(0,0,0,0.12);">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#052e16 0%,#14532d 100%);
               padding:32px 36px 24px;text-align:center;">
      <div style="width:64px;height:64px;background:rgba(255,255,255,0.12);
                  border-radius:50%;line-height:64px;font-size:32px;
                  margin:0 auto 14px;border:2px solid #4ade80;">
        ✅
      </div>
      <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#86efac;
                letter-spacing:2px;text-transform:uppercase;">Recursos Humanos</p>
      <h1 style="margin:0 0 6px;font-size:22px;font-weight:800;color:#ffffff;">
        Confirmación Registrada
      </h1>
      <p style="margin:0;font-size:13px;color:#bbf7d0;">{label}</p>
    </td>
  </tr>

  <!-- BODY -->
  <tr>
    <td style="background:#ffffff;padding:30px 36px 24px;">
      <p style="margin:0 0 18px;font-size:15px;color:#374151;line-height:1.7;">
        Hola <strong>{first_name}</strong>, gracias por tomarte el tiempo de leer
        la guía. Tu confirmación ha quedado <strong>registrada exitosamente</strong>
        en el sistema.
      </p>

      <!-- Receipt card -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;
                    margin-bottom:22px;">
        <tr>
          <td style="padding:14px 20px;border-bottom:1px solid #bbf7d0;">
            <p style="margin:0 0 2px;font-size:10px;font-weight:700;color:#64748b;
                      text-transform:uppercase;letter-spacing:1px;">Empleado</p>
            <p style="margin:0;font-size:14px;font-weight:700;color:#0a1628;">
              {emp.name}
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:14px 20px;border-bottom:1px solid #bbf7d0;">
            <p style="margin:0 0 2px;font-size:10px;font-weight:700;color:#64748b;
                      text-transform:uppercase;letter-spacing:1px;">Documento confirmado</p>
            <p style="margin:0;font-size:13px;color:#374151;">{label}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:14px 20px;border-bottom:1px solid #bbf7d0;">
            <p style="margin:0 0 2px;font-size:10px;font-weight:700;color:#64748b;
                      text-transform:uppercase;letter-spacing:1px;">Estado</p>
            <span style="display:inline-block;background:#dcfce7;color:#15803d;
                         font-size:12px;font-weight:700;padding:3px 12px;
                         border-radius:20px;">✅ Leído y comprendido</span>
          </td>
        </tr>
        <tr>
          <td style="padding:14px 20px;">
            <p style="margin:0 0 2px;font-size:10px;font-weight:700;color:#64748b;
                      text-transform:uppercase;letter-spacing:1px;">Fecha de confirmación</p>
            <p style="margin:0;font-size:13px;color:#374151;">{dt}</p>
          </td>
        </tr>
      </table>

      <!-- Next step -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="margin-bottom:22px;">
        <tr>
          <td style="background:#fef3c7;border-left:4px solid #f59e0b;
                     border-radius:0 8px 8px 0;padding:14px 18px;">
            <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#78350f;">
              📋 Próximo paso
            </p>
            <p style="margin:0;font-size:12px;color:#78350f;line-height:1.6;">
              Accede al portal y completa tu declaración AR-I para el año fiscal en curso.
              Recuerda que la fecha límite de la declaración inicial es el
              <strong>15 de enero</strong> de cada año.
            </p>
          </td>
        </tr>
      </table>

      <!-- CTA -->
      <div style="text-align:center;">
        <a href="{portal_url}"
           style="display:inline-block;background:linear-gradient(135deg,#0a1628,#1a3a6b);
                  color:#C8A951;text-decoration:none;font-size:14px;font-weight:700;
                  padding:13px 40px;border-radius:50px;letter-spacing:0.5px;">
          📋 Ir al Portal AR-I
        </a>
      </div>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#0a1628;padding:18px 36px;text-align:center;">
      <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#C8A951;">
        Recursos Humanos · Colegio Andrés Bello
      </p>
      <p style="margin:0;font-size:11px;color:#4b6080;">
        <a href="mailto:recursoshumanos@ueipab.edu.ve"
           style="color:#4b6080;text-decoration:none;">
          recursoshumanos@ueipab.edu.ve
        </a>
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""

            request.env['mail.mail'].sudo().create({
                'subject':    cfg['subject'],
                'email_from': 'Recursos Humanos — Colegio Andrés Bello <recursoshumanos@ueipab.edu.ve>',
                'email_to':   to_email,
                'email_cc':   'recursoshumanos@ueipab.edu.ve',
                'body_html':  body,
                'state':      'outgoing',
            }).send()
            _logger.info(
                "_send_ack_confirmation_email: sent to %s (employee %s, key %s)",
                to_email, emp.name, ack.notice_key,
            )
        except Exception as e:
            _logger.warning(
                "_send_ack_confirmation_email: failed for employee %s — %s",
                ack.employee_id.name if ack.employee_id else '?', e,
            )

    # ── Base page shell ───────────────────────────────────────────────────────

    def _base_page(self, title, content, extra_style=''):
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} — UEIPAB</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; background: #f0f4fa;
            margin: 0; padding: 40px 16px; }}
    .card {{ max-width: 520px; margin: 0 auto; background: white;
             border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.12);
             overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #1a2c5b 0%, #2471a3 100%);
               color: white; padding: 28px 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 17px; font-weight: bold; }}
    .header p  {{ margin: 6px 0 0; font-size: 13px; opacity: 0.85; }}
    .header .badge {{ display: inline-block; margin-top: 12px;
                      background: rgba(212,175,55,0.2); border: 1px solid #d4af37;
                      color: #d4af37; font-size: 11px; letter-spacing: 2px;
                      padding: 4px 14px; border-radius: 20px;
                      text-transform: uppercase; }}
    .body   {{ padding: 28px 24px; }}
    .footer {{ background: #f8f9fa; padding: 14px 24px; text-align: center;
               font-size: 11px; color: #aaa; border-top: 1px solid #e8e8e8; }}
    {extra_style}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>Instituto Privado Andr&eacute;s Bello, CA</h1>
      <p>Recursos Humanos</p>
      <span class="badge">Programa Glenda AI</span>
    </div>
    <div class="body">{content}</div>
    <div class="footer">Enlace personal e intransferible &mdash;
      recursoshumanos@ueipab.edu.ve</div>
  </div>
</body>
</html>"""

    # ── Glenda WA welcome message ─────────────────────────────────────────────

    def _send_glenda_wa_welcome(self, wa_number, emp_name):
        """Send a WhatsApp welcome message to the employee's confirmed number.

        Uses ir.config_parameter for WA credentials so this controller does
        not hard-depend on ueipab_ai_agent. Respects dry_run flag. Best-effort
        — never raises so it cannot break the ACK confirmation flow.
        """
        try:
            ICP = request.env['ir.config_parameter'].sudo()

            dry_run = ICP.get_param('ai_agent.dry_run', 'True').lower() == 'true'
            secret  = ICP.get_param('ai_agent.whatsapp_api_secret', '')
            account = ICP.get_param('ai_agent.whatsapp_account_id', '')
            base_url = ICP.get_param(
                'ai_agent.whatsapp_base_url',
                'https://whatsapp.massivamovil.com/api'
            ).rstrip('/')

            if not secret or not account:
                _logger.info(
                    "Glenda WA welcome: WA credentials not configured — skipping"
                )
                return

            today    = datetime.date.today()
            end_date = today + datetime.timedelta(days=60)
            today_s  = today.strftime('%d/%m/%Y')
            end_s    = end_date.strftime('%d/%m/%Y')

            first_name = emp_name.split()[0].capitalize()

            message = (
                f"¡Hola {first_name}! 🤖 Soy *Glenda*, la asistente virtual de "
                f"inteligencia artificial del *Instituto Andrés Bello*.\n\n"
                f"Tu participación en el *Programa de Calibración* ha sido confirmada. ✅\n\n"
                f"📋 *Detalles del programa:*\n"
                f"• Inicio: {today_s}\n"
                f"• Vigencia: 60 días\n"
                f"• Vencimiento: {end_s}\n\n"
                f"Durante este período, escríbeme semanalmente por WhatsApp. "
                f"Cada sesión documentada genera un bono equivalente a *1 día de tu salario base*.\n\n"
                f"¡Gracias por ser parte de esta iniciativa! 🎉\n"
                f"_Recursos Humanos — UEIPAB_"
            )

            if dry_run:
                _logger.info(
                    "Glenda WA welcome [DRY RUN]: would send to %s — %s",
                    wa_number, message[:80]
                )
                return

            resp = _requests.post(
                f"{base_url}/send/whatsapp",
                data={
                    'secret':    secret,
                    'account':   account,
                    'recipient': wa_number,
                    'type':      'text',
                    'message':   message,
                },
                timeout=15,
            )
            result = resp.json()
            if result.get('status') == 200:
                _logger.info(
                    "Glenda WA welcome sent to %s (msg_id=%s)",
                    wa_number, result.get('data', {}).get('id')
                )
            else:
                _logger.warning(
                    "Glenda WA welcome: API returned status %s for %s",
                    result.get('status'), wa_number
                )
        except Exception as e:
            _logger.warning("Glenda WA welcome: failed for %s — %s", wa_number, e)

    # ── Glenda form page ──────────────────────────────────────────────────────

    def _page_glenda_form(self, ack, prefill, error):
        emp   = ack.employee_id.name
        err_html = (
            f'<div style="background:#fde8e8;border:1px solid #f5c6cb;'
            f'border-radius:6px;padding:10px 14px;margin-bottom:16px;'
            f'font-size:13px;color:#721c24;">{error}</div>'
            if error else ''
        )
        return self._base_page(
            'Confirma tu número de WhatsApp',
            f"""
<div style="text-align:center;margin-bottom:24px;">
  <div style="font-size:52px;">🤖</div>
  <h2 style="color:#1a2c5b;margin:8px 0 4px;font-size:20px;">
    ¡Únete al programa Glenda!
  </h2>
  <p style="color:#555;font-size:14px;margin:0;">
    Hola <strong>{emp}</strong>, confirma el número de WhatsApp<br/>
    que usarás para interactuar con Glenda.
  </p>
</div>
{err_html}
<div style="background:#f0f4fa;border-radius:8px;padding:16px 18px;
            margin-bottom:20px;font-size:13px;color:#444;line-height:1.6;">
  <strong>¿Para qué sirve esto?</strong><br/>
  Tu número de WA nos permite vincular tus sesiones de calibración
  con Glenda a tu perfil, para calcular correctamente tu bono de participación.
</div>
<form method="POST" action="/glenda-calibracion/{ack.token}">
  <label style="display:block;font-size:13px;font-weight:bold;
                color:#1a2c5b;margin-bottom:8px;">
    Tu número de WhatsApp:
  </label>
  <input type="tel" name="wa_number" value="{prefill}"
         placeholder="+58 414 000 0000"
         style="width:100%;padding:12px 14px;border:2px solid #ccd6e8;
                border-radius:8px;font-size:16px;outline:none;
                transition:border 0.2s;" required/>
  <p style="font-size:11px;color:#888;margin:6px 0 20px;">
    Formato: +58 414 000 0000 &nbsp;|&nbsp; 0414-0000000
  </p>
  <button type="submit"
          style="width:100%;padding:14px;background:#1a2c5b;color:white;
                 border:none;border-radius:8px;font-size:15px;
                 font-weight:bold;cursor:pointer;letter-spacing:0.5px;">
    ✅ &nbsp;Confirmar mi participación
  </button>
</form>
""",
            extra_style="""
  input[type=tel]:focus { border-color: #1a2c5b; }
  button:hover { background: #2471a3 !important; }
"""
        )

    # ── HR notification — ACK confirmed (always sent) ────────────────────────

    def _notify_hr_ack_confirmed(self, emp, wa_number, status, old_number=''):
        """Send a confirmation email to recursoshumanos for every calibration ACK.

        status: 'registered' (no prior number), 'confirmed' (matched),
                'updated' (mismatch — auto-updated).
        """
        dt = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

        status_cfg = {
            'registered': ('#155724', '#d4edda', '#c3e6cb', '✅ Número registrado',
                           'registró su número de WhatsApp por primera vez'),
            'confirmed':  ('#1a2c5b', '#e8f0fe', '#c8d0e8', '✅ Número confirmado',
                           'confirmó su número de WhatsApp (coincide con Odoo)'),
            'updated':    ('#856404', '#fff3cd', '#ffeeba', '⚠️ Número actualizado',
                           'actualizó su número de WhatsApp (era diferente al de Odoo)'),
        }
        color, bg, border, badge, desc = status_cfg.get(status, status_cfg['confirmed'])

        old_row = ''
        if status == 'updated' and old_number:
            old_row = f"""
      <tr>
        <td style="padding:12px 18px;border-bottom:1px solid {border};">
          <span style="font-size:11px;color:#888;display:block;margin-bottom:2px;">NÚMERO ANTERIOR (Odoo)</span>
          <span style="font-size:14px;color:#c62828;text-decoration:line-through;">{old_number}</span>
        </td>
      </tr>"""

        body = f"""
<div style="font-family:Arial,sans-serif;max-width:540px;margin:0 auto;">
  <div style="background:#1a2c5b;color:#fff;padding:18px 24px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;font-size:17px;">📋 Programa Glenda AI — ACK Recibido</h2>
    <p style="margin:5px 0 0;font-size:12px;opacity:0.8;">Confirmación de participación</p>
  </div>
  <div style="background:#fff;border:1px solid #dde;padding:20px 24px;border-radius:0 0 8px 8px;">
    <p style="font-size:13px;color:#333;margin:0 0 14px;">
      El empleado <strong>{emp.name}</strong> {desc}.
    </p>
    <span style="display:inline-block;background:{bg};color:{color};border:1px solid {border};
                 font-size:12px;font-weight:bold;padding:4px 12px;border-radius:20px;
                 margin-bottom:16px;">{badge}</span>
    <table cellpadding="0" cellspacing="0"
           style="width:100%;background:{bg};border-radius:8px;border:1px solid {border};">
      <tr>
        <td style="padding:12px 18px;border-bottom:1px solid {border};">
          <span style="font-size:11px;color:#888;display:block;margin-bottom:2px;">EMPLEADO</span>
          <strong style="font-size:14px;color:#1a2c5b;">{emp.name}</strong>
          &nbsp;·&nbsp;
          <span style="font-size:12px;color:#555;">{emp.work_email or ''}</span>
        </td>
      </tr>{old_row}
      <tr>
        <td style="padding:12px 18px;border-bottom:1px solid {border};">
          <span style="font-size:11px;color:#888;display:block;margin-bottom:2px;">NÚMERO WHATSAPP CONFIRMADO</span>
          <strong style="font-size:14px;color:{color};">{wa_number}</strong>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 18px;">
          <span style="font-size:11px;color:#888;display:block;margin-bottom:2px;">FECHA DE CONFIRMACIÓN</span>
          <span style="font-size:13px;color:#333;">{dt}</span>
        </td>
      </tr>
    </table>
  </div>
</div>"""
        try:
            request.env['mail.mail'].sudo().create({
                'subject':    f'[Glenda Calibración] {badge} — {emp.name}',
                'email_from': 'Sistema UEIPAB <recursoshumanos@ueipab.edu.ve>',
                'email_to':   'recursoshumanos@ueipab.edu.ve',
                'body_html':  body,
                'state':      'outgoing',
            }).send()
        except Exception:
            pass  # best-effort, never break the ACK flow

    # ── HR notification on WA number mismatch (kept for backward compat) ─────

    def _notify_hr_number_change(self, emp, old_number, new_number):
        """Send an alert to recursoshumanos when an employee's WA number differs
        from what Odoo had on file and has been updated automatically."""
        dt = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        body = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
  <div style="background:#1a2c5b;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;font-size:18px;">📱 Actualización de número WA — Glenda Calibración</h2>
    <p style="margin:6px 0 0;font-size:13px;opacity:0.8;">Notificación automática del sistema</p>
  </div>
  <div style="background:#fff;border:1px solid #dde;padding:24px;border-radius:0 0 8px 8px;">
    <p style="font-size:14px;color:#333;margin:0 0 16px;">
      El empleado <strong>{emp.name}</strong> confirmó su número de WhatsApp
      para el Programa de Calibración de Glenda. El número ingresado
      <strong>no coincide</strong> con el registrado en Odoo —
      se actualizó automáticamente.
    </p>
    <table cellpadding="0" cellspacing="0"
           style="width:100%;background:#f5f7ff;border-radius:8px;
                  border:1px solid #c8d0e8;">
      <tr>
        <td style="padding:14px 18px;border-bottom:1px solid #dde;">
          <span style="font-size:12px;color:#888;display:block;margin-bottom:2px;">
            EMPLEADO
          </span>
          <strong style="font-size:15px;color:#1a2c5b;">{emp.name}</strong>
          &nbsp;·&nbsp;
          <span style="font-size:13px;color:#555;">{emp.work_email or ''}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:14px 18px;border-bottom:1px solid #dde;">
          <span style="font-size:12px;color:#888;display:block;margin-bottom:2px;">
            NÚMERO ANTERIOR (Odoo)
          </span>
          <span style="font-size:15px;color:#c62828;
                       text-decoration:line-through;">{old_number}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:14px 18px;border-bottom:1px solid #dde;">
          <span style="font-size:12px;color:#888;display:block;margin-bottom:2px;">
            NÚMERO NUEVO (confirmado por empleado)
          </span>
          <strong style="font-size:15px;color:#155724;">{new_number}</strong>
        </td>
      </tr>
      <tr>
        <td style="padding:14px 18px;">
          <span style="font-size:12px;color:#888;display:block;margin-bottom:2px;">
            FECHA DE CONFIRMACIÓN
          </span>
          <span style="font-size:13px;color:#333;">{dt}</span>
        </td>
      </tr>
    </table>
    <p style="font-size:12px;color:#888;margin:16px 0 0;">
      El campo <em>Teléfono móvil</em> del empleado en Odoo fue actualizado
      automáticamente al nuevo número. Si hay algún error, corríjalo directamente
      en el perfil del empleado.
    </p>
  </div>
</div>"""
        try:
            request.env['mail.mail'].sudo().create({
                'subject':    f'[Glenda Calibración] WA actualizado — {emp.name}',
                'email_from': 'Sistema UEIPAB <recursoshumanos@ueipab.edu.ve>',
                'email_to':   'recursoshumanos@ueipab.edu.ve',
                'body_html':  body,
                'state':      'outgoing',
            }).send()
        except Exception:
            pass  # Notification is best-effort; don't break the ACK flow

    # ── Glenda success page ───────────────────────────────────────────────────

    def _page_glenda_success(self, ack, wa_number, number_changed=False):
        emp = ack.employee_id.name
        dt  = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
        update_note = ''
        if number_changed:
            update_note = """
<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;
            padding:12px 16px;font-size:12px;color:#795548;margin-bottom:14px;">
  ⚠️&nbsp; <strong>Número actualizado:</strong> el número ingresado difiere del
  registrado en Odoo — tu perfil fue actualizado automáticamente y se notificó
  a Recursos Humanos.
</div>"""
        return self._base_page(
            'Registro confirmado',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">🎉</div>
  <h2 style="color:#155724;margin:10px 0 4px;">¡Registro completado!</h2>
  <p style="color:#555;font-size:14px;margin:0;">
    Gracias, <strong>{emp}</strong>.
  </p>
</div>
<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:8px;
            padding:18px;font-size:13px;color:#155724;margin-bottom:14px;
            line-height:1.8;">
  <p style="margin:0 0 6px;">✅ &nbsp;<strong>Participación confirmada</strong></p>
  <p style="margin:0 0 6px;">📱 &nbsp;<strong>WA registrado:</strong> {wa_number}</p>
  <p style="margin:0;">🕐 &nbsp;<strong>Fecha:</strong> {dt}</p>
</div>
{update_note}
<div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;
            padding:14px 18px;font-size:13px;color:#795548;margin-bottom:16px;">
  <strong>¿Qué sigue?</strong><br/>
  RRHH te contactará con los detalles del programa.
  Mientras tanto, puedes escribirle a Glenda en WhatsApp:
  <br/><br/>
  <a href="https://wa.me/584148321989"
     style="display:inline-block;background:#25d366;color:white;
            padding:10px 20px;border-radius:6px;text-decoration:none;
            font-weight:bold;font-size:14px;">
    💬 &nbsp;Escríbele a Glenda: +58 414 832 1989
  </a>
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin:0;">
  Puedes cerrar esta página.
</p>
"""
        )

    def _page_glenda_already_done(self, ack):
        emp = ack.employee_id.name
        dt  = ack.ack_date.strftime('%d/%m/%Y %H:%M') if ack.ack_date else ''
        wa  = ack.wa_number or '(no registrado)'
        return self._base_page(
            'Ya registrado',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:52px;">📋</div>
  <h2 style="color:#1a2c5b;margin:10px 0 4px;">Ya estás registrado/a</h2>
  <p style="color:#555;font-size:14px;margin:0;"><strong>{emp}</strong></p>
</div>
<div style="background:#e8f4f8;border:1px solid #bee5eb;border-radius:8px;
            padding:16px 18px;font-size:13px;color:#1a2c5b;line-height:1.8;">
  <p style="margin:0 0 4px;">📱 <strong>WA confirmado:</strong> {wa}</p>
  <p style="margin:0;">🕐 <strong>Registrado el:</strong> {dt}</p>
</div>
"""
        )

    # ── Generic pages (existing notice keys) ─────────────────────────────────

    def _page_success(self, ack):
        emp   = ack.employee_id.name
        label = ack.notice_label or ack.notice_key
        dt    = ack.ack_date.strftime('%d/%m/%Y %H:%M') if ack.ack_date else ''
        content = f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">&#9989;</div>
  <h2 style="color:#155724;margin:10px 0 4px;">Confirmaci&oacute;n registrada</h2>
  <p style="color:#555;font-size:14px;margin:0;">Gracias, <strong>{emp}</strong>.</p>
</div>
<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:6px;
            padding:16px;font-size:13px;color:#155724;margin-bottom:16px;">
  <p style="margin:0 0 6px;"><strong>Comunicado:</strong> {label}</p>
  <p style="margin:0 0 6px;"><strong>Confirmado el:</strong> {dt}</p>
  <p style="margin:0;"><strong>Estado:</strong> Le&iacute;do y entendido &#9989;</p>
</div>
<p style="font-size:13px;color:#888;text-align:center;margin:0;">
  Puede cerrar esta p&aacute;gina.</p>"""
        return self._base_page('Confirmación registrada', content)

    def _page_already_done(self, ack):
        emp = ack.employee_id.name
        dt  = ack.ack_date.strftime('%d/%m/%Y %H:%M') if ack.ack_date else ''
        content = f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">&#128203;</div>
  <h2 style="color:#1a2c5b;margin:10px 0 4px;">Ya confirmado</h2>
  <p style="color:#555;font-size:14px;margin:0;"><strong>{emp}</strong></p>
</div>
<div style="background:#e8f4f8;border:1px solid #bee5eb;border-radius:6px;
            padding:16px;font-size:13px;color:#1a2c5b;">
  <p style="margin:0;">Este comunicado ya fue confirmado el <strong>{dt}</strong>.
  No es necesario confirmar nuevamente.</p>
</div>"""
        return self._base_page('Ya confirmado', content)

    def _page_invalid(self):
        content = """
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">&#10060;</div>
  <h2 style="color:#721c24;margin:10px 0 4px;">Enlace no v&aacute;lido</h2>
</div>
<div style="background:#fde8e8;border:1px solid #f5c6cb;border-radius:6px;
            padding:16px;font-size:13px;color:#721c24;">
  <p style="margin:0;">Este enlace no es v&aacute;lido o ya expir&oacute;.
  Si necesita ayuda contacte a
  <a href="mailto:recursoshumanos@ueipab.edu.ve" style="color:#721c24;">
    recursoshumanos@ueipab.edu.ve</a>.</p>
</div>"""
        return self._base_page('Enlace inválido', content)
