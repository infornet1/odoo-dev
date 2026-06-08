import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

_LOGO_URL   = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
_RRHH_EMAIL = 'recursoshumanos@ueipab.edu.ve'
_FROM_EMAIL = 'soporte@ueipab.edu.ve'
_FROM_NAME  = 'Recursos Humanos - Colegio Andrés Bello'

_MONTHS_ES = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
              'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
_DAYS_ES   = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def _fmt_date(d):
    if not d:
        return '—'
    day_name = _DAYS_ES[d.weekday()]
    return f"{day_name.capitalize()}, {d.day} de {_MONTHS_ES[d.month]} de {d.year}"


class RecruitmentJobPreviewController(http.Controller):

    @http.route('/recruitment/job/<int:job_id>', type='http', auth='public', website=False)
    def job_preview(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or not job.description:
            return _not_found()
        html = _build_page(job)
        return Response(html, content_type='text/html; charset=utf-8')

    @http.route('/recruitment/confirm/<string:token>', type='http', auth='public', website=False)
    def confirm_eval(self, token, **kwargs):
        applicant = request.env['hr.applicant'].sudo().search(
            [('ueipab_eval_invite_token', '=', token)], limit=1
        )
        if not applicant:
            return _not_found()

        if applicant.ueipab_eval_confirmed:
            return Response(
                _already_confirmed_page(applicant),
                content_type='text/html; charset=utf-8',
            )

        _send_confirmation_email(request.env, applicant)
        applicant.write({'ueipab_eval_confirmed': True, 'ueipab_eval_state': 'confirmed'})

        return Response(
            _confirmed_page(applicant),
            content_type='text/html; charset=utf-8',
        )


# ── Confirmation email ─────────────────────────────────────────────────────────

def _send_confirmation_email(env, applicant):
    name        = (applicant.partner_name or 'Candidato/a').upper()
    first_name  = name.split()[0]
    job         = applicant.job_id.name if applicant.job_id else '—'
    date_str    = _fmt_date(applicant.ueipab_eval_appointment_date)
    time_str    = applicant.ueipab_eval_appointment_time or '—'
    address     = applicant.ueipab_eval_appointment_addr or '—'
    to_email    = applicant.email_from or ''

    if not to_email:
        _logger.warning("confirm_eval: applicant %s has no email, skipping confirmation email", applicant.id)
        return

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:20px 0;">
<tr><td align="center">
<div style="max-width:580px;margin:0 auto;background:#ffffff;border-radius:8px;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

  <div style="background:linear-gradient(135deg,#1a6b3a,#0d4a24);
              padding:32px 24px;text-align:center;color:#ffffff;">
    <img src="{_LOGO_URL}" width="64" height="64"
         style="border-radius:50%;border:3px solid rgba(255,255,255,.3);
                display:block;margin:0 auto 12px;object-fit:cover;">
    <h1 style="margin:0 0 4px;font-size:22px;font-weight:700;">✅ Asistencia Confirmada</h1>
    <p style="margin:0;font-size:13px;opacity:.85;">U.E.I.P.A.B. — Recursos Humanos</p>
  </div>

  <div style="padding:28px 32px;">
    <p style="margin:0 0 16px;font-size:14px;color:#333;">
      Estimado/a <strong>{first_name}</strong>,
    </p>
    <p style="margin:0 0 20px;font-size:14px;color:#555;line-height:1.6;">
      Hemos recibido su confirmación de asistencia a la evaluación técnica presencial.
      Le esperamos en la fecha indicada. A continuación el resumen de su cita:
    </p>

    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;margin-bottom:24px;font-size:14px;">
      <tr>
        <td style="padding:10px 12px;background:#f8f9fa;border-radius:6px 6px 0 0;
                   color:#555;width:40%;font-weight:600;">👤 Candidato</td>
        <td style="padding:10px 12px;background:#f8f9fa;color:#222;">{name}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;color:#555;font-weight:600;">💼 Cargo</td>
        <td style="padding:10px 12px;color:#222;">{job}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;background:#f8f9fa;color:#555;font-weight:600;">📅 Fecha</td>
        <td style="padding:10px 12px;background:#f8f9fa;color:#1a6b3a;font-weight:700;">{date_str}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;color:#555;font-weight:600;">⏰ Hora</td>
        <td style="padding:10px 12px;color:#1a6b3a;font-weight:700;">{time_str}</td>
      </tr>
      <tr>
        <td style="padding:10px 12px;background:#f8f9fa;color:#555;font-weight:600;">📍 Dirección</td>
        <td style="padding:10px 12px;background:#f8f9fa;color:#222;">{address}</td>
      </tr>
    </table>

    <div style="background:#fff8e1;border-left:4px solid #f0ad4e;border-radius:4px;
                padding:14px 16px;margin-bottom:20px;">
      <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#856404;">📌 Recuerde traer:</p>
      <ul style="margin:0;padding-left:18px;font-size:13px;color:#555;line-height:1.8;">
        <li>Cédula de identidad <strong>original</strong></li>
        <li>Presentarse <strong>5 minutos antes</strong> de la hora indicada</li>
      </ul>
    </div>

    <p style="margin:0;font-size:13px;color:#555;line-height:1.6;">
      Si tiene alguna pregunta o necesita realizar un cambio de horario,
      responda a este correo o contáctenos en
      <a href="mailto:{_RRHH_EMAIL}" style="color:#1a73e8;">{_RRHH_EMAIL}</a>.
    </p>
  </div>

  <div style="background:#f8f9fa;padding:14px 24px;text-align:center;border-top:1px solid #eee;">
    <p style="margin:0;font-size:11px;color:#aaa;">
      Mensaje de U.E.I.P.A.B. — Consultas: {_RRHH_EMAIL}
    </p>
  </div>

</div>
</td></tr>
</table>
</body>
</html>"""

    mail = env['mail.mail'].sudo().create({
        'subject':    f'✅ Asistencia Confirmada — {job} | UEIPAB',
        'email_to':   to_email,
        'email_from': f'"{_FROM_NAME}" <{_FROM_EMAIL}>',
        'reply_to':   _RRHH_EMAIL,
        'email_cc':   _RRHH_EMAIL,
        'body_html':  html,
        'state':      'outgoing',
    })
    _logger.info(
        "Eval confirmation email queued: mail.mail id=%s to=%s applicant=%s",
        mail.id, to_email, applicant.id,
    )
    try:
        env['ir.cron'].sudo().browse(3).method_direct_trigger()
    except Exception:
        _logger.warning("confirm_eval: could not trigger mail queue cron", exc_info=True)


# ── Confirmation pages ─────────────────────────────────────────────────────────

def _confirmed_page(applicant):
    name      = (applicant.partner_name or 'Candidato/a').upper()
    job       = applicant.job_id.name if applicant.job_id else '—'
    date_str  = _fmt_date(applicant.ueipab_eval_appointment_date)
    time_str  = applicant.ueipab_eval_appointment_time or '—'
    address   = applicant.ueipab_eval_appointment_addr or '—'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Asistencia Confirmada — Colegio Andrés Bello</title>
  <meta name="robots" content="noindex, nofollow"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:'Poppins',Arial,sans-serif;background:#f0f4fa;color:#2c3e50;min-height:100vh;
         display:flex;flex-direction:column;}}
    nav{{background:#1a2c5b;padding:0 24px;display:flex;align-items:center;height:64px;
         box-shadow:0 2px 12px rgba(0,0,0,.25);}}
    .nav-brand{{display:flex;align-items:center;gap:12px;text-decoration:none;}}
    .nav-logo{{height:44px;width:44px;border-radius:50%;object-fit:cover;border:2px solid #f0c400;}}
    .nav-name{{color:#fff;font-weight:700;font-size:15px;line-height:1.2;}}
    .nav-name span{{display:block;font-weight:400;font-size:11px;color:#f0c400;letter-spacing:.5px;}}
    main{{flex:1;display:flex;align-items:center;justify-content:center;padding:48px 24px;}}
    .card{{background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(26,44,91,.10);
           max-width:520px;width:100%;overflow:hidden;}}
    .card-top{{background:linear-gradient(135deg,#1a6b3a,#0d4a24);padding:40px 32px;
               text-align:center;color:#fff;}}
    .check-circle{{width:72px;height:72px;background:rgba(255,255,255,.15);border-radius:50%;
                   display:flex;align-items:center;justify-content:center;font-size:36px;
                   margin:0 auto 16px;border:3px solid rgba(255,255,255,.3);}}
    .card-top h1{{font-size:22px;font-weight:800;margin-bottom:6px;}}
    .card-top p{{font-size:13px;opacity:.8;}}
    .card-body{{padding:28px 32px;}}
    .detail-row{{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #f0f4fa;
                 font-size:13.5px;}}
    .detail-row:last-child{{border-bottom:none;}}
    .detail-label{{color:#5d7a9a;font-weight:500;min-width:90px;flex-shrink:0;}}
    .detail-value{{color:#1a2c5b;font-weight:600;}}
    .note-box{{background:#f0faf4;border-left:4px solid #1a6b3a;border-radius:4px;
               padding:12px 16px;margin-top:20px;font-size:13px;color:#1a6b3a;line-height:1.6;}}
    footer{{background:#0d1a35;color:rgba(255,255,255,.5);text-align:center;padding:20px;
            font-size:12px;}}
    footer a{{color:#f0c400;text-decoration:none;}}
  </style>
</head>
<body>
<nav>
  <a href="https://www.ueipab.edu.ve" class="nav-brand" target="_blank" rel="noopener">
    <img src="{_LOGO_URL}" alt="Logo Colegio Andrés Bello" class="nav-logo"/>
    <div class="nav-name">Colegio Andrés Bello<span>El Tigre, Anzoátegui</span></div>
  </a>
</nav>
<main>
  <div class="card">
    <div class="card-top">
      <div class="check-circle">✅</div>
      <h1>¡Asistencia Confirmada!</h1>
      <p>Su confirmación ha sido registrada exitosamente.</p>
    </div>
    <div class="card-body">
      <div class="detail-row">
        <span class="detail-label">👤 Candidato</span>
        <span class="detail-value">{name}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">💼 Cargo</span>
        <span class="detail-value">{job}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">📅 Fecha</span>
        <span class="detail-value">{date_str}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">⏰ Hora</span>
        <span class="detail-value">{time_str}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">📍 Dirección</span>
        <span class="detail-value">{address}</span>
      </div>
      <div class="note-box">
        Recibirá una copia de confirmación en su correo electrónico. Si necesita hacer
        algún cambio, escríbanos a
        <strong>{_RRHH_EMAIL}</strong>.
      </div>
    </div>
  </div>
</main>
<footer>
  <p>Instituto Privado Andrés Bello &mdash; El Tigre, Anzoátegui, Venezuela</p>
  <p style="margin-top:6px;"><a href="https://www.ueipab.edu.ve">www.ueipab.edu.ve</a></p>
</footer>
</body>
</html>"""


def _already_confirmed_page(applicant):
    job = applicant.job_id.name if applicant.job_id else '—'
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Ya Confirmado — Colegio Andrés Bello</title>
  <meta name="robots" content="noindex, nofollow"/>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet"/>
  <style>
    body{{font-family:'Poppins',Arial,sans-serif;background:#f0f4fa;display:flex;
         flex-direction:column;min-height:100vh;margin:0;}}
    nav{{background:#1a2c5b;height:64px;display:flex;align-items:center;padding:0 24px;}}
    .nav-logo{{height:44px;width:44px;border-radius:50%;border:2px solid #f0c400;object-fit:cover;}}
    main{{flex:1;display:flex;align-items:center;justify-content:center;padding:48px 24px;}}
    .card{{background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(26,44,91,.10);
           max-width:440px;width:100%;padding:40px 32px;text-align:center;}}
    .icon{{font-size:52px;margin-bottom:16px;}}
    h1{{font-size:20px;font-weight:700;color:#1a2c5b;margin-bottom:10px;}}
    p{{font-size:13.5px;color:#5d7a9a;line-height:1.7;}}
    a{{color:#1a73e8;}}
  </style>
</head>
<body>
<nav><img src="{_LOGO_URL}" alt="Logo" class="nav-logo"/></nav>
<main>
  <div class="card">
    <div class="icon">✅</div>
    <h1>Ya registramos su confirmación</h1>
    <p>
      Su asistencia para el cargo de <strong>{job}</strong> ya fue confirmada anteriormente.<br><br>
      Si necesita realizar algún cambio, por favor escríbanos a
      <a href="mailto:{_RRHH_EMAIL}">{_RRHH_EMAIL}</a>.
    </p>
  </div>
</main>
</body>
</html>"""


# ── Page builder ──────────────────────────────────────────────────────────────

def _not_found():
    return Response("""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>No encontrado — Colegio Andrés Bello</title></head>
<body style="font-family:Arial,sans-serif;text-align:center;padding:80px 24px;background:#f0f4fa;">
  <img src="/web/image/res.company/1/logo" width="64" height="64"
       style="border-radius:50%;border:3px solid #1a2c5b;margin-bottom:24px;display:block;margin-left:auto;margin-right:auto;">
  <h2 style="color:#1a2c5b;font-size:22px;margin-bottom:12px;">Enlace no encontrado</h2>
  <p style="color:#5d7a9a;font-size:14px;">Esta oferta laboral ya no está disponible o el enlace es incorrecto.</p>
</body></html>""", content_type='text/html; charset=utf-8', status=404)


def _build_page(job):
    title      = job.name or 'Oferta Laboral'
    dept       = job.department_id.name if job.department_id else 'Administración'
    vacantes   = job.no_of_recruitment or 1
    desc_html  = str(job.description or '')

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} — Colegio Andrés Bello</title>
  <meta name="robots" content="noindex, nofollow"/>
  <meta name="description" content="Descripción del cargo {title} en el Colegio Andrés Bello, El Tigre, Anzoátegui."/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --navy:  #1a2c5b;
      --blue:  #2471a3;
      --gold:  #f0c400;
      --teal:  #1fb8c0;
      --light: #f0f4fa;
      --white: #ffffff;
      --text:  #2c3e50;
      --muted: #5d7a9a;
    }}

    body {{
      font-family: 'Poppins', Arial, sans-serif;
      background: var(--light);
      color: var(--text);
      line-height: 1.6;
    }}

    /* ── NAV ── */
    nav {{
      background: var(--navy);
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 2px 12px rgba(0,0,0,.25);
    }}
    .nav-brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
    }}
    .nav-logo {{
      height: 44px; width: 44px;
      border-radius: 50%;
      object-fit: cover;
      border: 2px solid var(--gold);
    }}
    .nav-name {{
      color: var(--white);
      font-weight: 700;
      font-size: 15px;
      line-height: 1.2;
    }}
    .nav-name span {{
      display: block;
      font-weight: 400;
      font-size: 11px;
      color: var(--gold);
      letter-spacing: .5px;
    }}
    .nav-back {{
      color: var(--gold);
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
      opacity: .85;
      transition: opacity .2s;
    }}
    .nav-back:hover {{ opacity: 1; }}

    /* ── HERO ── */
    .hero {{
      background: linear-gradient(135deg, var(--navy) 0%, #0f1e3d 60%, #0a3a52 100%);
      color: var(--white);
      padding: 64px 24px 56px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}
    .hero::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    }}
    .hero-badge {{
      display: inline-block;
      background: var(--gold);
      color: var(--navy);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      padding: 4px 14px;
      border-radius: 20px;
      margin-bottom: 18px;
    }}
    .hero h1 {{
      font-size: clamp(22px, 4.5vw, 38px);
      font-weight: 800;
      line-height: 1.2;
      margin-bottom: 14px;
    }}
    .hero h1 em {{
      font-style: normal;
      color: var(--gold);
    }}
    .hero p {{
      font-size: 15px;
      color: rgba(255,255,255,.75);
      max-width: 520px;
      margin: 0 auto;
    }}

    /* ── SECTIONS ── */
    .section {{ max-width: 860px; margin: 0 auto; padding: 48px 24px; }}

    /* ── CHIPS ROW ── */
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      justify-content: center;
      padding: 32px 24px 0;
      max-width: 860px;
      margin: 0 auto;
    }}
    .chip {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--white);
      border-radius: 24px;
      padding: 8px 18px;
      font-size: 13px;
      font-weight: 600;
      color: var(--navy);
      box-shadow: 0 2px 8px rgba(26,44,91,.10);
    }}
    .chip .chip-icon {{ font-size: 16px; }}
    .chip .chip-label {{ font-size: 11px; font-weight: 400; color: var(--muted); margin-right: 4px; }}

    /* ── DESCRIPTION CARD ── */
    .card {{
      background: var(--white);
      border-radius: 14px;
      padding: 32px 36px;
      box-shadow: 0 2px 12px rgba(26,44,91,.08);
    }}
    .card-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 28px;
      padding-bottom: 16px;
      border-bottom: 2px solid var(--light);
    }}
    .card-header h2 {{
      font-size: 17px;
      font-weight: 700;
      color: var(--navy);
    }}
    .card-header-icon {{
      width: 36px; height: 36px;
      border-radius: 8px;
      background: var(--light);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }}

    /* Description content */
    .desc-content h3 {{
      font-size: 15px;
      font-weight: 700;
      color: var(--navy);
      margin: 28px 0 10px;
      padding-left: 12px;
      border-left: 4px solid var(--blue);
      line-height: 1.4;
    }}
    .desc-content h3:first-child {{ margin-top: 0; }}
    .desc-content p {{
      font-size: 13.5px;
      color: var(--text);
      line-height: 1.75;
      margin-bottom: 12px;
    }}
    .desc-content ul {{
      margin: 0 0 16px 0;
      padding-left: 0;
      list-style: none;
    }}
    .desc-content ul li {{
      font-size: 13.5px;
      color: var(--text);
      padding: 7px 0 7px 22px;
      position: relative;
      border-bottom: 1px solid #f0f4fa;
      line-height: 1.6;
    }}
    .desc-content ul li:last-child {{ border-bottom: none; }}
    .desc-content ul li::before {{
      content: '▸';
      position: absolute;
      left: 0;
      color: var(--blue);
      font-weight: bold;
      font-size: 12px;
      top: 9px;
    }}
    .desc-content strong {{ color: var(--navy); font-weight: 600; }}

    /* ── CTA SECTION ── */
    .cta-section {{
      background: linear-gradient(135deg, var(--navy), #0f1e3d);
      border-radius: 14px;
      padding: 36px 32px;
      text-align: center;
      color: var(--white);
      margin-top: 24px;
    }}
    .cta-section h3 {{
      font-size: 19px;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .cta-section p {{
      font-size: 13px;
      color: rgba(255,255,255,.7);
      margin-bottom: 24px;
      max-width: 480px;
      margin-left: auto;
      margin-right: auto;
    }}
    .email-card {{
      display: inline-flex;
      align-items: center;
      gap: 14px;
      background: rgba(255,255,255,.08);
      border: 1px solid rgba(255,255,255,.18);
      border-radius: 10px;
      padding: 14px 20px;
      max-width: 100%;
    }}
    .email-addr {{
      font-size: 15px;
      font-weight: 700;
      color: var(--gold);
      letter-spacing: .3px;
      word-break: break-all;
    }}
    .copy-btn {{
      flex-shrink: 0;
      background: var(--gold);
      color: var(--navy);
      border: none;
      border-radius: 6px;
      padding: 7px 14px;
      font-family: 'Poppins', Arial, sans-serif;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity .2s;
      white-space: nowrap;
    }}
    .copy-btn:hover {{ opacity: .85; }}
    .copy-hint {{
      font-size: 12px;
      color: rgba(255,255,255,.45);
      margin-top: 14px;
    }}

    /* ── DIVIDER ── */
    .divider {{ height: 4px; background: linear-gradient(90deg, var(--navy), var(--blue), var(--teal)); }}

    /* ── FOOTER ── */
    footer {{
      background: #0d1a35;
      color: rgba(255,255,255,.5);
      text-align: center;
      padding: 24px;
      font-size: 12px;
    }}
    footer a {{ color: var(--gold); text-decoration: none; }}

    @media (max-width: 600px) {{
      .card {{ padding: 24px 20px; }}
      .chips {{ padding-top: 24px; gap: 8px; }}
    }}
  </style>
</head>
<body>

<!-- NAV -->
<nav>
  <a href="https://www.ueipab.edu.ve" class="nav-brand" target="_blank" rel="noopener">
    <img src="{_LOGO_URL}" alt="Logo Colegio Andrés Bello" class="nav-logo"/>
    <div class="nav-name">
      Colegio Andrés Bello
      <span>El Tigre, Anzoátegui</span>
    </div>
  </a>
  <a href="https://www.ueipab.edu.ve" class="nav-back" target="_blank" rel="noopener">
    ← Volver al sitio web
  </a>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="hero-badge">Oferta Laboral</div>
  <h1>{title}</h1>
  <p>Colegio Andrés Bello &mdash; El Tigre, Anzoátegui, Venezuela</p>
</section>

<!-- CHIPS -->
<div class="chips">
  <div class="chip">
    <span class="chip-icon">💼</span>
    <span><span class="chip-label">Cargo</span>{title}</span>
  </div>
  <div class="chip">
    <span class="chip-icon">🏢</span>
    <span><span class="chip-label">Área</span>{dept}</span>
  </div>
  <div class="chip">
    <span class="chip-icon">📍</span>
    <span><span class="chip-label">Sede</span>El Tigre, Anzoátegui</span>
  </div>
  <div class="chip">
    <span class="chip-icon">🗓️</span>
    <span><span class="chip-label">Vacantes</span>{vacantes}</span>
  </div>
  <div class="chip">
    <span class="chip-icon">⏱️</span>
    <span><span class="chip-label">Modalidad</span>Tiempo completo</span>
  </div>
</div>

<!-- DESCRIPTION -->
<div class="section">
  <div class="card">
    <div class="card-header">
      <div class="card-header-icon">📋</div>
      <h2>Descripción del Cargo</h2>
    </div>
    <div class="desc-content">
      {desc_html}
    </div>
  </div>

  <!-- CTA -->
  <div class="cta-section">
    <h3>¿Te interesa este cargo?</h3>
    <p>Escríbenos directamente desde tu correo favorito —<br>Gmail, Outlook, o cualquier cliente que uses.</p>
    <div class="email-card">
      <span class="email-addr" id="rrhh-email">{_RRHH_EMAIL}</span>
      <button class="copy-btn" onclick="copyEmail()">Copiar</button>
    </div>
    <p class="copy-hint">Adjunta tu CV e indica el cargo al que te postulas</p>
  </div>
</div>

<div class="divider"></div>
<footer>
  <p>Instituto Privado Andrés Bello &mdash; El Tigre, Municipio Simón Rodríguez, Anzoátegui, Venezuela</p>
  <p style="margin-top:6px;">
    <a href="https://www.ueipab.edu.ve">www.ueipab.edu.ve</a>
    &nbsp;|&nbsp;
    <a href="mailto:{_RRHH_EMAIL}">{_RRHH_EMAIL}</a>
  </p>
</footer>

<script>
function copyEmail() {{
  var email = document.getElementById('rrhh-email').textContent;
  navigator.clipboard.writeText(email).then(function() {{
    var btn = document.querySelector('.copy-btn');
    btn.textContent = '✓ Copiado';
    btn.style.background = '#1fb8c0';
    setTimeout(function() {{
      btn.textContent = 'Copiar';
      btn.style.background = '';
    }}, 2000);
  }}).catch(function() {{
    window.prompt('Copia esta dirección:', email);
  }});
}}
</script>
</body>
</html>"""
