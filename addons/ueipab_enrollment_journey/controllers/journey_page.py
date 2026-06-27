# -*- coding: utf-8 -*-
from markupsafe import escape

from odoo import fields, http
from odoo.http import request

from odoo.addons.ueipab_enrollment_journey.models.enrollment_journey import (
    STEP_DEFS, BLOCK_DEFS, DONE_STATES,
    _is_graduating_grade, _next_grade,
)

TELEGRAM_BOT = 'GlendaUeipabBot'


class EnrollmentJourneyPage(http.Controller):

    # ------------------------------------------------------------------
    # /verify-contract/<token>
    # ------------------------------------------------------------------

    @http.route('/verify-contract/<string:token>', type='http',
                auth='public', website=False, csrf=False)
    def verify_contract(self, token, **kw):
        j = request.env['enrollment.journey'].sudo().search(
            [('access_token', '=', token), ('active', '=', True)], limit=1)
        if not j:
            return request.make_response(
                self._render_invalid_contract(),
                headers=[('Content-Type', 'text/html; charset=utf-8')],
                status=404)
        return request.make_response(
            self._render_valid_contract(j),
            headers=[('Content-Type', 'text/html; charset=utf-8')])

    def _render_valid_contract(self, j):
        from datetime import datetime
        partner_name = escape(j.partner_id.name or '')
        contract_num = escape(j.contract_number or '—')
        date_str = j.contract_date.strftime('%d/%m/%Y') if j.contract_date else '—'
        n = len(j.student_ids) or '—'
        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        student_rows = ''.join(
            '<tr><td style="padding:3px 8px;">%s</td><td style="padding:3px 8px;color:#555;">%s</td></tr>' % (
                escape(s.name), escape(s.grade or ''))
            for s in j.student_ids
        ) or '<tr><td colspan="2" style="padding:3px 8px;color:#999;">%s estudiante(s) registrado(s)</td></tr>' % n
        return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Verificación de Contrato — UEIPAB</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#f0f4fa;color:#1a1a1a;min-height:100vh;
display:flex;align-items:center;justify-content:center;padding:24px}}
.card{{background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(26,44,91,.14);
max-width:520px;width:100%;overflow:hidden}}
.card-header{{background:#1a2c5b;color:#fff;padding:20px 28px;text-align:center}}
.card-header .badge{{display:inline-block;background:#27ae60;color:#fff;
font-size:13px;font-weight:700;padding:5px 18px;border-radius:999px;margin-bottom:10px;
letter-spacing:.5px}}
.card-header h1{{font-size:18px;font-weight:700;margin-bottom:2px}}
.card-header p{{font-size:12px;color:#cdd9ee}}
.card-body{{padding:24px 28px}}
.check-icon{{text-align:center;font-size:56px;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:12px}}
td{{padding:7px 4px;border-bottom:1px solid #eef2f8}}
td:first-child{{color:#555;width:46%;}}
td:last-child{{font-weight:600;color:#1a2c5b}}
.students-section{{background:#f8faff;border-radius:8px;padding:12px 14px;margin-top:8px;font-size:13px}}
.students-section h4{{font-size:12px;font-weight:700;color:#1a2c5b;letter-spacing:.5px;
text-transform:uppercase;margin-bottom:8px}}
.students-table td{{border-bottom:1px solid #e8edf5;font-weight:normal;color:#2c3e50}}
.footer{{text-align:center;font-size:11px;color:#999;padding:14px 28px 20px;border-top:1px solid #f0f0f0}}
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <div class="badge">✓ DOCUMENTO VÁLIDO</div>
    <h1>Instituto Privado Andrés Bello, C.A.</h1>
    <p>Verificación de Contrato de Servicio Educativo</p>
  </div>
  <div class="card-body">
    <div class="check-icon">✅</div>
    <table>
      <tr><td>Nro. de Contrato</td><td>{contract_num}</td></tr>
      <tr><td>Representante</td><td>{partner_name}</td></tr>
      <tr><td>Fecha del contrato</td><td>{date_str}</td></tr>
      <tr><td>Período escolar</td><td>2026 – 2027</td></tr>
      <tr><td>Estado</td><td style="color:#27ae60;">Vigente ✓</td></tr>
    </table>
    <div class="students-section">
      <h4>Estudiantes matriculados</h4>
      <table class="students-table">{student_rows}</table>
    </div>
  </div>
  <div class="footer">
    Verificación realizada el {now} · RIF J-080086171<br/>
    <a href="https://ueipab.edu.ve" style="color:#2471a3;">ueipab.edu.ve</a>
  </div>
</div>
</body>
</html>""".format(contract_num=contract_num, partner_name=partner_name,
                  date_str=date_str, student_rows=student_rows, now=now)

    def _render_invalid_contract(self):
        return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Contrato No Encontrado — UEIPAB</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#f0f4fa;min-height:100vh;
display:flex;align-items:center;justify-content:center;padding:24px}}
.card{{background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(26,44,91,.14);
max-width:480px;width:100%;text-align:center;padding:40px 32px}}
.icon{{font-size:52px;margin-bottom:16px}}
h1{{font-size:20px;color:#1a2c5b;margin-bottom:8px}}
p{{color:#555;font-size:14px;line-height:1.6}}
a{{color:#2471a3}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">❌</div>
  <h1>Documento no encontrado</h1>
  <p>El código QR escaneado no corresponde a ningún contrato válido en nuestros registros.<br/>
  Si cree que es un error, contáctenos en
  <a href="mailto:pagos@ueipab.edu.ve">pagos@ueipab.edu.ve</a>.</p>
</div>
</body>
</html>"""

    # ------------------------------------------------------------------
    # /enrollment-journey/<token>  GET  — branches on continuation_status
    # ------------------------------------------------------------------

    @http.route('/enrollment-journey/<string:token>', type='http',
                auth='public', website=False, csrf=False)
    def journey_page(self, token, **kw):
        journey = request.env['enrollment.journey'].sudo().search(
            [('access_token', '=', token), ('active', '=', True)], limit=1)
        if not journey:
            return request.not_found()

        status = journey.continuation_status
        if status == 'confirmed':
            html = self._render_wizard(journey)
        elif status == 'declined':
            html = self._render_declined(journey)
        else:  # pending
            html = self._render_step0(journey)

        return request.make_response(
            html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ------------------------------------------------------------------
    # POST /enrollment-journey/<token>/confirm
    # ------------------------------------------------------------------

    @http.route('/enrollment-journey/<string:token>/confirm', type='http',
                auth='public', website=False, csrf=False, methods=['POST'])
    def journey_confirm(self, token, **kw):
        journey = request.env['enrollment.journey'].sudo().search(
            [('access_token', '=', token), ('active', '=', True)], limit=1)
        if not journey:
            return request.not_found()
        if journey.continuation_status == 'pending':
            journey.write({
                'continuation_status': 'confirmed',
                'confirmation_date': fields.Datetime.now(),
            })
            journey._ensure_quote()
            journey._send_response_notification('confirmed')
        return request.redirect('/enrollment-journey/%s' % token)

    # ------------------------------------------------------------------
    # POST /enrollment-journey/<token>/decline
    # ------------------------------------------------------------------

    @http.route('/enrollment-journey/<string:token>/decline', type='http',
                auth='public', website=False, csrf=False, methods=['POST'])
    def journey_decline(self, token, **kw):
        journey = request.env['enrollment.journey'].sudo().search(
            [('access_token', '=', token), ('active', '=', True)], limit=1)
        if not journey:
            return request.not_found()
        if journey.continuation_status == 'pending':
            reason = (kw.get('reason') or '').strip()[:2000]
            journey.write({
                'continuation_status': 'declined',
                'decline_reason': reason or None,
                'decline_date': fields.Datetime.now(),
            })
            journey._send_response_notification('declined')
        return request.redirect('/enrollment-journey/%s' % token)

    # ------------------------------------------------------------------
    # GET /enrollment-journey/<token>/cotizacion.pdf
    # Public, token-scoped download of the family's draft quotation
    # (Acuerdo de Inscripción report) so the parent can review the
    # numbers before signing. No sale.order access is exposed — the
    # journey token is the only key.
    # ------------------------------------------------------------------

    @http.route('/enrollment-journey/<string:token>/cotizacion.pdf', type='http',
                auth='public', website=False, csrf=False)
    def journey_quote_pdf(self, token, **kw):
        journey = request.env['enrollment.journey'].sudo().search(
            [('access_token', '=', token), ('active', '=', True)], limit=1)
        if not journey or not journey.order_id:
            return request.not_found()
        pdf, _ftype = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'ueipab_sales.action_report_quotation_agreement', [journey.order_id.id])
        fname = 'Cotizacion_%s.pdf' % (
            (journey.partner_id.name or 'UEIPAB').replace(' ', '_'))
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'inline; filename="%s"' % fname),
        ])

    # ------------------------------------------------------------------
    # Step 0 page — pending
    # ------------------------------------------------------------------

    def _render_step0(self, j):
        partner_name = escape(j.partner_id.name or 'Representante')
        tg_link = 'https://t.me/%s?start=ENROLL_%s' % (TELEGRAM_BOT, j.access_token[:8])

        # Students excluding graduating 5° Año
        enrolling = [s for s in j.student_ids if not _is_graduating_grade(s.grade)]

        if not enrolling and not j.student_ids:
            # No students imported yet — holding screen
            return self._render_holding(j)

        if enrolling:
            student_items = ''.join(
                '<li class="student-item">'
                '<span class="s-name">%s</span>'
                '%s'
                '</li>' % (
                    escape(s.name),
                    ('<span class="s-grade">%s → %s</span>' % (
                        escape(s.grade), escape(_next_grade(s.grade)))
                    ) if s.grade else '',
                )
                for s in enrolling
            )
            question_html = f"""
<p class="question-lead">
  ¿Va(n) a continuar con nosotros el próximo año escolar
  <strong>2026-2027</strong>?
</p>
<ul class="student-list">{student_items}</ul>"""
        else:
            question_html = """
<p class="question-lead">
  ¿Su(s) representado(s) van a continuar con nosotros el próximo año escolar
  <strong>2026-2027</strong>?
</p>"""

        confirm_url = '/enrollment-journey/%s/confirm' % j.access_token

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Inscripción 2026-2027 — Confirmación — UEIPAB</title>
<meta name="robots" content="noindex"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--navy:#1a2c5b;--blue:#2471a3;--gold:#f0c400;--teal:#1fb8c0;--light:#f0f4fa;
--white:#fff;--text:#2c3e50;--muted:#5d7a9a;--green:#27ae60;--amber:#e67e22;--red:#c0392b}}
body{{font-family:'Poppins',Arial,sans-serif;background:var(--light);color:var(--text);
min-height:100vh;line-height:1.6}}
nav{{background:var(--navy);padding:0 24px;display:flex;align-items:center;
height:64px;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,.25)}}
.nav-brand{{display:flex;align-items:center;gap:12px;text-decoration:none}}
.nav-logo{{height:44px;width:44px;border-radius:50%;object-fit:cover;border:2px solid var(--gold)}}
.nav-name{{color:var(--white);font-weight:700;font-size:15px;line-height:1.2}}
.nav-name span{{display:block;font-weight:400;font-size:11px;color:var(--gold);letter-spacing:.5px}}
.hero{{background:linear-gradient(135deg,var(--navy) 0%,#0f1e3d 60%,#0a3a52 100%);
color:var(--white);padding:48px 24px 80px;text-align:center}}
.hero-badge{{display:inline-block;background:var(--gold);color:var(--navy);font-weight:700;
font-size:12px;letter-spacing:1px;padding:6px 18px;border-radius:999px;margin-bottom:16px}}
.hero h1{{font-size:clamp(22px,4vw,34px);font-weight:800;margin-bottom:8px}}
.hero p{{color:#cdd9ee;max-width:560px;margin:0 auto;font-size:14px}}
.wrap{{max-width:680px;margin:-40px auto 48px;padding:0 20px;position:relative;z-index:2}}
.card{{background:var(--white);border-radius:20px;box-shadow:0 8px 32px rgba(26,44,91,.13);
overflow:hidden}}
.card-body{{padding:32px 36px}}
.greeting{{font-size:16px;color:var(--navy);font-weight:600;margin-bottom:6px}}
.intro{{font-size:14px;color:var(--muted);line-height:1.7;margin-bottom:24px}}
.question-lead{{font-size:15px;color:var(--text);font-weight:500;margin-bottom:12px}}
.student-list{{list-style:none;padding:0;margin:0 0 28px;}}
.student-item{{display:flex;align-items:center;justify-content:space-between;
background:var(--light);border-radius:10px;padding:10px 16px;margin-bottom:8px;gap:12px}}
.s-name{{font-weight:600;color:var(--navy);font-size:14px}}
.s-grade{{font-size:12px;color:var(--muted);background:#dce6f5;
padding:3px 10px;border-radius:999px;white-space:nowrap}}
/* Buttons */
.btn-row{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:0}}
.btn-yes{{flex:1;min-width:140px;background:var(--green);color:#fff;font-family:inherit;
font-size:15px;font-weight:700;border:none;border-radius:12px;padding:15px 24px;
cursor:pointer;transition:background .2s;letter-spacing:.3px}}
.btn-yes:hover{{background:#1e8449}}
.btn-no{{flex:1;min-width:140px;background:var(--white);color:var(--red);font-family:inherit;
font-size:15px;font-weight:600;border:2px solid var(--red);border-radius:12px;padding:13px 24px;
cursor:pointer;transition:all .2s;letter-spacing:.3px}}
.btn-no:hover{{background:#fdf2f0}}
/* Decline section (hidden by default) */
.decline-section{{display:none;margin-top:24px;border-top:2px dashed #dce6f5;padding-top:24px}}
.decline-section.open{{display:block}}
.decline-msg{{font-size:13.5px;color:var(--text);line-height:1.8;margin-bottom:16px;
background:#fef9e7;border-left:3px solid var(--amber);padding:14px 16px;border-radius:0 10px 10px 0}}
.decline-msg strong{{color:var(--amber)}}
.solvencia-note{{font-size:12.5px;color:#7d5000;background:#fff8e6;
border:1px solid #f5cba7;border-radius:8px;padding:12px 14px;
margin:14px 0 16px;line-height:1.7}}
.decline-label{{font-size:13px;font-weight:600;color:var(--navy);margin-bottom:6px}}
.decline-textarea{{width:100%;min-height:100px;border:1.5px solid #dce6f5;border-radius:10px;
padding:12px 14px;font-family:inherit;font-size:13.5px;color:var(--text);resize:vertical;
transition:border-color .2s;outline:none}}
.decline-textarea:focus{{border-color:var(--blue)}}
.btn-decline-submit{{background:var(--red);color:#fff;font-family:inherit;font-size:14px;
font-weight:700;border:none;border-radius:10px;padding:13px 28px;cursor:pointer;
margin-top:12px;transition:background .2s}}
.btn-decline-submit:hover{{background:#a93226}}
/* Glenda */
.glenda-fab{{position:fixed;right:20px;bottom:20px;z-index:200;width:60px;height:60px;
border-radius:50%;background:linear-gradient(135deg,var(--teal),var(--blue));
display:flex;align-items:center;justify-content:center;font-size:28px;cursor:pointer;
box-shadow:0 6px 24px rgba(26,44,91,.35);border:3px solid var(--white);transition:transform .2s}}
.glenda-fab:hover{{transform:scale(1.08)}}
.glenda-card{{position:fixed;right:20px;bottom:92px;z-index:200;width:290px;
background:var(--white);border-radius:16px;box-shadow:0 12px 40px rgba(26,44,91,.3);
padding:20px;display:none}}
.glenda-card.open{{display:block;animation:up .25s ease}}
@keyframes up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
.glenda-card h4{{font-size:15px;color:var(--navy);margin-bottom:6px}}
.glenda-card p{{font-size:13px;color:var(--muted);margin-bottom:14px}}
.glenda-btn{{display:block;text-align:center;background:#229ED9;color:#fff;
font-weight:600;font-size:14px;padding:10px;border-radius:10px;text-decoration:none}}
footer{{text-align:center;font-size:12.5px;color:var(--muted);padding:24px;line-height:1.8}}
footer a{{color:var(--blue);text-decoration:none}}
@media(max-width:480px){{.card-body{{padding:24px 20px}}.btn-row{{flex-direction:column}}}}
</style>
</head>
<body>
<nav>
  <a class="nav-brand" href="https://ueipab.edu.ve">
    <img class="nav-logo" src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo" alt="UEIPAB"/>
    <div class="nav-name">U.E. Instituto Privado<span>ANDRÉS BELLO — EL TIGRE</span></div>
  </a>
</nav>
<div class="hero">
  <div class="hero-badge">INSCRIPCIÓN 2026-2027</div>
  <h1>ENCUESTA DE CONTINUIDAD PERÍODO ACADÉMICO 2026-2027</h1>
  <p>Antes de comenzar, necesitamos confirmar la continuidad de su familia para el próximo año escolar.</p>
</div>
<div class="wrap">
  <div class="card">
    <div class="card-body">
      <p class="greeting">Estimado/a Representante {partner_name},</p>
      <p class="intro">
        Estimado(a) representante, por favor, sírvase indicar a través de esta breve encuesta
        si sus representados(as) continuarán cursando estudios en éste plantel educativo en el
        próximo período académico <strong>2026-2027</strong>. Esta información es importante
        para nuestra planificación y gestión de un servicio educativo diferencial.
      </p>
      {question_html}
      <div class="btn-row">
        <form action="{confirm_url}" method="POST" style="flex:1;min-width:140px;">
          <button type="submit" class="btn-yes" style="width:100%;">
            ✓ &nbsp;Sí, continuamos
          </button>
        </form>
        <button type="button" class="btn-no" onclick="toggleDecline()" id="btn-no-toggle">
          ✕ &nbsp;No, no continuaremos
        </button>
      </div>

      <!-- Inline decline section (JS-toggled) -->
      <div class="decline-section" id="decline-section">
        <div class="decline-msg">
          Estimado/a Representante, ha sido un honor haber prestado los servicios educativos
          para su(s) representado(s) este año escolar 2025-2026 y los vamos a extrañar mucho
          en nuestra institución, independientemente de la razón por la cual lo llevó a usted
          a no seguir con nosotros. En este sentido, <strong>nos gustaría que nos comentara
          la razón de no continuidad:</strong>
        </div>
        <form action="/enrollment-journey/{j.access_token}/decline" method="POST">
          <div class="decline-label">Motivo (con sus propias palabras):</div>
          <textarea name="reason" class="decline-textarea"
                    placeholder="Escriba aquí el motivo por el cual su(s) hijo(s) no continuarán con nosotros..."></textarea>
          <div class="solvencia-note">
            📋 <strong>Recordatorio — Solvencia administrativa:</strong><br/>
            Para formalizar el retiro, usted debe contar con la solvencia administrativa
            correspondiente, que se obtiene con el pago total del año escolar 2025-2026
            en curso de las dos mensualidades pendientes correspondientes a los meses de
            <strong>julio y agosto</strong>.
          </div>
          <button type="submit" class="btn-decline-submit">Confirmar retiro →</button>
        </form>
      </div>

    </div>
  </div>
</div>
<footer>
  ¿Dudas? Escríbanos a <a href="mailto:soporte@ueipab.edu.ve">soporte@ueipab.edu.ve</a><br/>
  U.E. Instituto Privado Andrés Bello · El Tigre, Anzoátegui
</footer>
<div class="glenda-card" id="gcard">
  <h4>🤖 Hola, soy Glenda</h4>
  <p>Tu asistente de inscripción. Pregúntame lo que necesites sobre el proceso, tarifas o próximos pasos.</p>
  <a class="glenda-btn" href="{tg_link}" target="_blank">💬 Chatear por Telegram</a>
</div>
<div class="glenda-fab" onclick="document.getElementById('gcard').classList.toggle('open')">🤖</div>
<script>
function toggleDecline() {{
  var sec = document.getElementById('decline-section');
  var btn = document.getElementById('btn-no-toggle');
  var open = sec.classList.toggle('open');
  btn.textContent = open ? '← Volver atrás' : '✕  No, no continuaremos';
}}
</script>
</body>
</html>"""

    # ------------------------------------------------------------------
    # Holding screen — no students imported yet
    # ------------------------------------------------------------------

    def _render_holding(self, j):
        partner_name = escape(j.partner_id.name or 'Representante')
        tg_link = 'https://t.me/%s?start=ENROLL_%s' % (TELEGRAM_BOT, j.access_token[:8])
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Inscripción 2026-2027 — UEIPAB</title>
<meta name="robots" content="noindex"/>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Poppins',Arial,sans-serif;background:#f0f4fa;min-height:100vh;
display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px;color:#2c3e50}}
.card{{background:#fff;border-radius:20px;box-shadow:0 8px 32px rgba(26,44,91,.13);
max-width:520px;width:100%;padding:40px 36px;text-align:center}}
.logo{{width:72px;height:72px;border-radius:50%;border:3px solid #f0c400;margin-bottom:20px}}
h2{{font-size:20px;color:#1a2c5b;margin-bottom:10px}}
p{{font-size:14px;color:#5d7a9a;line-height:1.7}}
a{{color:#2471a3;text-decoration:none}}
</style>
</head>
<body>
<div class="card">
  <img class="logo" src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo" alt="UEIPAB"/>
  <h2>Estamos preparando su información</h2>
  <p>
    Estimado/a <strong>{partner_name}</strong>, su enlace de inscripción 2026-2027 ya está activo.<br/><br/>
    Nuestro equipo está cargando los datos de su familia. Por favor vuelva a intentarlo
    en unos minutos o contáctenos en
    <a href="mailto:soporte@ueipab.edu.ve">soporte@ueipab.edu.ve</a>
    si el problema persiste.
  </p>
</div>
</body>
</html>"""

    # ------------------------------------------------------------------
    # Declined page — read-only farewell
    # ------------------------------------------------------------------

    def _render_declined(self, j):
        partner_name = escape(j.partner_id.name or 'Representante')
        declined_at = j.decline_date
        dt_str = declined_at.strftime('%d/%m/%Y a las %H:%M') if declined_at else ''
        reason = escape(j.decline_reason or '') if j.decline_reason else None

        reason_block = ''
        if reason:
            reason_block = f"""
<div style="background:#f8faff;border:1px solid #dce6f5;border-radius:10px;
            padding:14px 16px;margin:16px 0;font-size:13.5px;color:#2c3e50;line-height:1.7;">
  <strong style="color:#5d7a9a;font-size:12px;text-transform:uppercase;letter-spacing:.5px;">
    Tu respuesta registrada{(' el ' + dt_str) if dt_str else ''}:
  </strong><br/><br/>
  {reason}
</div>"""

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Inscripción 2026-2027 — UEIPAB</title>
<meta name="robots" content="noindex"/>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Poppins',Arial,sans-serif;background:#f0f4fa;
min-height:100vh;display:flex;flex-direction:column;color:#2c3e50}}
nav{{background:#1a2c5b;padding:0 24px;display:flex;align-items:center;height:64px;
box-shadow:0 2px 12px rgba(0,0,0,.25)}}
.nav-brand{{display:flex;align-items:center;gap:12px;text-decoration:none}}
.nav-logo{{height:44px;width:44px;border-radius:50%;object-fit:cover;border:2px solid #f0c400}}
.nav-name{{color:#fff;font-weight:700;font-size:15px;line-height:1.2}}
.nav-name span{{display:block;font-weight:400;font-size:11px;color:#f0c400;letter-spacing:.5px}}
.wrap{{max-width:660px;margin:40px auto 48px;padding:0 20px;flex:1}}
.card{{background:#fff;border-radius:20px;box-shadow:0 8px 32px rgba(26,44,91,.13);padding:36px}}
.icon{{font-size:52px;text-align:center;margin-bottom:16px}}
h2{{font-size:20px;color:#1a2c5b;font-weight:700;margin-bottom:8px}}
.intro{{font-size:14px;color:#5d7a9a;line-height:1.7;margin-bottom:16px}}
.solvencia{{background:#fff8e6;border-left:4px solid #f0c400;padding:14px 16px;
border-radius:0 10px 10px 0;font-size:13px;color:#7d5000;line-height:1.7;margin:20px 0}}
.contact-note{{font-size:13px;color:#5d7a9a;margin-top:20px;line-height:1.7}}
.contact-note a{{color:#2471a3;text-decoration:none}}
footer{{text-align:center;font-size:12.5px;color:#5d7a9a;padding:24px;line-height:1.8}}
footer a{{color:#2471a3;text-decoration:none}}
</style>
</head>
<body>
<nav>
  <a class="nav-brand" href="https://ueipab.edu.ve">
    <img class="nav-logo" src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo" alt="UEIPAB"/>
    <div class="nav-name">U.E. Instituto Privado<span>ANDRÉS BELLO — EL TIGRE</span></div>
  </a>
</nav>
<div class="wrap">
  <div class="card">
    <div class="icon">🤝</div>
    <h2>Estimado/a Representante {partner_name},</h2>
    <p class="intro">
      Ha sido un honor haber prestado los servicios educativos para su(s) representado(s)
      este año escolar 2025-2026 y los vamos a extrañar mucho en nuestra institución,
      independientemente de la razón por la cual lo llevó a usted a no seguir con nosotros.
    </p>
    {reason_block}
    <div class="solvencia">
      📋 <strong>Recordatorio — Solvencia administrativa:</strong><br/>
      Para formalizar el retiro, usted debe contar con la solvencia administrativa
      correspondiente al pago total del año escolar 2025-2026 en curso de las dos
      mensualidades pendientes correspondientes a los meses de <strong>julio y agosto</strong>.
    </div>
    <p class="contact-note">
      Su respuesta ha sido registrada. Si cometió un error o cambió de opinión,
      contáctenos en
      <a href="mailto:soporte@ueipab.edu.ve">soporte@ueipab.edu.ve</a>
      y con gusto revisamos su caso.
    </p>
  </div>
</div>
<footer>
  ¿Dudas? <a href="mailto:soporte@ueipab.edu.ve">soporte@ueipab.edu.ve</a><br/>
  U.E. Instituto Privado Andrés Bello · El Tigre, Anzoátegui
</footer>
</body>
</html>"""

    # ------------------------------------------------------------------
    # 9-step wizard page — confirmed  (original _render, renamed)
    # ------------------------------------------------------------------

    def _render_wizard(self, j):
        partner_name = escape(j.partner_id.name or '')
        students = j.student_ids
        n_students = len(students) or (
            int(sum(l.product_uom_qty for l in j.order_id.order_line[:1])) if j.order_id else 0)

        student_chips = ''.join(
            '<span class="chip">🎓 %s%s</span>' % (
                escape(s.name), ' · %s' % escape(s.grade) if s.grade else '')
            for s in students
        ) or '<span class="chip">🎓 %d estudiante(s)</span>' % n_students

        step_data = {}
        for idx, (prefix, title, hint) in enumerate(STEP_DEFS, start=1):
            state = j[prefix + '_state']
            cleared_at = j[prefix + '_cleared_at']

            if state in DONE_STATES and idx == 3:
                if j.contract_retained:
                    step_data[idx] = dict(
                        cls='retained', icon='📋',
                        title=title,
                        meta='Contrato firmado — en custodia',
                        body=('<p class="step-hint retained-msg">'
                              'Tu contrato fue firmado y está en resguardo en nuestras instalaciones. '
                              'Se te entregará al completar el plan de pagos establecido.'
                              '</p>'),
                    )
                else:
                    rel_date = j.contract_released_date
                    meta = ('Contrato entregado · %s' % rel_date.strftime('%d/%m/%Y')) \
                        if rel_date else 'Contrato entregado'
                    step_data[idx] = dict(
                        cls='done', icon='✓',
                        title=title,
                        meta=meta,
                        body='<p class="step-hint">🎉 Tu contrato ha sido entregado. ¡Inscripción formal completa!</p>',
                    )
            elif state in DONE_STATES:
                meta = ('Completado · %s' % cleared_at.strftime('%d/%m/%Y')) if cleared_at else 'Completado'
                step_data[idx] = dict(cls='done', icon='✓', title=title, meta=meta, body='')
            elif idx == j.current_step:
                step_data[idx] = dict(
                    cls='current', icon=str(idx), title=title,
                    meta='Paso actual',
                    body='<p class="step-hint">%s</p>' % escape(hint),
                )
            elif state == 'blocked':
                step_data[idx] = dict(
                    cls='blocked', icon='!', title=title,
                    meta='En revisión por nuestro equipo', body='',
                )
            else:
                step_data[idx] = dict(
                    cls='pending', icon=str(idx), title=title,
                    meta='Próximamente', body='',
                )

        # Offer the parent a download of the draft quotation for review.
        # Available on step 1 as soon as the quote exists (auto-created on
        # S0 'Sí'), regardless of whether staff has cleared the step yet.
        if j.order_id:
            dl_btn = (
                '<a href="/enrollment-journey/%s/cotizacion.pdf" target="_blank" '
                'rel="noopener" style="display:inline-flex;align-items:center;gap:8px;'
                'margin-top:12px;padding:11px 18px;background:#2471a3;color:#fff;'
                'font-weight:600;font-size:14px;text-decoration:none;border-radius:10px;'
                'box-shadow:0 2px 6px rgba(36,113,163,.25);">'
                '📄 Descargar cotización (borrador) para revisión</a>'
                '<p style="font-size:12.5px;color:#5d7a9a;margin-top:8px;">'
                'Revise el detalle de su cotización <strong>%s</strong>. '
                'Es un documento preliminar para su revisión; '
                'la versión definitiva se firma en el paso 2.</p>'
            ) % (j.access_token, escape(j.order_id.name or ''))
            step_data[1]['body'] = (step_data[1].get('body') or '') + dl_btn

        sections = []
        for block_title, step_nums in BLOCK_DEFS:
            nodes = []
            for idx in step_nums:
                d = step_data[idx]
                badge = '<span class="badge-here">ESTÁS AQUÍ</span>' if d['cls'] == 'current' else ''
                nodes.append(f"""
            <div class="tl-item {d['cls']}">
              <div class="tl-dot">{d['icon']}</div>
              <div class="tl-card">
                <div class="tl-head"><h3>{idx}. {escape(d['title'])}</h3>{badge}</div>
                <div class="tl-meta">{d['meta']}</div>
                {d['body']}
              </div>
            </div>""")
            sections.append(f"""
          <div class="block-section">
            <div class="block-header">{escape(block_title)}</div>
            <div class="timeline">{''.join(nodes)}</div>
          </div>""")

        timeline_html = ''.join(sections)
        tg_link = f'https://t.me/{TELEGRAM_BOT}?start=ENROLL_{j.access_token[:8]}'

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Inscripción 2026-2027 — UEIPAB</title>
<meta name="robots" content="noindex"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--navy:#1a2c5b;--blue:#2471a3;--gold:#f0c400;--teal:#1fb8c0;--light:#f0f4fa;
--white:#fff;--text:#2c3e50;--muted:#5d7a9a;--green:#27ae60;--amber:#e67e22}}
body{{font-family:'Poppins',Arial,sans-serif;background:var(--light);color:var(--text);line-height:1.6}}
nav{{background:var(--navy);padding:0 24px;display:flex;align-items:center;justify-content:space-between;
height:64px;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,.25)}}
.nav-brand{{display:flex;align-items:center;gap:12px;text-decoration:none}}
.nav-logo{{height:44px;width:44px;border-radius:50%;object-fit:cover;border:2px solid var(--gold)}}
.nav-name{{color:var(--white);font-weight:700;font-size:15px;line-height:1.2}}
.nav-name span{{display:block;font-weight:400;font-size:11px;color:var(--gold);letter-spacing:.5px}}
.hero{{background:linear-gradient(135deg,var(--navy) 0%,#0f1e3d 60%,#0a3a52 100%);color:var(--white);
padding:48px 24px 96px;text-align:center;position:relative;overflow:hidden}}
.hero-badge{{display:inline-block;background:var(--gold);color:var(--navy);font-weight:700;font-size:12px;
letter-spacing:1px;padding:6px 18px;border-radius:999px;margin-bottom:16px}}
.hero h1{{font-size:clamp(24px,4vw,38px);font-weight:800;margin-bottom:8px}}
.hero p{{color:#cdd9ee;max-width:620px;margin:0 auto;font-size:15px}}
.wrap{{max-width:760px;margin:-56px auto 48px;padding:0 20px;position:relative;z-index:2}}
.family-card{{background:var(--white);border-radius:16px;box-shadow:0 8px 30px rgba(26,44,91,.12);
padding:24px 28px;margin-bottom:28px}}
.family-card h2{{font-size:18px;color:var(--navy);margin-bottom:4px}}
.family-card .yr{{font-size:13px;color:var(--muted);margin-bottom:12px}}
.chip{{display:inline-block;background:var(--light);border:1px solid #dce6f5;color:var(--navy);
font-size:13px;font-weight:500;border-radius:999px;padding:4px 14px;margin:3px 6px 3px 0}}
.progress-track{{background:#e4ebf7;border-radius:999px;height:10px;margin-top:14px;overflow:hidden}}
.progress-fill{{background:linear-gradient(90deg,var(--teal),var(--green));height:100%;border-radius:999px;
width:{j.progress_pct}%;transition:width .6s}}
.progress-label{{font-size:12px;color:var(--muted);margin-top:6px}}
.block-section{{margin-bottom:28px}}
.block-header{{font-size:13px;font-weight:700;color:var(--navy);letter-spacing:.5px;
text-transform:uppercase;padding:8px 4px 10px;border-bottom:2px solid #dce6f5;margin-bottom:16px}}
.timeline{{position:relative;padding-left:8px}}
.tl-item{{position:relative;display:flex;gap:18px;padding-bottom:20px}}
.tl-item::before{{content:'';position:absolute;left:21px;top:46px;bottom:0;width:3px;background:#d4deef}}
.tl-item:last-child::before{{display:none}}
.tl-item.done::before{{background:var(--green)}}
.tl-dot{{flex:0 0 44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-weight:700;font-size:16px;z-index:1;border:3px solid var(--white);box-shadow:0 2px 8px rgba(26,44,91,.18)}}
.done .tl-dot{{background:var(--green);color:#fff}}
.current .tl-dot{{background:var(--blue);color:#fff;animation:pulse 1.8s infinite}}
.pending .tl-dot{{background:#cfd9ea;color:#7589a8}}
.blocked .tl-dot{{background:var(--amber);color:#fff}}
.retained .tl-dot{{background:var(--amber);color:#fff;font-size:20px}}
@keyframes pulse{{0%{{box-shadow:0 0 0 0 rgba(36,113,163,.45)}}70%{{box-shadow:0 0 0 14px rgba(36,113,163,0)}}
100%{{box-shadow:0 0 0 0 rgba(36,113,163,0)}}}}
.tl-card{{flex:1;background:var(--white);border-radius:14px;padding:16px 20px;
box-shadow:0 4px 18px rgba(26,44,91,.08)}}
.current .tl-card{{border:2px solid var(--blue)}}
.retained .tl-card{{border:2px solid var(--amber)}}
.done .tl-card{{opacity:.92}}
.pending .tl-card{{opacity:.65}}
.tl-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}}
.tl-card h3{{font-size:15px;color:var(--navy)}}
.badge-here{{background:var(--blue);color:#fff;font-size:10px;font-weight:700;letter-spacing:1px;
padding:3px 10px;border-radius:999px}}
.tl-meta{{font-size:12px;color:var(--muted);margin-top:2px}}
.done .tl-meta{{color:var(--green);font-weight:500}}
.retained .tl-meta{{color:var(--amber);font-weight:500}}
.step-hint{{font-size:13.5px;margin-top:8px;color:var(--text)}}
.retained-msg{{font-size:13.5px;margin-top:8px;color:#7d5000;background:#fff8e6;
border-left:3px solid var(--amber);padding:8px 12px;border-radius:0 8px 8px 0}}
footer{{text-align:center;font-size:12.5px;color:var(--muted);padding:24px;line-height:1.8}}
footer a{{color:var(--blue);text-decoration:none}}
.glenda-fab{{position:fixed;right:20px;bottom:20px;z-index:200;width:64px;height:64px;border-radius:50%;
background:linear-gradient(135deg,var(--teal),var(--blue));display:flex;align-items:center;justify-content:center;
font-size:30px;cursor:pointer;box-shadow:0 6px 24px rgba(26,44,91,.35);border:3px solid var(--white);
transition:transform .2s}}
.glenda-fab:hover{{transform:scale(1.08)}}
.glenda-card{{position:fixed;right:20px;bottom:96px;z-index:200;width:300px;background:var(--white);
border-radius:16px;box-shadow:0 12px 40px rgba(26,44,91,.3);padding:20px;display:none}}
.glenda-card.open{{display:block;animation:up .25s ease}}
@keyframes up{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.glenda-card h4{{font-size:15px;color:var(--navy);margin-bottom:6px}}
.glenda-card p{{font-size:13px;color:var(--muted);margin-bottom:14px}}
.glenda-btn{{display:block;text-align:center;background:#229ED9;color:#fff;font-weight:600;font-size:14px;
padding:10px;border-radius:10px;text-decoration:none}}
</style>
</head>
<body>
<nav>
  <a class="nav-brand" href="https://ueipab.edu.ve">
    <img class="nav-logo" src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo" alt="UEIPAB"/>
    <div class="nav-name">U.E. Instituto Privado<span>ANDRÉS BELLO — EL TIGRE</span></div>
  </a>
</nav>
<div class="hero">
  <div class="hero-badge">INSCRIPCIÓN 2026-2027</div>
  <h1>Tu proceso de inscripción, paso a paso</h1>
  <p>Sigue aquí el avance de la inscripción de tu familia para el próximo año escolar.
     Nuestro equipo va confirmando cada paso — esta página se actualiza automáticamente.</p>
</div>
<div class="wrap">
  <div class="family-card">
    <h2>👨‍👩‍👧 Familia {partner_name}</h2>
    <div class="yr">Año escolar {escape(j.academic_year)}{' · ' + escape(j.order_id.name) if j.order_id else ''}</div>
    {student_chips}
    <div class="progress-track"><div class="progress-fill"></div></div>
    <div class="progress-label">{j.progress_pct}% completado — paso {j.current_step} de {len(STEP_DEFS)}</div>
  </div>
  {timeline_html}
</div>
<footer>
  ¿Dudas? Escríbenos a <a href="mailto:pagos@ueipab.edu.ve">pagos@ueipab.edu.ve</a>
  o <a href="mailto:soporte@ueipab.edu.ve">soporte@ueipab.edu.ve</a><br/>
  U.E. Instituto Privado Andrés Bello · El Tigre, Anzoátegui
</footer>
<div class="glenda-card" id="gcard">
  <h4>🤖 Hola, soy Glenda</h4>
  <p>Tu asistente de inscripción. Pregúntame lo que necesites sobre tu proceso, tarifas o próximos pasos.</p>
  <a class="glenda-btn" href="{tg_link}" target="_blank">💬 Chatear por Telegram</a>
</div>
<div class="glenda-fab" onclick="document.getElementById('gcard').classList.toggle('open')">🤖</div>
</body>
</html>"""
