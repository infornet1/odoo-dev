import datetime
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PartnerAckController(http.Controller):

    # ── Direct YES from email link ────────────────────────────────────────────

    @http.route('/partner-ack/<string:token>/si', type='http', auth='public', website=False)
    def partner_ack_si(self, token, **kwargs):
        return self._record_decision(token, 'continuing')

    # ── Direct NO from email link ─────────────────────────────────────────────

    @http.route('/partner-ack/<string:token>/no', type='http', auth='public', website=False)
    def partner_ack_no(self, token, **kwargs):
        return self._record_decision(token, 'leaving')

    # ── Landing page (no-param link, shows decision form) ────────────────────

    @http.route('/partner-ack/<string:token>', type='http', auth='public', website=False)
    def partner_ack_landing(self, token, **kwargs):
        Ack = request.env['partner.communication.ack'].sudo()
        ack = Ack.search([('token', '=', token)], limit=1)
        if not ack:
            return self._respond(self._page_invalid())
        if ack.state != 'pending':
            return self._respond(self._page_already_done(ack))
        deadline = self._VOTE_DEADLINES.get(ack.notice_key)
        if deadline and datetime.date.today() > deadline:
            return self._respond(self._page_voting_closed(ack))
        return self._respond(self._page_decision(ack))

    # ── Core decision handler ─────────────────────────────────────────────────

    _VOTE_DEADLINES = {
        'budget_consulta_2026_2027': datetime.date(2026, 6, 8),
        # Closed early per CEO on 2026-07-01 (threshold 90 SÍ surpassed at 115).
        # Gate moved a day back to force closure now; the closed page still
        # DISPLAYS "01 de julio de 2026" (the deadline parents were promised).
        'contingencia_academica_2026': datetime.date(2026, 6, 30),
    }

    def _record_decision(self, token, decision):
        Ack = request.env['partner.communication.ack'].sudo()
        ack = Ack.search([('token', '=', token)], limit=1)
        if not ack:
            return self._respond(self._page_invalid())
        if ack.state != 'pending':
            return self._respond(self._page_already_done(ack))
        deadline = self._VOTE_DEADLINES.get(ack.notice_key)
        if deadline and datetime.date.today() > deadline:
            return self._respond(self._page_voting_closed(ack))
        ip = self._client_ip()
        ack.write({
            'state':        decision,
            'ack_date':     datetime.datetime.now(),
            'ack_ip':       ip,
            'vote_channel': 'email_link',
        })
        _logger.info('partner_ack: %s decision=%s ip=%s', ack.partner_name, decision, ip)
        self._send_ack_confirmation(ack, decision)
        if decision == 'continuing':
            return self._respond(self._page_success_yes(ack))
        return self._respond(self._page_success_no(ack))

    def _vote_context(self, ack, decision):
        """Return label/styling for a vote decision, adapting to notice_key."""
        is_budget = (ack.notice_key == 'budget_consulta_2026_2027')
        if is_budget:
            if decision == 'continuing':
                return {
                    'label': 'Votó por Opción A — $218,88/mes ✅',
                    'bg': '#e8f0fb', 'border': '#b8cef5', 'color': '#1a2c5b',
                    'emoji': '🗳️',
                }
            return {
                'label': 'Votó por Opción B — $236,58/mes ✅',
                'bg': '#f3e5f5', 'border': '#ce93d8', 'color': '#6c3483',
                'emoji': '🗳️',
            }
        if ack.notice_key == 'contingencia_academica_2026':
            if decision == 'continuing':
                return {
                    'label': 'SÍ — Estoy de acuerdo ✅',
                    'bg': '#e8f5e9', 'border': '#c3e6cb', 'color': '#1b5e20',
                    'emoji': '✅',
                }
            return {
                'label': 'NO — Mantener el esquema actual',
                'bg': '#fff3cd', 'border': '#ffe69c', 'color': '#856404',
                'emoji': '📋',
            }
        if ack.notice_key == 'loyalty_2026_2027':
            return {
                'label': 'Beneficio de fidelidad aceptado ✅',
                'bg': '#f6f9fc', 'border': '#c8a04b', 'color': '#0b3d6b',
                'emoji': '🤝',
            }
        # Default: continuity campaign
        if decision == 'continuing':
            return {
                'label': 'Sí, continuará en 2026-2027 ✅',
                'bg': '#d4edda', 'border': '#c3e6cb', 'color': '#155724',
                'emoji': '🎉',
            }
        return {
            'label': 'No continuará ❌',
            'bg': '#e8f4f8', 'border': '#bee5eb', 'color': '#1a2c5b',
            'emoji': '📋',
        }

    def _send_ack_confirmation(self, ack, decision):
        """Send CC confirmation to votacion@ when a partner records their decision."""
        try:
            dt       = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
            name     = ack.partner_name or ''
            email    = ack.partner_email or ''
            ctx      = self._vote_context(ack, decision)
            label    = ctx['label']
            bg       = ctx['bg']
            border   = ctx['border']
            color    = ctx['color']

            header_title = (
                '&#129309; Carta de Fidelidad 2026-2027 &mdash; Beneficio aceptado'
                if ack.notice_key == 'loyalty_2026_2027'
                else '&#128221; Encuesta Continuidad 2026-2027 — Respuesta registrada'
            )
            body = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;">
  <div style="background:#1a2c5b;color:#fff;padding:18px 24px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;font-size:16px;">
      {header_title}
    </h2>
    <p style="margin:5px 0 0;font-size:12px;opacity:0.8;">Confirmaci&oacute;n autom&aacute;tica</p>
  </div>
  <div style="background:#fff;border:1px solid #dde;padding:20px 24px;border-radius:0 0 8px 8px;">
    <table cellpadding="0" cellspacing="0"
           style="width:100%;background:{bg};border-radius:8px;border:1px solid {border};">
      <tr>
        <td style="padding:12px 18px;border-bottom:1px solid {border};">
          <span style="font-size:11px;color:#888;display:block;margin-bottom:2px;">REPRESENTANTE</span>
          <strong style="font-size:14px;color:#1a2c5b;">{name}</strong>
          &nbsp;&middot;&nbsp;
          <span style="font-size:12px;color:#555;">{email}</span>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 18px;border-bottom:1px solid {border};">
          <span style="font-size:11px;color:#888;display:block;margin-bottom:2px;">DECISI&Oacute;N</span>
          <strong style="font-size:14px;color:{color};">{label}</strong>
        </td>
      </tr>
      <tr>
        <td style="padding:12px 18px;">
          <span style="font-size:11px;color:#888;display:block;margin-bottom:2px;">FECHA</span>
          <span style="font-size:13px;color:#333;">{dt}</span>
        </td>
      </tr>
    </table>
  </div>
</div>"""

            # Vote campaigns share the votacion@ inbox; loyalty routes to pagos@.
            email_from  = 'Colegio Andrés Bello <votacion@ueipab.edu.ve>'
            inbox       = 'votacion@ueipab.edu.ve'
            if ack.notice_key == 'loyalty_2026_2027':
                email_from = 'Colegio Andrés Bello - Pagos <pagos@ueipab.edu.ve>'
                inbox      = 'pagos@ueipab.edu.ve'
                subject    = f'[Carta de Fidelidad 2026-2027] {label} — {name}'
            elif ack.notice_key == 'contingencia_academica_2026':
                subject     = f'[Contingencia Académica] {label} — {name}'
            else:
                subject     = f'[Encuesta 2026-2027] {label} — {name}'

            request.env['mail.mail'].sudo().create({
                'subject':    subject,
                'email_from': email_from,
                'email_to':   f'{name} <{email}>' if email else inbox,
                'email_cc':   inbox,
                'body_html':  body,
                'state':      'outgoing',
            }).send()
        except Exception:
            pass  # best-effort, never break the ACK flow

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

    def _base_page(self, title, content):
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} &mdash; Instituto Andr&eacute;s Bello</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: Arial, sans-serif; background: #f0f4fa;
            margin: 0; padding: 40px 16px; }}
    .card {{ max-width: 540px; margin: 0 auto; background: white;
             border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.12);
             overflow: hidden; }}
    .header {{ background-color: #1a2c5b; color: white;
               padding: 28px 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 18px; font-weight: bold; }}
    .header p  {{ margin: 6px 0 0; font-size: 13px; opacity: 0.85; }}
    .body   {{ padding: 28px 24px; }}
    .footer {{ background: #f8f9fa; padding: 14px 24px; text-align: center;
               font-size: 11px; color: #aaa; border-top: 1px solid #e8e8e8; }}
    .btn {{ display: inline-block; padding: 14px 28px; border-radius: 8px;
            font-size: 15px; font-weight: bold; text-decoration: none;
            cursor: pointer; text-align: center; }}
    .btn-yes {{ background-color: #1a2c5b; color: white; }}
    .btn-yes:hover {{ background-color: #2471a3; }}
    .btn-no  {{ background-color: #5d6d7e; color: white; margin-left: 12px; }}
    .btn-no:hover {{ background-color: #4a5568; }}
    @media (max-width: 480px) {{
      .btn {{ display: block; margin: 8px 0 !important; }}
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;</h1>
      <p>El Tigre, Estado Anzo&aacute;tegui</p>
    </div>
    <div class="body">{content}</div>
    <div class="footer">
      ¿Preguntas? Escr&iacute;benos a
      <a href="mailto:votacion@ueipab.edu.ve" style="color:#2471a3;">votacion@ueipab.edu.ve</a>
    </div>
  </div>
</body>
</html>"""

    # ── Decision landing page ─────────────────────────────────────────────────

    def _page_decision(self, ack):
        name = ack.partner_name or ''
        si_url = ack._get_si_url()
        no_url = ack._get_no_url()
        return self._base_page(
            'Confirmar intenci&oacute;n',
            f"""
<div style="text-align:center;margin-bottom:24px;">
  <div style="font-size:48px;">&#127979;</div>
  <h2 style="color:#1a2c5b;margin:10px 0 4px;font-size:20px;">
    Per&iacute;odo 2026-2027
  </h2>
  <p style="color:#555;font-size:14px;margin:0;">
    Estimado(a) representante <strong>{name}</strong>
  </p>
</div>
<div style="background:#f0f4fa;border-left:4px solid #1a2c5b;padding:16px 18px;
            border-radius:4px;font-size:13px;color:#333;margin-bottom:24px;">
  <p style="margin:0 0 8px;"><strong>Comunicado:</strong> Pol&iacute;tica de descuento PDVSA &mdash; Per&iacute;odo 2026-2027</p>
  <p style="margin:0;"><strong>Fecha l&iacute;mite:</strong> 08 de junio de 2026 a las 12:30 p.m.</p>
</div>
<p style="font-size:14px;color:#333;margin:0 0 20px;">
  Por favor confirme si desea continuar en nuestra instituci&oacute;n para el
  pr&oacute;ximo per&iacute;odo escolar:
</p>
<div style="text-align:center;padding:10px 0;">
  <a href="{si_url}" class="btn btn-yes">
    &#10003;&nbsp; S&iacute;, continuar&eacute; en 2026-2027
  </a>
  <a href="{no_url}" class="btn btn-no">
    No continuar&eacute;
  </a>
</div>
<p style="font-size:11px;color:#aaa;text-align:center;margin:20px 0 0;">
  Si no responde antes del 08/06/2026, el sistema asumir&aacute; que acepta
  las nuevas condiciones para el per&iacute;odo 2026-2027.
</p>
"""
        )

    # ── Success pages ─────────────────────────────────────────────────────────

    def _page_loyalty_success(self, ack):
        name = ack.partner_name or ''
        dt   = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
        return self._base_page(
            'Beneficio de fidelidad confirmado',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">&#129309;</div>
  <h2 style="color:#0b3d6b;margin:10px 0 4px;">¡Gracias por su fidelidad!</h2>
  <p style="color:#555;font-size:14px;margin:0;"><strong>{name}</strong></p>
</div>
<div style="background:#f6f9fc;border:1px solid #c8a04b;border-radius:8px;
            padding:18px;font-size:13px;color:#0b3d6b;margin-bottom:16px;line-height:1.8;">
  <p style="margin:0 0 6px;">&#10003;&nbsp; <strong>Beneficio de fidelidad 2026-2027 registrado.</strong></p>
  <p style="margin:0;">&#128336;&nbsp; <strong>Confirmado el:</strong> {dt}</p>
</div>
<div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;
            font-size:13px;color:#444;margin-bottom:16px;">
  <p style="margin:0 0 6px;"><strong>Pr&oacute;ximos pasos:</strong></p>
  <p style="margin:0;">El equipo de admisiones formalizar&aacute; su inscripci&oacute;n 2026-2027 con la
  <strong>tarifa preferencial</strong> reservada para su familia. Para cualquier consulta escr&iacute;banos a
  <a href="mailto:pagos@ueipab.edu.ve" style="color:#2471a3;">pagos@ueipab.edu.ve</a>.</p>
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin:0;">Puede cerrar esta p&aacute;gina.</p>
"""
        )

    def _page_success_yes(self, ack):
        if ack.notice_key == 'budget_consulta_2026_2027':
            return self._page_budget_vote_success(ack, 'continuing')
        if ack.notice_key == 'contingencia_academica_2026':
            return self._page_contingencia_success(ack, 'continuing')
        if ack.notice_key == 'loyalty_2026_2027':
            return self._page_loyalty_success(ack)
        name = ack.partner_name or ''
        dt   = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
        return self._base_page(
            'Continuidad confirmada',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">&#127881;</div>
  <h2 style="color:#155724;margin:10px 0 4px;">¡Gracias por confirmar!</h2>
  <p style="color:#555;font-size:14px;margin:0;">
    <strong>{name}</strong>
  </p>
</div>
<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:8px;
            padding:18px;font-size:13px;color:#155724;margin-bottom:16px;line-height:1.8;">
  <p style="margin:0 0 6px;">&#10003;&nbsp; <strong>Decisi&oacute;n registrada:</strong> Continuidad en 2026-2027</p>
  <p style="margin:0;">&#128336;&nbsp; <strong>Confirmado el:</strong> {dt}</p>
</div>
<div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;
            font-size:13px;color:#444;margin-bottom:16px;">
  <p style="margin:0 0 6px;"><strong>Pr&oacute;ximos pasos:</strong></p>
  <p style="margin:0;">El equipo de administraci&oacute;n le contactar&aacute; con la informaci&oacute;n
  de inscripci&oacute;n para el per&iacute;odo 2026-2027. Si tiene consultas sobre
  facturaci&oacute;n escr&iacute;banos a
  <a href="mailto:votacion@ueipab.edu.ve" style="color:#2471a3;">votacion@ueipab.edu.ve</a>.</p>
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin:0;">Puede cerrar esta p&aacute;gina.</p>
"""
        )

    def _page_success_no(self, ack):
        if ack.notice_key == 'budget_consulta_2026_2027':
            return self._page_budget_vote_success(ack, 'leaving')
        if ack.notice_key == 'contingencia_academica_2026':
            return self._page_contingencia_success(ack, 'leaving')
        name = ack.partner_name or ''
        dt   = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
        return self._base_page(
            'Decisi&oacute;n registrada',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">&#128203;</div>
  <h2 style="color:#1a2c5b;margin:10px 0 4px;">Decisi&oacute;n registrada</h2>
  <p style="color:#555;font-size:14px;margin:0;">
    <strong>{name}</strong>
  </p>
</div>
<div style="background:#e8f4f8;border:1px solid #bee5eb;border-radius:8px;
            padding:18px;font-size:13px;color:#1a2c5b;margin-bottom:16px;line-height:1.8;">
  <p style="margin:0 0 6px;">&#128221;&nbsp; <strong>Decisi&oacute;n registrada:</strong> No continuar&aacute; en 2026-2027</p>
  <p style="margin:0;">&#128336;&nbsp; <strong>Registrado el:</strong> {dt}</p>
</div>
<div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;
            font-size:13px;color:#444;margin-bottom:16px;">
  <p style="margin:0 0 6px;"><strong>¿Cambi&oacute; de opini&oacute;n?</strong></p>
  <p style="margin:0;">Si desea reconsiderar, escr&iacute;banos a
  <a href="mailto:votacion@ueipab.edu.ve" style="color:#2471a3;">votacion@ueipab.edu.ve</a>
  antes del 08 de junio de 2026 a las 12:30 p.m.</p>
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin:0;">Puede cerrar esta p&aacute;gina.</p>
"""
        )

    def _page_already_done(self, ack):
        name  = ack.partner_name or ''
        dt    = ack.ack_date.strftime('%d/%m/%Y %H:%M') if ack.ack_date else ''
        ctx   = self._vote_context(ack, ack.state)
        label = ctx['label']
        return self._base_page(
            'Ya respondido',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:52px;">&#128203;</div>
  <h2 style="color:#1a2c5b;margin:10px 0 4px;">Ya respondiste</h2>
  <p style="color:#555;font-size:14px;margin:0;"><strong>{name}</strong></p>
</div>
<div style="background:#e8f4f8;border:1px solid #bee5eb;border-radius:8px;
            padding:16px 18px;font-size:13px;color:#1a2c5b;">
  <p style="margin:0 0 4px;"><strong>Decisi&oacute;n:</strong> {label}</p>
  <p style="margin:0;"><strong>Respondido el:</strong> {dt}</p>
</div>
"""
        )

    def _page_voting_closed(self, ack):
        name = ack.partner_name or ''
        if ack.notice_key == 'contingencia_academica_2026':
            survey_name = 'Encuesta del Plan de Contingencia Acad&eacute;mica'
            deadline    = '01 de julio de 2026'
            contact     = 'votacion@ueipab.edu.ve'
        else:
            survey_name = 'Consulta Presupuestaria 2026-2027'
            deadline    = '08 de junio de 2026'
            contact     = 'pagos@ueipab.edu.ve'
        return self._base_page(
            'Consulta cerrada',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:52px;">&#128274;</div>
  <h2 style="color:#1a2c5b;margin:10px 0 4px;">Per&iacute;odo de consulta cerrado</h2>
  <p style="color:#555;font-size:14px;margin:0;"><strong>{name}</strong></p>
</div>
<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;
            padding:16px 18px;font-size:13px;color:#856404;margin-bottom:16px;">
  <p style="margin:0;">El plazo para participar en la {survey_name}
  venci&oacute; el <strong>{deadline}</strong>. Los resultados oficiales ya
  fueron publicados.</p>
</div>
<div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;font-size:13px;color:#444;">
  <p style="margin:0;">Si tiene preguntas,
  escr&iacute;banos a
  <a href="mailto:{contact}" style="color:#2471a3;">{contact}</a>.</p>
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin:16px 0 0;">Puede cerrar esta p&aacute;gina.</p>
"""
        )

    def _page_budget_vote_success(self, ack, decision):
        name  = ack.partner_name or ''
        dt    = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
        ctx   = self._vote_context(ack, decision)
        is_a  = (decision == 'continuing')
        price = '$218,88' if is_a else '$236,58'
        label = 'Opci&oacute;n A' if is_a else 'Opci&oacute;n B'
        pp    = '$207,93' if is_a else '$224,75'
        annual = '$2.845,45' if is_a else '$3.075,55'
        hdr_bg = '#1a2c5b' if is_a else '#6c3483'
        return self._base_page(
            f'Voto registrado &mdash; {label}',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">🗳️</div>
  <h2 style="color:{hdr_bg};margin:10px 0 4px;">¡Voto registrado!</h2>
  <p style="color:#555;font-size:14px;margin:0;">
    <strong>{name}</strong>
  </p>
</div>
<div style="background:{ctx['bg']};border:2px solid {ctx['border']};border-radius:10px;
            padding:18px;font-size:13px;color:{ctx['color']};margin-bottom:16px;text-align:center;">
  <div style="font-size:22px;font-weight:bold;margin-bottom:6px;">{ctx['emoji']} {label}</div>
  <div style="font-size:32px;font-weight:bold;margin-bottom:4px;">{price}<span style="font-size:14px;">/mes</span></div>
  <div style="font-size:12px;opacity:0.8;">Pronto pago: {pp} &nbsp;|&nbsp; Costo anual: {annual}</div>
  <div style="margin-top:10px;font-size:12px;">&#128336;&nbsp; Registrado el: <strong>{dt}</strong></div>
</div>
<div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;font-size:13px;color:#444;">
  <p style="margin:0;">Los resultados de la votaci&oacute;n ser&aacute;n publicados el <strong>26 de mayo de 2026</strong>.
  Para consultas escr&iacute;banos a
  <a href="mailto:votacion@ueipab.edu.ve" style="color:#1a2c5b;">votacion@ueipab.edu.ve</a>.</p>
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin:16px 0 0;">Puede cerrar esta p&aacute;gina.</p>
"""
        )

    def _page_contingencia_success(self, ack, decision):
        name   = ack.partner_name or ''
        dt     = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
        ctx    = self._vote_context(ack, decision)
        is_yes = (decision == 'continuing')
        hdr_bg = '#1b5e20' if is_yes else '#856404'
        headline = '¡Respuesta registrada!' if is_yes else 'Respuesta registrada'
        if is_yes:
            stance = ('Est&aacute; de acuerdo con la activaci&oacute;n del plan bimodal '
                      '&mdash; Google Classroom + Google Meet')
        else:
            stance = ('Prefiere mantener el esquema actual y esperar nuevas '
                      'disposiciones de las autoridades')
        return self._base_page(
            'Respuesta registrada &mdash; Plan de Contingencia',
            f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">{ctx['emoji']}</div>
  <h2 style="color:{hdr_bg};margin:10px 0 4px;">{headline}</h2>
  <p style="color:#555;font-size:14px;margin:0;">
    <strong>{name}</strong>
  </p>
</div>
<div style="background:{ctx['bg']};border:2px solid {ctx['border']};border-radius:10px;
            padding:18px;font-size:13px;color:{ctx['color']};margin-bottom:16px;text-align:center;">
  <div style="font-size:18px;font-weight:bold;margin-bottom:8px;">{ctx['emoji']} {ctx['label']}</div>
  <div style="font-size:13px;line-height:1.6;">{stance}</div>
  <div style="margin-top:10px;font-size:12px;">&#128336;&nbsp; Registrado el: <strong>{dt}</strong></div>
</div>
<div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;font-size:13px;color:#444;">
  <p style="margin:0 0 6px;">El Plan de Contingencia Acad&eacute;mica bajo el modelo bimodal
  se activar&aacute; &uacute;nicamente al alcanzar el <strong>50% + 1</strong> de aprobaci&oacute;n
  del total de la plantilla de representantes.</p>
  <p style="margin:0;">Para consultas escr&iacute;banos a
  <a href="mailto:votacion@ueipab.edu.ve" style="color:#1b5e20;">votacion@ueipab.edu.ve</a>.</p>
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin:16px 0 0;">Puede cerrar esta p&aacute;gina.</p>
"""
        )

    def _page_invalid(self):
        return self._base_page(
            'Enlace no v&aacute;lido',
            """
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">&#10060;</div>
  <h2 style="color:#5d6d7e;margin:10px 0 4px;">Enlace no v&aacute;lido</h2>
</div>
<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;
            padding:16px;font-size:13px;color:#555;">
  <p style="margin:0;">Este enlace no es v&aacute;lido o ya expir&oacute;.
  Si necesita ayuda cont&aacute;ctenos en
  <a href="mailto:votacion@ueipab.edu.ve" style="color:#2471a3;">
    votacion@ueipab.edu.ve</a>.</p>
</div>
"""
        )
