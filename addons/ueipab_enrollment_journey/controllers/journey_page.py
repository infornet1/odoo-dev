# -*- coding: utf-8 -*-
from markupsafe import escape

from odoo import http
from odoo.http import request

from odoo.addons.ueipab_enrollment_journey.models.enrollment_journey import (
    STEP_DEFS, DONE_STATES,
)

TELEGRAM_BOT = 'GlendaUeipabBot'


class EnrollmentJourneyPage(http.Controller):

    @http.route('/enrollment-journey/<string:token>', type='http',
                auth='public', website=False, csrf=False)
    def journey_page(self, token, **kw):
        journey = request.env['enrollment.journey'].sudo().search(
            [('access_token', '=', token), ('active', '=', True)], limit=1)
        if not journey:
            return request.not_found()
        return request.make_response(
            self._render(journey),
            headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ------------------------------------------------------------------
    def _render(self, j):
        partner_name = escape(j.partner_id.name or '')
        students = j.student_ids
        n_students = len(students) or (
            int(sum(l.product_uom_qty for l in j.order_id.order_line[:1])) if j.order_id else 0)

        # student chips
        student_chips = ''.join(
            '<span class="chip">🎓 %s%s</span>' % (
                escape(s.name), ' · %s' % escape(s.grade) if s.grade else '')
            for s in students
        ) or '<span class="chip">🎓 %d estudiante(s)</span>' % n_students

        # timeline nodes
        nodes = []
        current_done = True
        for idx, (prefix, title, hint) in enumerate(STEP_DEFS, start=1):
            state = j[prefix + '_state']
            cleared_at = j[prefix + '_cleared_at']
            if state in DONE_STATES:
                cls, icon = 'done', '✓'
                meta = ('Completado · %s' % cleared_at.strftime('%d/%m/%Y')) if cleared_at else 'Completado'
                body = ''
            elif idx == j.current_step:
                cls, icon = 'current', str(idx)
                meta = 'Paso actual'
                body = '<p class="step-hint">%s</p>' % escape(hint)
            elif state == 'blocked':
                cls, icon = 'blocked', '!'
                meta = 'En revisión por nuestro equipo'
                body = ''
            else:
                cls, icon = 'pending', str(idx)
                meta = 'Próximamente'
                body = ''
            badge = '<span class="badge-here">ESTÁS AQUÍ</span>' if cls == 'current' else ''
            nodes.append(f"""
            <div class="tl-item {cls}">
              <div class="tl-dot">{icon}</div>
              <div class="tl-card">
                <div class="tl-head"><h3>{idx}. {escape(title)}</h3>{badge}</div>
                <div class="tl-meta">{meta}</div>
                {body}
              </div>
            </div>""")

        timeline = ''.join(nodes)
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
.timeline{{position:relative;padding-left:8px}}
.tl-item{{position:relative;display:flex;gap:18px;padding-bottom:26px}}
.tl-item::before{{content:'';position:absolute;left:21px;top:46px;bottom:0;width:3px;background:#d4deef}}
.tl-item:last-child::before{{display:none}}
.tl-item.done::before{{background:var(--green)}}
.tl-dot{{flex:0 0 44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-weight:700;font-size:16px;z-index:1;border:3px solid var(--white);box-shadow:0 2px 8px rgba(26,44,91,.18)}}
.done .tl-dot{{background:var(--green);color:#fff}}
.current .tl-dot{{background:var(--blue);color:#fff;animation:pulse 1.8s infinite}}
.pending .tl-dot{{background:#cfd9ea;color:#7589a8}}
.blocked .tl-dot{{background:var(--amber);color:#fff}}
@keyframes pulse{{0%{{box-shadow:0 0 0 0 rgba(36,113,163,.45)}}70%{{box-shadow:0 0 0 14px rgba(36,113,163,0)}}
100%{{box-shadow:0 0 0 0 rgba(36,113,163,0)}}}}
.tl-card{{flex:1;background:var(--white);border-radius:14px;padding:16px 20px;
box-shadow:0 4px 18px rgba(26,44,91,.08)}}
.current .tl-card{{border:2px solid var(--blue)}}
.done .tl-card{{opacity:.92}}
.pending .tl-card{{opacity:.65}}
.tl-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}}
.tl-card h3{{font-size:15px;color:var(--navy)}}
.badge-here{{background:var(--blue);color:#fff;font-size:10px;font-weight:700;letter-spacing:1px;
padding:3px 10px;border-radius:999px}}
.tl-meta{{font-size:12px;color:var(--muted);margin-top:2px}}
.done .tl-meta{{color:var(--green);font-weight:500}}
.step-hint{{font-size:13.5px;margin-top:8px;color:var(--text)}}
footer{{text-align:center;font-size:12.5px;color:var(--muted);padding:24px;line-height:1.8}}
footer a{{color:var(--blue);text-decoration:none}}
/* Glenda bubble */
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
    <div class="progress-label">{j.progress_pct}% completado — paso {j.current_step} de 6</div>
  </div>
  <div class="timeline">{timeline}</div>
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
