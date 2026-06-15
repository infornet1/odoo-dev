# -*- coding: utf-8 -*-
from markupsafe import escape

from odoo import http
from odoo.http import request


class QuoteVerifyPage(http.Controller):

    @http.route('/verify-quote/<string:token>', type='http',
                auth='public', website=False, csrf=False)
    def verify_quote(self, token, **kw):
        order = request.env['sale.order'].sudo().search(
            [('access_token', '=', token)], limit=1)
        if not order:
            return request.make_response(
                self._render_invalid(),
                headers=[('Content-Type', 'text/html; charset=utf-8')],
                status=404)
        return request.make_response(
            self._render_valid(order),
            headers=[('Content-Type', 'text/html; charset=utf-8')])

    def _render_valid(self, order):
        from datetime import datetime
        state_labels = {
            'draft': 'Borrador',
            'sent': 'Enviado al Representante',
            'sale': 'Confirmado ✓',
            'done': 'Completado ✓',
            'cancel': 'Cancelado',
        }
        state_colors = {
            'draft': '#888',
            'sent': '#1565c0',
            'sale': '#27ae60',
            'done': '#27ae60',
            'cancel': '#c0392b',
        }
        state = order.state
        state_label = escape(state_labels.get(state, state))
        state_color = state_colors.get(state, '#333')
        partner_name = escape(order.partner_id.name or '')
        order_name = escape(order.name or '')
        date_str = order.date_order.strftime('%d/%m/%Y') if order.date_order else '—'
        validity_str = order.validity_date.strftime('%d/%m/%Y') if order.validity_date else '—'
        amount = '%.2f' % order.amount_total
        n_students = int(max(order.order_line.mapped('product_uom_qty') or [0]))
        now = datetime.now().strftime('%d/%m/%Y %H:%M')

        line_rows = ''.join(
            '<tr><td style="padding:4px 6px;border-bottom:1px solid #eef2f8;">{name}</td>'
            '<td style="padding:4px 6px;border-bottom:1px solid #eef2f8;text-align:right;">'
            '${amount}</td></tr>'.format(
                name=escape(l.product_id.name or l.name or ''),
                amount='%.2f' % l.price_subtotal)
            for l in order.order_line.filtered(lambda l: not l.display_type)
        )

        return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Verificación de Cotización — UEIPAB</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#f0f4fa;color:#1a1a1a;min-height:100vh;
display:flex;align-items:center;justify-content:center;padding:24px}}
.card{{background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(21,101,192,.14);
max-width:560px;width:100%;overflow:hidden}}
.card-header{{background:#1565c0;color:#fff;padding:20px 28px;text-align:center}}
.badge{{display:inline-block;background:#27ae60;color:#fff;font-size:13px;font-weight:700;
padding:5px 18px;border-radius:999px;margin-bottom:10px;letter-spacing:.5px}}
.card-header h1{{font-size:18px;font-weight:700;margin-bottom:2px}}
.card-header p{{font-size:12px;color:#bbdefb}}
.card-body{{padding:24px 28px}}
.check-icon{{text-align:center;font-size:52px;margin-bottom:12px}}
table.info{{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:14px}}
table.info td{{padding:7px 4px;border-bottom:1px solid #eef2f8}}
table.info td:first-child{{color:#555;width:46%}}
table.info td:last-child{{font-weight:600;color:#1565c0}}
.lines-section{{background:#f8faff;border-radius:8px;padding:12px 14px;margin-top:4px;font-size:13px}}
.lines-section h4{{font-size:12px;font-weight:700;color:#1565c0;letter-spacing:.5px;
text-transform:uppercase;margin-bottom:8px}}
.lines-table{{width:100%;border-collapse:collapse;font-size:12px}}
.lines-table td{{color:#2c3e50}}
.total-row td{{font-weight:700;color:#1565c0;border-top:2px solid #1565c0;padding-top:6px}}
.footer{{text-align:center;font-size:11px;color:#999;padding:14px 28px 20px;
border-top:1px solid #f0f0f0}}
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <div class="badge">✓ DOCUMENTO VÁLIDO</div>
    <h1>Instituto Privado Andrés Bello, C.A.</h1>
    <p>Verificación de Acuerdo de Inscripción (Cotización)</p>
  </div>
  <div class="card-body">
    <div class="check-icon">✅</div>
    <table class="info">
      <tr><td>Nro. de Cotización</td><td>{order_name}</td></tr>
      <tr><td>Representante</td><td>{partner_name}</td></tr>
      <tr><td>Estudiantes</td><td>{n_students}</td></tr>
      <tr><td>Fecha de emisión</td><td>{date_str}</td></tr>
      <tr><td>Válido hasta</td><td>{validity_str}</td></tr>
      <tr><td>Total USD</td><td>${amount}</td></tr>
      <tr><td>Estado</td><td style="color:{state_color};">{state_label}</td></tr>
    </table>
    <div class="lines-section">
      <h4>Detalle de conceptos</h4>
      <table class="lines-table">
        {line_rows}
        <tr class="total-row">
          <td style="padding:6px 6px 2px;">TOTAL</td>
          <td style="padding:6px 6px 2px;text-align:right;">${amount}</td>
        </tr>
      </table>
    </div>
  </div>
  <div class="footer">
    Verificación realizada el {now} · RIF J-080086171<br/>
    <a href="https://ueipab.edu.ve" style="color:#1565c0;">ueipab.edu.ve</a> ·
    <a href="mailto:pagos@ueipab.edu.ve" style="color:#1565c0;">pagos@ueipab.edu.ve</a>
  </div>
</div>
</body>
</html>""".format(order_name=order_name, partner_name=partner_name,
                  n_students=n_students, date_str=date_str,
                  validity_str=validity_str, amount=amount,
                  state_label=state_label, state_color=state_color,
                  line_rows=line_rows, now=now)

    def _render_invalid(self):
        return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Cotización No Encontrada — UEIPAB</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#f0f4fa;min-height:100vh;
display:flex;align-items:center;justify-content:center;padding:24px}}
.card{{background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(21,101,192,.14);
max-width:440px;width:100%;text-align:center;padding:40px 32px}}
.icon{{font-size:52px;margin-bottom:16px}}
h1{{font-size:20px;color:#1565c0;margin-bottom:8px}}
p{{color:#555;font-size:14px;line-height:1.6}}
a{{color:#1565c0}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">❌</div>
  <h1>Documento no encontrado</h1>
  <p>El código QR escaneado no corresponde a ninguna cotización válida.<br/>
  Contáctenos en <a href="mailto:pagos@ueipab.edu.ve">pagos@ueipab.edu.ve</a>.</p>
</div>
</body>
</html>"""
