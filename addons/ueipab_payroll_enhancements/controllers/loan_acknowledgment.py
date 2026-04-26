# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request


class LoanAcknowledgmentController(http.Controller):
    """Portal endpoint for employees to acknowledge salary advance receipt."""

    # ── shared HTML renderer (same style as payslip ack) ──────────────────

    def _page(self, title, body, status='success'):
        color = {'success': '#28a745', 'error': '#dc3545', 'info': '#1a2c5b'}[status]
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} – UEIPAB</title>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#1a2c5b,#2471a3);
         min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
    .card{{background:#fff;border-radius:12px;padding:40px;max-width:560px;width:100%;
           box-shadow:0 10px 40px rgba(0,0,0,.2);text-align:center}}
    .icon{{width:72px;height:72px;border-radius:50%;background:{color};display:flex;
           align-items:center;justify-content:center;margin:0 auto 18px;
           font-size:36px;color:#fff}}
    h1{{color:#1a2c5b;margin-bottom:12px;font-size:22px}}
    .info{{background:#f0f4fa;border-radius:8px;padding:16px;margin:18px 0;text-align:left;
           font-size:14px;color:#333;line-height:1.7}}
    .info strong{{color:#1a2c5b}}
    .table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}}
    .table th{{background:#1a2c5b;color:#fff;padding:8px;text-align:left}}
    .table td{{padding:7px 8px;border-bottom:1px solid #e0e0e0}}
    .btn{{display:inline-block;margin-top:22px;padding:14px 36px;background:#28a745;
          color:#fff;text-decoration:none;border-radius:8px;font-size:16px;font-weight:600;
          border:none;cursor:pointer;width:100%}}
    .btn:hover{{opacity:.92}}
    .legal{{background:#f8f9fa;border:1px solid #dee2e6;border-radius:6px;padding:14px;
            margin:18px 0;font-size:12px;color:#555;text-align:left;line-height:1.6}}
    .footer{{margin-top:24px;padding-top:16px;border-top:1px solid #eee;
             color:#999;font-size:12px}}
  </style>
</head>
<body>
  <div class="card">
    {body}
    <div class="footer">Instituto Privado Andrés Bello &bull; recursoshumanos@ueipab.edu.ve</div>
  </div>
</body>
</html>"""

    # ── confirmation email ─────────────────────────────────────────────────

    def _send_ack_confirmation_email(self, loan):
        """Send confirmation email to employee + CC to HR after ack is registered."""
        emp_email = loan.employee_id.work_email
        if not emp_email:
            return

        bs_total = loan.advance_bs_amount or (
            loan.loan_amount * (loan.advance_exchange_rate or 1.0))
        rate = loan.advance_exchange_rate or 0.0
        ack_date = loan.loan_acknowledged_date.strftime('%d/%m/%Y a las %H:%M')
        ack_ip = loan.loan_acknowledged_ip or 'N/A'

        subject = '✅ Conformidad Registrada – Adelanto de Salario │ %s' % loan.name

        body_html = f'''
<div style="font-family:'Segoe UI',sans-serif;background:#f4f4f4;padding:20px">
  <div style="max-width:600px;margin:0 auto;background:white;border-radius:10px;
              box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden">

    <div style="background:linear-gradient(135deg,#1a2c5b,#2471a3);color:white;
                padding:24px;text-align:center">
      <h1 style="margin:0;font-size:22px">✅ Conformidad Registrada</h1>
      <p style="margin:6px 0 0;font-size:14px;opacity:.9">Adelanto de Salario</p>
    </div>

    <div style="padding:28px">
      <p style="font-size:15px;color:#333;margin-bottom:20px">
        Estimado/a <strong>{loan.employee_id.name}</strong>,
      </p>
      <p style="font-size:14px;color:#555;line-height:1.6;margin-bottom:22px">
        Hemos registrado su conformidad digital con el adelanto de salario
        indicado a continuación.
      </p>

      <div style="background:#f0f4fa;border-radius:8px;padding:18px;margin-bottom:22px">
        <div style="display:flex;justify-content:space-between;padding:6px 0;
                    border-bottom:1px solid #d0dce8">
          <span style="font-weight:600;color:#1a2c5b;font-size:13px">📋 Nro. Adelanto:</span>
          <span style="color:#333;font-size:13px">{loan.name}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:6px 0;
                    border-bottom:1px solid #d0dce8">
          <span style="font-weight:600;color:#1a2c5b;font-size:13px">💰 Monto:</span>
          <span style="color:#333;font-size:13px">Bs. {bs_total:,.2f}</span>
        </div>
        {'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #d0dce8"><span style="font-weight:600;color:#1a2c5b;font-size:13px">Tasa de Cambio:</span><span style="color:#333;font-size:13px">Bs. ' + f'{rate:,.4f}' + '</span></div>' if rate else ''}
        <div style="display:flex;justify-content:space-between;padding:6px 0;
                    border-bottom:1px solid #d0dce8">
          <span style="font-weight:600;color:#1a2c5b;font-size:13px">📅 Fecha confirmación:</span>
          <span style="color:#333;font-size:13px">{ack_date}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:6px 0">
          <span style="font-weight:600;color:#1a2c5b;font-size:13px">🌐 IP registrada:</span>
          <span style="color:#333;font-size:13px">{ack_ip}</span>
        </div>
      </div>

      <div style="background:#d4edda;border-left:4px solid #28a745;padding:14px 18px;
                  border-radius:4px;margin-bottom:22px">
        <p style="font-size:13px;color:#155724;margin:0">
          Su conformidad digital ha quedado registrada con fecha, hora e IP.
          El descuento será aplicado a su nómina según el plan de recuperación acordado.
        </p>
      </div>

      <div style="background:#e8f4f8;border-left:4px solid #2471a3;padding:14px 18px;
                  border-radius:4px">
        <p style="font-size:13px;color:#1a2c5b;margin:0 0 4px">
          <strong>¿Dudas o consultas?</strong>
        </p>
        <p style="font-size:13px;color:#555;margin:0">
          Escriba a
          <a href="mailto:recursoshumanos@ueipab.edu.ve"
             style="color:#2471a3">recursoshumanos@ueipab.edu.ve</a>
        </p>
      </div>
    </div>

    <div style="background:#f8f9fa;padding:14px 28px;border-top:1px solid #e0e0e0;
                text-align:center;font-size:12px;color:#888">
      Instituto Privado Andrés Bello &#8226;
      <strong style="color:#1a2c5b">recursoshumanos@ueipab.edu.ve</strong>
    </div>
  </div>
</div>'''

        request.env['mail.mail'].sudo().create({
            'subject': subject,
            'email_from': '"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>',
            'email_to': emp_email,
            'email_cc': 'recursoshumanos@ueipab.edu.ve',
            'body_html': body_html,
            'auto_delete': True,
        }).send()

    # ── GET: landing page ──────────────────────────────────────────────────

    @http.route(
        '/loan/acknowledge/<int:loan_id>/<string:token>',
        type='http', auth='public', csrf=False, methods=['GET', 'POST']
    )
    def loan_acknowledge(self, loan_id, token, **kw):
        loan = request.env['hr.loan'].sudo().search(
            [('id', '=', loan_id), ('loan_ack_token', '=', token)], limit=1)

        if not loan:
            body = '''
              <div class="icon">❌</div>
              <h1>Enlace Inválido</h1>
              <div class="info">
                <p>Este enlace de confirmación no es válido o ha expirado.</p>
                <p>Por favor contacte a Recursos Humanos.</p>
              </div>'''
            return request.make_response(
                self._page('Enlace Inválido', body, 'error'),
                [('Content-Type', 'text/html')])

        # ── POST: process confirmation ─────────────────────────────────────
        if request.httprequest.method == 'POST':
            first_ack = not loan.loan_is_acknowledged
            if first_ack:
                loan.write({
                    'loan_is_acknowledged': True,
                    'loan_acknowledged_date': fields.Datetime.now(),
                    'loan_acknowledged_ip': request.httprequest.remote_addr,
                })
                self._send_ack_confirmation_email(loan)

            ack_date = loan.loan_acknowledged_date.strftime('%d/%m/%Y a las %H:%M')
            bs_total = loan.advance_bs_amount or (loan.loan_amount * (loan.advance_exchange_rate or 1.0))
            body = f'''
              <div class="icon">✅</div>
              <h1>¡Confirmación Registrada!</h1>
              <div class="info">
                <p><strong>Empleado:</strong> {loan.employee_id.name}</p>
                <p><strong>Nro. Adelanto:</strong> {loan.name}</p>
                <p><strong>Monto:</strong> Bs. {bs_total:,.2f}</p>
                <p><strong>Fecha confirmación:</strong> {ack_date}</p>
              </div>
              <p style="color:#555;font-size:14px">
                Su confirmación ha sido registrada correctamente.<br>
                El descuento será aplicado según el plan de recuperación acordado.
              </p>'''
            return request.make_response(
                self._page('Confirmación Registrada', body, 'success'),
                [('Content-Type', 'text/html')])

        # ── GET: show landing page ─────────────────────────────────────────
        if loan.loan_is_acknowledged:
            ack_date = loan.loan_acknowledged_date.strftime('%d/%m/%Y a las %H:%M')
            body = f'''
              <div class="icon">✅</div>
              <h1>Ya Confirmado</h1>
              <div class="info">
                <p><strong>Empleado:</strong> {loan.employee_id.name}</p>
                <p><strong>Nro. Adelanto:</strong> {loan.name}</p>
                <p>Este adelanto ya fue confirmado el <strong>{ack_date}</strong></p>
              </div>'''
            return request.make_response(
                self._page('Ya Confirmado', body, 'success'),
                [('Content-Type', 'text/html')])

        # Compute Bs amount (primary) and rate reference
        bs_total = loan.advance_bs_amount or (loan.loan_amount * (loan.advance_exchange_rate or 1.0))
        rate = loan.advance_exchange_rate or 0.0

        # Build repayment schedule rows (amounts in Bs)
        schedule_rows = ''.join(
            f'<tr><td>{i+1}</td>'
            f'<td>{line.date.strftime("%d/%m/%Y") if line.date else ""}</td>'
            f'<td>Bs. {line.amount * rate:,.2f}</td>'
            f'<td>{"✅" if line.paid else "⏳"}</td></tr>'
            for i, line in enumerate(loan.loan_lines)
        )

        rate_display = (
            f'<div style="background:#fff9e6;border:2px dashed #ffc107;border-radius:6px;'
            f'padding:10px;margin:10px 0;text-align:center;font-size:13px;color:#856404">'
            f'Tasa de Cambio Aplicada (Referencia): '
            f'<strong>Bs. {rate:,.4f}</strong>'
            f'</div>'
        ) if rate else ''

        body = f'''
          <div class="icon">💰</div>
          <h1>Confirmación de Adelanto de Salario</h1>
          <div class="info">
            <p><strong>Empleado:</strong> {loan.employee_id.name}</p>
            <p><strong>Cédula:</strong> {loan.employee_id.identification_id or "N/A"}</p>
            <p><strong>Nro. Adelanto:</strong> {loan.name}</p>
            <p><strong>Monto:</strong> Bs. {bs_total:,.2f}</p>
          </div>
          {rate_display}
          <table class="table">
            <thead><tr><th>#</th><th>Fecha</th><th>Monto</th><th>Estado</th></tr></thead>
            <tbody>{schedule_rows}</tbody>
          </table>
          <div class="legal">
            El suscrito trabajador declara haber recibido de la
            <strong>UNIDAD EDUCATIVA INSTITUTO PRIVADO ANDRES BELLO, CA</strong>
            la cantidad de <strong>Bs. {bs_total:,.2f}</strong>
            por concepto de <strong>ADELANTO DE SALARIO</strong>, el cual será
            descontado de su nómina según el plan de recuperación indicado.
          </div>
          <form method="POST"
                action="/loan/acknowledge/{loan_id}/{token}">
            <button type="submit" class="btn">
              ✅ Confirmar Recepción del Adelanto
            </button>
          </form>'''

        return request.make_response(
            self._page('Confirmar Adelanto de Salario', body, 'info'),
            [('Content-Type', 'text/html')])
