# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

NOTICE_KEY = 'attendance_guide_2026_v1'
LOGO_URL   = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'


class AttendanceGuideController(http.Controller):

    @http.route('/attendance-guide/<string:token>', type='http', auth='public', website=False)
    def attendance_guide(self, token, **kwargs):
        Ack = request.env['hr.notice.acknowledgment'].sudo()
        ack = Ack.search([('token', '=', token), ('notice_key', '=', NOTICE_KEY)], limit=1)
        if not ack:
            return Response(_page_not_found(), content_type='text/html; charset=utf-8', status=404)

        base     = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://odoo.ueipab.edu.ve')
        ack_url  = base + '/notice-ack/' + ack.token
        emp_name = ack.employee_id.name or 'Estimado/a trabajador/a'
        already  = ack.state == 'acknowledged'

        html = _build_page(emp_name, ack_url, already)
        return Response(html, content_type='text/html; charset=utf-8')


def _page_not_found():
    return """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"/>
<title>Enlace inválido</title></head>
<body style="font-family:Arial,sans-serif;text-align:center;padding:60px;background:#f0f4f8;">
<h2 style="color:#1a2c5b;">Enlace no válido</h2>
<p style="color:#64748b;">Este enlace ya no existe o ha expirado.</p>
</body></html>"""


def _build_page(emp_name, ack_url, already=False):
    first_name = emp_name.split()[0].capitalize() if emp_name else 'Estimado/a'
    ack_section = _ack_already_done() if already else _ack_pending(ack_url)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Guía de Control de Asistencia | Colegio Andrés Bello</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;}}
    .wrap{{max-width:660px;margin:28px auto;border-radius:14px;overflow:hidden;
           box-shadow:0 6px 32px rgba(0,0,0,.13);}}
    .hdr{{background:linear-gradient(135deg,#1a2c5b,#2471a3);padding:32px 36px 24px;text-align:center;}}
    .logo{{width:70px;height:70px;border-radius:50%;border:3px solid rgba(255,255,255,.3);
           display:block;margin:0 auto 12px;object-fit:cover;}}
    .hdr-title{{font-size:22px;font-weight:800;color:#fff;margin-bottom:6px;line-height:1.3;}}
    .hdr-sub{{font-size:13px;color:rgba(255,255,255,.8);}}
    .sec{{padding:24px 36px;}}
    .sec.alt{{background:#f8faff;}}
    .sec.white{{background:#fff;}}
    .sec-title{{font-size:14px;font-weight:800;color:#1a2c5b;text-transform:uppercase;
                letter-spacing:1px;border-bottom:2px solid #2471a3;padding-bottom:7px;margin-bottom:16px;}}
    .prose{{font-size:13px;color:#374151;line-height:1.75;margin-bottom:12px;}}
    .steps-grid{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:4px;}}
    .step-card{{flex:1;min-width:110px;background:#fff;border:1px solid #dde3ee;border-radius:10px;padding:14px 10px;text-align:center;}}
    .step-num{{width:32px;height:32px;background:#1a2c5b;border-radius:50%;color:#fff;
               font-size:14px;font-weight:800;line-height:32px;margin:0 auto 8px;}}
    .step-label{{font-size:11px;font-weight:700;color:#1a2c5b;margin-bottom:4px;}}
    .step-desc{{font-size:10px;color:#64748b;line-height:1.45;}}
    .case-card{{border-radius:8px;padding:16px 18px;margin-bottom:12px;}}
    .case-card.blue{{background:#f0f6ff;border-left:4px solid #2471a3;}}
    .case-card.amber{{background:#fffbf0;border-left:4px solid #f0ad4e;}}
    .case-card.green{{background:#f0fdf4;border-left:4px solid #28a745;}}
    .case-title{{font-size:13px;font-weight:700;margin-bottom:8px;}}
    .case-title.blue{{color:#1a2c5b;}}
    .case-title.amber{{color:#7b5800;}}
    .case-title.green{{color:#155724;}}
    .case-body{{font-size:12px;color:#444;line-height:1.7;}}
    .tips-box{{background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:16px 20px;}}
    .tips-title{{font-size:13px;font-weight:700;color:#7b5800;margin-bottom:10px;}}
    .tips-list{{padding-left:16px;font-size:12px;color:#555;line-height:1.9;}}
    .ack-box{{background:linear-gradient(135deg,#052e16,#14532d);border-radius:12px;
              padding:26px;text-align:center;margin:0 36px 28px;}}
    .ack-eyebrow{{font-size:11px;font-weight:700;color:#86efac;letter-spacing:2px;
                  text-transform:uppercase;margin-bottom:8px;}}
    .ack-title{{font-size:17px;font-weight:800;color:#fff;margin-bottom:10px;}}
    .ack-desc{{font-size:12px;color:#bbf7d0;line-height:1.7;margin-bottom:18px;}}
    .btn-ack{{display:inline-block;background:#28a745;color:#fff;text-decoration:none;
              font-size:15px;font-weight:800;padding:13px 44px;border-radius:50px;}}
    .ack-note{{font-size:10px;color:#4ade80;margin-top:12px;}}
    .done-box{{background:#f0fdf4;border:2px solid #28a745;border-radius:12px;
               padding:26px;text-align:center;margin:0 36px 28px;}}
    .done-icon{{font-size:42px;margin-bottom:10px;}}
    .done-title{{font-size:17px;font-weight:800;color:#15803d;margin-bottom:8px;}}
    .done-desc{{font-size:13px;color:#374151;line-height:1.6;}}
    .ftr{{background:#1a2c5b;padding:20px 36px;text-align:center;}}
    .ftr-name{{font-size:12px;font-weight:700;color:#adc8e6;margin-bottom:3px;}}
    .ftr-email{{font-size:11px;color:#4b6080;text-decoration:none;}}
    @media(max-width:500px){{
      .sec,.hdr,.ack-box,.done-box,.ftr{{padding-left:18px;padding-right:18px;}}
      .steps-grid{{flex-direction:column;}}
    }}
  </style>
</head>
<body>
<div class="wrap">

  <!-- HEADER -->
  <div class="hdr">
    <img class="logo" src="{LOGO_URL}" alt="UEIPAB" width="70" height="70"/>
    <p class="hdr-title">Guía de Control de Asistencia</p>
    <p class="hdr-sub">U.E.I.P.A.B. · Recursos Humanos · 2026</p>
  </div>

  <!-- INTRO -->
  <div class="sec white">
    <p class="prose">Hola <strong>{first_name}</strong>, esta guía te explica cómo funciona
    el sistema de registro de asistencia, para qué sirve — y sobre todo,
    <strong>cómo te protege a ti</strong>.</p>
  </div>

  <!-- HOW IT WORKS -->
  <div class="sec alt">
    <p class="sec-title">¿Cómo funciona el sistema?</p>
    <div class="steps-grid">
      <div class="step-card">
        <div class="step-num">1</div>
        <p class="step-label">Registra</p>
        <p class="step-desc">Kiosco de la Administración (principal) o menú lateral de Odoo — Check In/Out</p>
      </div>
      <div class="step-card">
        <div class="step-num">2</div>
        <p class="step-label">Aviso inteligente</p>
        <p class="step-desc">El sistema cruza múltiples señales — solo recibirás aviso cuando no haya evidencia suficiente de asistencia</p>
      </div>
      <div class="step-card">
        <div class="step-num">3</div>
        <p class="step-label">Corrección</p>
        <p class="step-desc">El correo tiene un botón "📝 Solicitar Corrección" — RRHH revisa antes del cierre</p>
      </div>
      <div class="step-card">
        <div class="step-num">4</div>
        <p class="step-label">Reporte</p>
        <p class="step-desc">Cada quincena recibes tu resumen completo para verificarlo antes de nómina</p>
      </div>
    </div>
  </div>

  <!-- SCENARIOS -->
  <div class="sec white">
    <p class="sec-title">Situaciones frecuentes — así funciona en la práctica</p>

    <div class="case-card blue">
      <p class="case-title blue">🖥️ Caso 1 — Falla técnica del Kiosco</p>
      <p class="case-body">Llegas a las 7:00 am pero el Kiosco tuvo un problema de conectividad
      y registró tu entrada a las 7:20 am. Al día siguiente recibes el correo de aviso.<br/><br/>
      <strong>¿Qué hacer?</strong> Clic en "Solicitar Corrección" → escribe
      <em>"Llegué a las 7:00 am, el Kiosco presentó un inconveniente técnico."</em>
      RRHH coordina con Tecnología, verifica y ajusta. Resuelto en horas.</p>
    </div>

    <div class="case-card amber">
      <p class="case-title amber">🤔 Caso 2 — Se me olvidó registrar la salida</p>
      <p class="case-body">Terminaste tu jornada y saliste sin pasar por el Kiosco — simplemente
      se te fue de la mente. El sistema detecta que no hay registro de salida y te avisa al día
      siguiente.<br/><br/>
      <strong>¿Qué hacer?</strong> Clic en "Solicitar Corrección" → indica la hora real de salida:
      <em>"Olvidé registrar mi salida."</em>
      Esto pasa — el sistema existe precisamente para corregirlo sin drama.</p>
    </div>

    <div class="case-card green">
      <p class="case-title green">🏥 Caso 3 — Ausencia por cita médica o permiso</p>
      <p class="case-body">Tuviste una cita médica y no pudiste asistir. Si gestionaste tu permiso
      con anticipación a través de RRHH, el sistema ya registra tu ausencia como justificada —
      el correo de aviso mostrará un bloque verde confirmando el permiso aprobado.
      No se requiere ninguna acción adicional.<br/><br/>
      <strong>Si fue una urgencia:</strong> Notifica a RRHH ese mismo día por correo
      (recursoshumanos@ueipab.edu.ve) y solicita el permiso correspondiente. Cuanto antes
      quede constancia, más fácil es gestionar la justificación.</p>
    </div>

    <div class="case-card" style="background:#f0fdf4;border-left:4px solid #2471a3;">
      <p class="case-title" style="color:#1a2c5b;">🏫 Caso 4 — Docentes: el sistema reconoce tus listas de asistencia</p>
      <p class="case-body">Si eres docente y registraste la asistencia de tus estudiantes ese día,
      el sistema lo toma como evidencia de tu presencia — aunque no hayas marcado en el Kiosco.
      <strong>Si diste tus clases normalmente, no recibirás un correo de alerta</strong>,
      incluso si tuviste un inconveniente con el registro físico.<br/><br/>
      Además, el sistema aprende tu horario: si hay días de la semana en que no tienes clases
      asignadas por contrato, ya sabe que no es un día esperado para ti y no te enviará avisos
      en esos días.<br/><br/>
      <strong>Si recibes un aviso siendo docente:</strong> significa que ese día no se encontró
      registro de clases ni otra señal de presencia. El botón de corrección sigue disponible
      para explicar lo que pasó.</p>
    </div>
  </div>

  <!-- TIPS -->
  <div class="sec alt">
    <div class="tips-box">
      <p class="tips-title">💡 Para recordar siempre</p>
      <ul class="tips-list">
        <li><strong>Kiosco</strong> (método principal) o <strong>menú lateral de Odoo</strong>
        (Check In/Out) si tienes cuenta — ambos son válidos.</li>
        <li><strong>Fallo técnico o ausencia urgente:</strong> notifícalo ese mismo día a
        recursoshumanos@ueipab.edu.ve.</li>
        <li><strong>Botón de corrección</strong> en el correo de aviso — es la vía más rápida
        y queda auditada en el sistema.</li>
        <li>Tu registro es tu <strong>respaldo documental</strong> — RRHH revisa cada solicitud
        individualmente antes de que afecte tu nómina.</li>
        <li>Si eres <strong>docente</strong>: registrar la asistencia de tus estudiantes en el
        sistema cuenta como señal de presencia — el Kiosco es el respaldo, no el único juez.</li>
      </ul>
    </div>
  </div>

  <!-- ACK SECTION -->
  {ack_section}

  <!-- FOOTER -->
  <div class="ftr">
    <p class="ftr-name">Recursos Humanos · Instituto Privado Andrés Bello, CA</p>
    <a class="ftr-email" href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
  </div>

</div>
</body>
</html>"""


def _ack_pending(ack_url):
    return f"""<div class="ack-box">
  <p class="ack-eyebrow">Confirmación de Lectura</p>
  <p class="ack-title">¿Ya leíste toda la guía?</p>
  <p class="ack-desc">Haz clic en el botón para confirmar que leíste y comprendiste
  el funcionamiento del sistema de asistencia. <strong style="color:#fff;">RRHH registrará
  tu confirmación</strong> como parte de la implementación del nuevo proceso.</p>
  <a class="btn-ack" href="{ack_url}">✅ Confirmo que leí esta guía</a>
  <p class="ack-note">Un solo clic · Sin iniciar sesión · Tu confirmación queda registrada</p>
</div>"""


def _ack_already_done():
    return """<div class="done-box">
  <div class="done-icon">✅</div>
  <p class="done-title">¡Ya confirmaste la lectura!</p>
  <p class="done-desc">Tu confirmación quedó registrada en el sistema.<br/>
  Puedes releer esta guía en cualquier momento.</p>
</div>"""
