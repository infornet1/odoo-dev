import datetime
import re

from odoo import fields, http
from odoo.http import request

_WA_RE = re.compile(r'^\+?[0-9\s\-]{7,20}$')

# Notice keys that require the WA-number confirmation form instead of
# an immediate one-click ACK.
_WA_FORM_KEYS = {'glenda_calibracion_v1'}


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

        # Compare with existing mobile — update and notify HR if different
        number_changed = old_mobile and old_mobile != wa_clean
        if not old_mobile or number_changed:
            emp.write({'mobile_phone': wa_clean})

        if number_changed:
            self._notify_hr_number_change(emp, old_mobile, wa_clean)

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

    # ── HR notification on WA number mismatch ────────────────────────────────

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
