import datetime

from odoo import http
from odoo.http import request


class AttendanceAckController(http.Controller):

    @http.route('/attendance-ack/<string:token>', type='http', auth='public', website=False)
    def attendance_ack(self, token, **kwargs):
        Report = request.env['hr.attendance.report'].sudo()
        report = Report.search([('ack_token', '=', token)], limit=1)

        if not report:
            return request.make_response(
                self._page_invalid(),
                headers=[('Content-Type', 'text/html; charset=utf-8')],
            )

        if report.state == 'acknowledged':
            return request.make_response(
                self._page_already_done(report),
                headers=[('Content-Type', 'text/html; charset=utf-8')],
            )

        # Capture real IP (behind nginx proxy)
        ip = (
            request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '')
            .split(',')[0].strip()
            or request.httprequest.remote_addr
        )

        report.write({
            'state': 'acknowledged',
            'ack_date': datetime.datetime.now(),
            'ack_ip': ip,
        })

        return request.make_response(
            self._page_success(report),
            headers=[('Content-Type', 'text/html; charset=utf-8')],
        )

    # -------------------------------------------------------------------------
    # HTML response pages (inline — no template dependency)
    # -------------------------------------------------------------------------

    def _base_page(self, content):
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Reporte de Asistencia - UEIPAB</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f0f4fa; margin: 0; padding: 40px 20px; }}
    .card {{ max-width: 480px; margin: 0 auto; background: white; border-radius: 10px;
              box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #1a2c5b, #2471a3); color: white;
               padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 20px; }}
    .header p {{ margin: 6px 0 0; font-size: 13px; opacity: 0.85; }}
    .body {{ padding: 28px 24px; }}
    .footer {{ background: #f8f9fa; padding: 14px 24px; text-align: center;
               font-size: 12px; color: #999; border-top: 1px solid #e0e0e0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>Instituto Privado Andr&eacute;s Bello, CA</h1>
      <p>Recursos Humanos</p>
    </div>
    <div class="body">{content}</div>
    <div class="footer">Este enlace es de uso personal e intransferible.</div>
  </div>
</body>
</html>"""

    def _page_success(self, report):
        emp = report.employee_id.name
        period = report.get_period_label()
        ack_dt = report.ack_date.strftime('%d/%m/%Y %H:%M') if report.ack_date else ''
        content = f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:60px;">&#9989;</div>
  <h2 style="color:#155724;margin:10px 0 4px;">Confirmaci&oacute;n registrada</h2>
  <p style="color:#555;font-size:14px;margin:0;">Gracias, <strong>{emp}</strong>.</p>
</div>
<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:6px;padding:16px;font-size:13px;color:#155724;">
  <p style="margin:0 0 8px;"><strong>Per&iacute;odo:</strong> {period}</p>
  <p style="margin:0 0 8px;"><strong>Fecha de confirmaci&oacute;n:</strong> {ack_dt}</p>
  <p style="margin:0;"><strong>Estado:</strong> Recepci&oacute;n confirmada &#9989;</p>
</div>
<p style="font-size:13px;color:#666;text-align:center;margin-top:20px;">
  Ya puede cerrar esta p&aacute;gina.
</p>"""
        return self._base_page(content)

    def _page_already_done(self, report):
        emp = report.employee_id.name
        ack_dt = report.ack_date.strftime('%d/%m/%Y %H:%M') if report.ack_date else ''
        content = f"""
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:60px;">&#128203;</div>
  <h2 style="color:#1a2c5b;margin:10px 0 4px;">Ya confirmado</h2>
  <p style="color:#555;font-size:14px;margin:0;"><strong>{emp}</strong></p>
</div>
<div style="background:#e8f4f8;border:1px solid #bee5eb;border-radius:6px;padding:16px;font-size:13px;color:#1a2c5b;">
  <p style="margin:0;">Este reporte ya fue confirmado el <strong>{ack_dt}</strong>.
  No es necesario confirmar nuevamente.</p>
</div>"""
        return self._base_page(content)

    def _page_invalid(self):
        content = """
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:60px;">&#10060;</div>
  <h2 style="color:#721c24;margin:10px 0 4px;">Enlace no v&aacute;lido</h2>
</div>
<div style="background:#fde8e8;border:1px solid #f5c6cb;border-radius:6px;padding:16px;font-size:13px;color:#721c24;">
  <p style="margin:0;">Este enlace de confirmaci&oacute;n no es v&aacute;lido o ya expir&oacute;.
  Si necesita ayuda, contacte a
  <a href="mailto:recursoshumanos@ueipab.edu.ve" style="color:#721c24;">recursoshumanos@ueipab.edu.ve</a>.</p>
</div>"""
        return self._base_page(content)
