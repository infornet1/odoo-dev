import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

_LOGO_URL = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
_RRHH_EMAIL = 'recursoshumanos@ueipab.edu.ve'


class RecruitmentJobPreviewController(http.Controller):

    @http.route('/recruitment/job/<int:job_id>', type='http', auth='public', website=False)
    def job_preview(self, job_id, **kwargs):
        job = request.env['hr.job'].sudo().browse(job_id)
        if not job.exists() or not job.description:
            return _not_found()
        html = _build_page(job)
        return Response(html, content_type='text/html; charset=utf-8')


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
    mailto     = (
        f"mailto:{_RRHH_EMAIL}"
        f"?subject=Postulación%20para%20{title.replace(' ', '%20')}"
        f"&body=Estimado%20equipo%20de%20RRHH%2C%0A%0AMi%20nombre%20es%20[Nombre%20completo]%20y%20deseo%20postularme%20al%20cargo%20de%20{title.replace(' ', '%20')}."
    )

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
    .cta-btn {{
      display: inline-block;
      background: var(--gold);
      color: var(--navy);
      font-family: 'Poppins', Arial, sans-serif;
      font-size: 14px;
      font-weight: 700;
      padding: 13px 32px;
      border-radius: 8px;
      text-decoration: none;
      transition: opacity .2s;
    }}
    .cta-btn:hover {{ opacity: .88; }}

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
    <p>Envíanos tu CV y carta de presentación al correo de Recursos Humanos. Revisamos cada postulación con atención.</p>
    <a href="{mailto}" class="cta-btn">✉ Postularme ahora</a>
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

</body>
</html>"""
