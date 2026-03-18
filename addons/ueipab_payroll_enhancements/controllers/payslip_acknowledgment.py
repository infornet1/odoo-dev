# -*- coding: utf-8 -*-
"""
Payslip Acknowledgment Portal Controller

Provides secure portal endpoint for employees to acknowledge receipt of payslips.
Uses signed tokens to prevent tampering and records audit trail.
"""

from datetime import datetime

from odoo import http
from odoo.http import request


class PayslipAcknowledgmentController(http.Controller):
    """Controller for payslip acknowledgment portal pages."""

    def _render_html_page(self, title, content, status='success'):
        """Render a simple HTML response page."""
        color = '#28a745' if status == 'success' else '#dc3545' if status == 'error' else '#667eea'
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - UEIPAB</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 15px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .icon {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: {color};
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 40px;
            color: white;
        }}
        h1 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 24px;
        }}
        .content {{
            color: #666;
            line-height: 1.6;
        }}
        .btn {{
            display: inline-block;
            margin-top: 25px;
            padding: 12px 30px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            cursor: pointer;
        }}
        .btn:hover {{ opacity: 0.9; }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="footer">
            Instituto Educativo Privado Andrés Bello<br>
            recursoshumanos@ueipab.edu.ve
        </div>
    </div>
</body>
</html>
"""
        return html

    @http.route(
        '/payslip/acknowledge/<int:payslip_id>/<string:token>',
        type='http',
        auth='public',
        csrf=False
    )
    def payslip_acknowledge_page(self, payslip_id, token, **kw):
        """Display the payslip acknowledgment landing page."""
        try:
            # Find payslip with matching ID and token
            payslip = request.env['hr.payslip'].sudo().search([
                ('id', '=', payslip_id),
                ('access_token', '=', token)
            ], limit=1)

            if not payslip:
                content = '''
                    <div class="icon">❌</div>
                    <h1>Enlace Inválido</h1>
                    <div class="content">
                        <p>El enlace de confirmación no es válido o ha expirado.</p>
                        <p>Por favor contacte a Recursos Humanos.</p>
                    </div>
                '''
                return request.make_response(
                    self._render_html_page('Enlace Inválido', content, 'error'),
                    [('Content-Type', 'text/html')]
                )

            # Check if already acknowledged
            if payslip.is_acknowledged:
                ack_date = payslip.acknowledged_date.strftime('%d/%m/%Y a las %H:%M')
                content = f'''
                    <div class="icon">✅</div>
                    <h1>Ya Confirmado</h1>
                    <div class="content">
                        <p><strong>Comprobante:</strong> {payslip.number}</p>
                        <p><strong>Empleado:</strong> {payslip.employee_id.name}</p>
                        <p style="margin-top: 15px;">Este comprobante ya fue confirmado el</p>
                        <p><strong>{ack_date}</strong></p>
                    </div>
                '''
                return request.make_response(
                    self._render_html_page('Ya Confirmado', content, 'success'),
                    [('Content-Type', 'text/html')]
                )

            # Show confirmation form
            period = f"{payslip.date_from.strftime('%d/%m/%Y')} - {payslip.date_to.strftime('%d/%m/%Y')}"
            # Try NET lines first, then fallback to AGUINALDOS for Christmas bonus payslips
            net_line = payslip.line_ids.filtered(lambda l: l.code in ('NET', 'VE_NET_V2'))
            if net_line:
                net_amount = sum(net_line.mapped('total'))
            else:
                # Fallback for Aguinaldos payslips (no NET line)
                aguinaldo_line = payslip.line_ids.filtered(lambda l: l.code == 'AGUINALDOS')
                net_amount = sum(aguinaldo_line.mapped('total')) if aguinaldo_line else payslip.net_wage

            # Convert to VES using exchange rate from payslip
            exchange_rate = payslip.exchange_rate_used or 1.0
            net_amount_ves = net_amount * exchange_rate

            # Get db from request
            db_name = request.db or request.httprequest.args.get('db', '')

            content = f'''
                <div class="icon" style="background: #667eea;">📋</div>
                <h1>Confirmar Recepción Digital</h1>
                <div class="content">
                    <p><strong>Comprobante:</strong> {payslip.number}</p>
                    <p><strong>Empleado:</strong> {payslip.employee_id.name}</p>
                    <p><strong>Cédula:</strong> {payslip.employee_id.identification_id or '-'}</p>
                    <p><strong>Período:</strong> {period}</p>
                    <p><strong>Monto Neto:</strong> <span style="color: #28a745; font-weight: bold;">Bs. {net_amount_ves:,.2f}</span></p>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                    <p style="color: #666; font-size: 14px;">Al hacer click en el botón, confirma que ha recibido y revisado este comprobante de pago de forma digital.</p>
                </div>
                <form action="/payslip/acknowledge/{payslip_id}/{token}/confirm?db={db_name}" method="POST"
                      onsubmit="var btn=this.querySelector('button'); btn.disabled=true; btn.textContent='⏳ Procesando...';">
                    <button type="submit" class="btn">✅ Confirmar Recepción Digital</button>
                </form>
                <p style="margin-top: 15px; color: #999; font-size: 12px;">
                    🔒 Su confirmación quedará registrada con fecha, hora e IP
                </p>
            '''
            return request.make_response(
                self._render_html_page('Confirmar Recepción', content, 'info'),
                [('Content-Type', 'text/html')]
            )

        except Exception as e:
            content = f'''
                <div class="icon">❌</div>
                <h1>Error del Sistema</h1>
                <div class="content">
                    <p>Ocurrió un error al procesar su solicitud.</p>
                    <p>Por favor contacte a Recursos Humanos.</p>
                </div>
            '''
            return request.make_response(
                self._render_html_page('Error', content, 'error'),
                [('Content-Type', 'text/html')]
            )

    @http.route(
        '/payslip/acknowledge/<int:payslip_id>/<string:token>/confirm',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def payslip_acknowledge_confirm(self, payslip_id, token, **kw):
        """Process the acknowledgment confirmation."""
        try:
            # Find payslip with matching ID and token
            payslip = request.env['hr.payslip'].sudo().search([
                ('id', '=', payslip_id),
                ('access_token', '=', token)
            ], limit=1)

            if not payslip:
                content = '''
                    <div class="icon">❌</div>
                    <h1>Enlace Inválido</h1>
                    <div class="content">
                        <p>El enlace de confirmación no es válido o ha expirado.</p>
                    </div>
                '''
                return request.make_response(
                    self._render_html_page('Enlace Inválido', content, 'error'),
                    [('Content-Type', 'text/html')]
                )

            # Acquire a row-level lock before checking/writing is_acknowledged.
            # This serializes concurrent requests (e.g. double-click): the second
            # request blocks here until the first commits, then re-reads the
            # committed value and returns "Ya Confirmado" without sending a second email.
            request.env.cr.execute(
                "SELECT is_acknowledged FROM hr_payslip WHERE id = %s FOR UPDATE",
                (payslip.id,)
            )
            row = request.env.cr.fetchone()
            is_already_acked = row and row[0]

            # Check if already acknowledged
            if is_already_acked:
                payslip.invalidate_recordset()  # flush stale ORM cache, re-read from DB
                ack_date = payslip.acknowledged_date.strftime('%d/%m/%Y a las %H:%M')
                content = f'''
                    <div class="icon">✅</div>
                    <h1>Ya Confirmado</h1>
                    <div class="content">
                        <p>Este comprobante ya fue confirmado el</p>
                        <p><strong>{ack_date}</strong></p>
                    </div>
                '''
                return request.make_response(
                    self._render_html_page('Ya Confirmado', content, 'success'),
                    [('Content-Type', 'text/html')]
                )

            # Get request information for audit trail
            ip_address = request.httprequest.remote_addr or 'Unknown'
            user_agent = 'Unknown'
            if request.httprequest.user_agent:
                user_agent = request.httprequest.user_agent.string or 'Unknown'
            if len(user_agent) > 255:
                user_agent = user_agent[:255]

            # Record acknowledgment
            payslip.write({
                'is_acknowledged': True,
                'acknowledged_date': datetime.now(),
                'acknowledged_ip': ip_address,
                'acknowledged_user_agent': user_agent,
            })

            # Post message to payslip chatter
            payslip.message_post(
                body="✅ Comprobante de pago confirmado por el empleado.<br/>"
                     f"<b>IP:</b> {ip_address}<br/>"
                     f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )

            # Send confirmation email to employee (CC to HR)
            try:
                ack_template = request.env.ref(
                    'ueipab_payroll_enhancements.email_template_payslip_ack_confirmation',
                    raise_if_not_found=False
                )
                if ack_template:
                    ack_template.sudo().send_mail(payslip.id, force_send=True)
            except Exception:
                pass  # Don't block acknowledgment success page if email fails

            ack_date = datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')
            content = f'''
                <div class="icon">✅</div>
                <h1>¡Confirmación Exitosa!</h1>
                <div class="content">
                    <p>Su confirmación de recepción del comprobante de pago</p>
                    <p><strong>{payslip.number}</strong></p>
                    <p>ha sido registrada correctamente.</p>
                    <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                    <p><strong>Fecha de confirmación:</strong></p>
                    <p>{ack_date}</p>
                </div>
                <p style="margin-top: 20px; color: #999; font-size: 13px;">
                    Esta confirmación ha sido registrada en el sistema.<br>
                    Puede cerrar esta ventana.
                </p>
            '''
            return request.make_response(
                self._render_html_page('Confirmación Exitosa', content, 'success'),
                [('Content-Type', 'text/html')]
            )

        except Exception as e:
            content = f'''
                <div class="icon">❌</div>
                <h1>Error del Sistema</h1>
                <div class="content">
                    <p>Ocurrió un error al procesar su confirmación.</p>
                    <p>Por favor contacte a Recursos Humanos.</p>
                </div>
            '''
            return request.make_response(
                self._render_html_page('Error', content, 'error'),
                [('Content-Type', 'text/html')]
            )


class ArcAcknowledgmentController(http.Controller):
    """Controller for ARC annual certificate acknowledgment portal pages."""

    @http.route(
        '/arc/ack/init/<int:cert_id>/<string:token>',
        type='http', auth='none', csrf=False
    )
    def arc_ack_init(self, cert_id, token, **kw):
        """Set the session database and redirect to the real ack page.

        auth='none' so it is included in Odoo's nodb_routing_map (requires
        the module to be in server_wide_modules).  Uses the standard
        ensure_db() helper: on the first visit with no session it sets
        session.db from the ?db= query param and redirects back to the same
        URL; on the second visit (session.db is set) it falls through and
        redirects to the auth='public' confirmation page.
        """
        from odoo.addons.web.controllers.utils import ensure_db
        ensure_db()          # sets session.db from ?db= and self-redirects if needed
        db = request.session.db or ''
        redirect_url = '/arc/acknowledge/%d/%s?db=%s' % (cert_id, token, db)
        return request.redirect(redirect_url, code=302, local=True)

    @http.route(
        '/arc/acknowledge/<int:cert_id>/<string:token>',
        type='http', auth='public', csrf=False
    )
    def arc_acknowledge_page(self, cert_id, token, **kw):
        """Display the ARC acknowledgment landing page."""
        _render = PayslipAcknowledgmentController()._render_html_page

        try:
            cert = request.env['arc.employee.certificate'].sudo().search([
                ('id', '=', cert_id),
                ('access_token', '=', token),
            ], limit=1)

            if not cert:
                content = '''
                    <div class="icon">❌</div>
                    <h1>Enlace Inválido</h1>
                    <div class="content">
                        <p>El enlace no es válido o ha expirado.</p>
                        <p>Por favor contacte a Recursos Humanos.</p>
                    </div>'''
                return request.make_response(
                    _render('Enlace Inválido', content, 'error'),
                    [('Content-Type', 'text/html')]
                )

            if cert.is_acknowledged:
                ack_date = cert.acknowledged_date.strftime('%d/%m/%Y a las %H:%M')
                content = f'''
                    <div class="icon">✅</div>
                    <h1>Ya Confirmado</h1>
                    <div class="content">
                        <p><strong>Empleado:</strong> {cert.employee_id.name}</p>
                        <p><strong>Ejercicio Fiscal:</strong> {cert.year}</p>
                        <p style="margin-top:15px;">Este ARC ya fue confirmado el</p>
                        <p><strong>{ack_date}</strong></p>
                    </div>'''
                return request.make_response(
                    _render('Ya Confirmado', content, 'success'),
                    [('Content-Type', 'text/html')]
                )

            db_name = request.db or ''
            content = f'''
                <div class="icon" style="background:#1a237e;">📋</div>
                <h1>Confirmar Recepción del ARC</h1>
                <div class="content">
                    <p><strong>Empleado:</strong> {cert.employee_id.name}</p>
                    <p><strong>Cédula:</strong> {cert.employee_id.identification_id or '-'}</p>
                    <p><strong>Ejercicio Fiscal:</strong> {cert.year}</p>
                    <hr style="margin:20px 0;border:none;border-top:1px solid #eee;">
                    <p style="color:#666;font-size:14px;">
                        Al hacer click confirma que ha recibido el Comprobante de
                        Retenciones de ISLR (ARC) correspondiente al ejercicio fiscal {cert.year}.
                    </p>
                </div>
                <form action="/arc/acknowledge/{cert_id}/{token}/confirm?db={db_name}" method="POST"
                      onsubmit="var btn=this.querySelector('button'); btn.disabled=true; btn.textContent='⏳ Procesando...';">
                    <button type="submit" class="btn">✅ Confirmar Recepción del ARC</button>
                </form>
                <p style="margin-top:15px;color:#999;font-size:12px;">
                    🔒 Su confirmación quedará registrada con fecha, hora e IP
                </p>'''
            return request.make_response(
                _render('Confirmar Recepción ARC', content, 'info'),
                [('Content-Type', 'text/html')]
            )

        except Exception as e:
            content = f'''
                <div class="icon">❌</div>
                <h1>Error del Sistema</h1>
                <div class="content"><p>Ocurrió un error: {str(e)[:200]}</p></div>'''
            return request.make_response(
                _render('Error', content, 'error'),
                [('Content-Type', 'text/html')]
            )

    @http.route(
        '/arc/acknowledge/<int:cert_id>/<string:token>/confirm',
        type='http', auth='public', methods=['POST'], csrf=False
    )
    def arc_acknowledge_confirm(self, cert_id, token, **kw):
        """Record the ARC acknowledgment."""
        _render = PayslipAcknowledgmentController()._render_html_page

        try:
            cert = request.env['arc.employee.certificate'].sudo().search([
                ('id', '=', cert_id),
                ('access_token', '=', token),
            ], limit=1)

            if not cert:
                content = '''
                    <div class="icon">❌</div><h1>Enlace Inválido</h1>
                    <div class="content"><p>El enlace no es válido.</p></div>'''
                return request.make_response(
                    _render('Error', content, 'error'),
                    [('Content-Type', 'text/html')]
                )

            if not cert.is_acknowledged:
                ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR',
                     request.httprequest.environ.get('REMOTE_ADDR', ''))
                ua = request.httprequest.user_agent.string if request.httprequest.user_agent else ''
                cert.write({
                    'is_acknowledged': True,
                    'acknowledged_date': datetime.utcnow(),
                    'acknowledged_ip': ip[:100],
                    'acknowledged_user_agent': ua[:250],
                    'state': 'acknowledged',
                })
                # Stage 2: generate signed PDF (employer seal + digital ack block)
                # and email it to the employee. Also send the plain ack confirmation.
                try:
                    cert.sudo().action_send_final_pdf()
                except Exception:
                    pass  # PDF delivery failure must not block the portal response
                try:
                    tmpl = request.env.ref(
                        'ueipab_payroll_enhancements.email_template_arc_ack_confirmation',
                        raise_if_not_found=False,
                    )
                    if tmpl:
                        tmpl.sudo().send_mail(cert.id, force_send=True)
                except Exception:
                    pass  # confirmation email failure must not block the portal response

            content = f'''
                <div class="icon">✅</div>
                <h1>Recepción Confirmada</h1>
                <div class="content">
                    <p><strong>Empleado:</strong> {cert.employee_id.name}</p>
                    <p><strong>Ejercicio Fiscal:</strong> {cert.year}</p>
                    <p style="margin-top:15px;color:#28a745;font-weight:bold;">
                        Ha confirmado exitosamente la recepción de su Comprobante ARC.
                    </p>
                    <p style="margin-top:10px;color:#666;font-size:13px;">
                        Puede cerrar esta ventana.
                    </p>
                </div>'''
            return request.make_response(
                _render('Recepción Confirmada', content, 'success'),
                [('Content-Type', 'text/html')]
            )

        except Exception as e:
            content = f'''
                <div class="icon">❌</div><h1>Error</h1>
                <div class="content"><p>{str(e)[:200]}</p></div>'''
            return request.make_response(
                _render('Error', content, 'error'),
                [('Content-Type', 'text/html')]
            )
