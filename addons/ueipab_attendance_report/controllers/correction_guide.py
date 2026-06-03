# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

NOTICE_KEY = 'correction_guide_2026_v1'
LOGO_URL   = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'


class CorrectionGuideController(http.Controller):

    @http.route('/correction-guide/<string:token>', type='http', auth='public', website=False)
    def correction_guide(self, token, **kwargs):
        Ack = request.env['hr.notice.acknowledgment'].sudo()
        ack = Ack.search([('token', '=', token), ('notice_key', '=', NOTICE_KEY)], limit=1)
        if not ack:
            return Response(_page_not_found(), content_type='text/html; charset=utf-8', status=404)

        base     = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'https://odoo.ueipab.edu.ve')
        ack_url  = base + '/notice-ack/' + ack.token
        emp_name = ack.employee_id.name or 'Estimado/a'
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
    first_name  = emp_name.split()[0].capitalize() if emp_name else 'Estimado/a'
    ack_section = _ack_already_done() if already else _ack_pending(ack_url)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Guía: Correcciones de Asistencia | RRHH</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;}}
    .wrap{{max-width:700px;margin:28px auto;border-radius:14px;overflow:hidden;
           box-shadow:0 6px 32px rgba(0,0,0,.13);}}
    .hdr{{background:linear-gradient(135deg,#1a2c5b,#2471a3);padding:32px 36px 24px;text-align:center;}}
    .logo{{width:70px;height:70px;border-radius:50%;border:3px solid rgba(255,255,255,.3);
           display:block;margin:0 auto 12px;object-fit:cover;}}
    .hdr-title{{font-size:22px;font-weight:800;color:#fff;margin-bottom:6px;}}
    .hdr-sub{{font-size:13px;color:rgba(255,255,255,.8);}}
    .sec{{padding:24px 36px;}}
    .sec.alt{{background:#f8faff;}}
    .sec.white{{background:#fff;}}
    .sec-title{{font-size:14px;font-weight:800;color:#1a2c5b;text-transform:uppercase;
                letter-spacing:1px;border-bottom:2px solid #2471a3;padding-bottom:7px;margin-bottom:16px;}}
    .prose{{font-size:13px;color:#374151;line-height:1.75;margin-bottom:12px;}}
    table.route{{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:12px;}}
    table.route th{{background:#1a2c5b;color:#fff;padding:8px 12px;text-align:left;}}
    table.route td{{padding:8px 12px;border-bottom:1px solid #e2e8f0;vertical-align:top;}}
    table.route tr:nth-child(even) td{{background:#f8faff;}}
    .badge-att{{background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;}}
    .badge-leave{{background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;}}
    .badge-wizard{{background:#f3e8ff;color:#6b21a8;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;}}
    .step-row{{display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;}}
    .step-num{{min-width:28px;height:28px;background:#1a2c5b;border-radius:50%;color:#fff;
               font-size:13px;font-weight:800;line-height:28px;text-align:center;}}
    .step-body{{font-size:13px;color:#374151;line-height:1.65;}}
    .callout{{border-radius:8px;padding:14px 18px;margin-bottom:12px;font-size:13px;}}
    .callout.blue{{background:#eff6ff;border-left:4px solid #2471a3;color:#1e3a5f;}}
    .callout.purple{{background:#f5f3ff;border-left:4px solid #7c3aed;color:#4c1d95;}}
    .callout.amber{{background:#fffbeb;border-left:4px solid #f59e0b;color:#78350f;}}
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
    @media(max-width:500px){{
      .sec,.hdr,.ack-box,.done-box,.ftr{{padding-left:18px;padding-right:18px;}}
    }}
  </style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <img class="logo" src="{LOGO_URL}" alt="UEIPAB" width="70" height="70"/>
    <p class="hdr-title">Guía de Correcciones de Asistencia</p>
    <p class="hdr-sub">U.E.I.P.A.B. · Recursos Humanos · Uso interno — 2026</p>
  </div>

  <div class="sec white">
    <p class="prose">Hola <strong>{first_name}</strong>, esta guía explica el funcionamiento
    del nuevo sistema de correcciones de asistencia con <strong>despacho automático según el motivo</strong>.
    Lee con atención — a partir de ahora el botón <em>Aprobar</em> actúa de forma diferente
    dependiendo de lo que el empleado indicó como motivo.</p>
  </div>

  <div class="sec alt">
    <p class="sec-title">Por qué dos rutas distintas</p>
    <p class="prose">No toda corrección es igual. Hay dos situaciones fundamentalmente diferentes
    que antes se trataban de la misma manera (creando un registro de asistencia), lo que generaba
    datos incorrectos:</p>
    <div class="callout blue" style="margin-bottom:10px;">
      <strong>Error de reloj</strong> — El empleado <em>estaba presente</em> pero el kiosco
      falló, se fue la luz, o se olvidó de registrar la salida. La solución correcta es crear
      o corregir el registro de <em>hr.attendance</em>.
    </div>
    <div class="callout amber">
      <strong>Ausencia genuina</strong> — El empleado <em>no estaba presente</em> (cita médica,
      luto, trámite legal, capacitación pagada). La solución correcta es crear un <em>hr.leave</em>
      para que quede clasificado y entre en el flujo de aprobación de permisos.
    </div>
  </div>

  <div class="sec white">
    <p class="sec-title">Tabla de despacho automático por motivo</p>
    <table class="route">
      <thead>
        <tr>
          <th>Motivo seleccionado por el empleado</th>
          <th>Al hacer clic en Aprobar</th>
          <th>Tipo de permiso creado</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Corte de energia electrica</td>
            <td><span class="badge-att">hr.attendance</span></td><td>—</td></tr>
        <tr><td>Capacitacion / evento institucional</td>
            <td><span class="badge-leave">hr.leave</span></td><td>Paid Time Off</td></tr>
        <tr><td>Consulta o emergencia medica</td>
            <td><span class="badge-leave">hr.leave</span></td><td>Cita Medica personal</td></tr>
        <tr><td>Reposo medico prescrito</td>
            <td><span class="badge-leave">hr.leave</span></td><td>Sick Time Off</td></tr>
        <tr><td>Duelo familiar</td>
            <td><span class="badge-leave">hr.leave</span></td><td>Muerte familiar (luto)</td></tr>
        <tr><td>Citacion judicial / obligacion legal</td>
            <td><span class="badge-leave">hr.leave</span></td><td>Diligencia personal</td></tr>
        <tr><td>Matrimonio del trabajador</td>
            <td><span class="badge-leave">hr.leave</span></td><td>Paid Time Off</td></tr>
        <tr><td>Calamidad domestica</td>
            <td><span class="badge-leave">hr.leave</span></td><td>Diligencia personal</td></tr>
        <tr><td>Otro motivo</td>
            <td><span class="badge-wizard">Asistente RRHH</span></td><td>RRHH decide</td></tr>
      </tbody>
    </table>
    <p class="prose" style="font-size:11px;color:#64748b;">
      * El permiso se crea en estado <strong>Confirmado</strong> y entra en el flujo de aprobacion
      normal — recibiras la notificacion habitual de permisos pendientes.
    </p>
  </div>

  <div class="sec alt">
    <p class="sec-title">El asistente para "Otro motivo"</p>
    <p class="prose">Cuando el motivo es <strong>Otro</strong>, el sistema no puede decidir
    automaticamente. Al hacer clic en <em>Aprobar</em> se abre un pequeno dialogo donde
    RRHH lee el texto libre del empleado y elige:</p>
    <div class="callout purple">
      <strong>Opcion A — Correccion de asistencia:</strong> el empleado estaba presente, solo
      hubo un error en el registro de entrada/salida.<br/><br/>
      <strong>Opcion B — Registrar como permiso:</strong> el empleado estaba ausente. Se
      selecciona el tipo de permiso del desplegable y el sistema crea el <em>hr.leave</em>.
    </div>
  </div>

  <div class="sec white">
    <p class="sec-title">Flujo completo paso a paso</p>
    <div class="step-row">
      <div class="step-num">1</div>
      <div class="step-body"><strong>Empleado recibe alerta</strong> — correo diario de asistencia
      con boton <em>Solicitar Correccion</em>. Rellena el formulario: hora de entrada/salida
      y <strong>motivo</strong>.</div>
    </div>
    <div class="step-row">
      <div class="step-num">2</div>
      <div class="step-body"><strong>RRHH recibe la solicitud</strong> — aparece en
      <em>Correcciones de Asistencia</em>. El campo <em>Categoria de motivo</em>
      ya indica si es una correccion de asistencia o un permiso.</div>
    </div>
    <div class="step-row">
      <div class="step-num">3</div>
      <div class="step-body"><strong>RRHH hace clic en Aprobar</strong> — el sistema despacha
      automaticamente segun el motivo. Para <em>Otro motivo</em> abre el asistente de decision.</div>
    </div>
    <div class="step-row">
      <div class="step-num">4</div>
      <div class="step-body"><strong>Resultado</strong> — si es asistencia: registro de reloj
      creado, empleado notificado. Si es permiso: <em>hr.leave</em> en estado Confirmado,
      entra en flujo de aprobacion normal, el empleado recibe la misma notificacion.</div>
    </div>
    <div class="step-row">
      <div class="step-num">5</div>
      <div class="step-body"><strong>Para permisos:</strong> aparecera en la bandeja de aprobacion
      de permisos con un boton <em>Ver Permiso</em> en el formulario de la correccion para navegar
      directamente al registro <em>hr.leave</em>.</div>
    </div>
  </div>

  {ack_section}

  <div class="ftr">
    <p class="ftr-name">Recursos Humanos · Instituto Privado Andres Bello, CA</p>
  </div>

</div>
</body>
</html>"""


def _ack_pending(ack_url):
    return f"""<div class="ack-box">
  <p class="ack-eyebrow">Confirmacion de Lectura</p>
  <p class="ack-title">Ya leiste toda la guia?</p>
  <p class="ack-desc">Haz clic para confirmar que leiste y comprendiste el nuevo flujo de
  correcciones con despacho automatico. <strong style="color:#fff;">Tu confirmacion queda
  registrada en el sistema.</strong></p>
  <a class="btn-ack" href="{ack_url}">Confirmo que lei esta guia</a>
  <p class="ack-note">Un solo clic · Sin iniciar sesion</p>
</div>"""


def _ack_already_done():
    return """<div class="done-box">
  <div class="done-icon">&#10003;</div>
  <p class="done-title">Ya confirmaste la lectura!</p>
  <p class="done-desc">Tu confirmacion quedo registrada.<br/>
  Puedes releer esta guia en cualquier momento.</p>
</div>"""
