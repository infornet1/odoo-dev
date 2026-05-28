# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

NOTICE_KEY = 'ari_guide_2026_v1'


class AriGuideController(http.Controller):

    @http.route('/ari-guide/', type='http', auth='public', website=False)
    def ari_guide_generic(self, **kwargs):
        """Generic guide page — no ACK tracking (for employees without a blast token)."""
        base       = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://odoo.ueipab.edu.ve')
        portal_url = base + '/my/ari'
        html = _build_page('trabajador/a', None, portal_url, already=False, generic=True)
        return Response(html, content_type='text/html; charset=utf-8')

    @http.route('/ari-guide/<string:token>', type='http', auth='public', website=False)
    def ari_guide(self, token, **kwargs):
        Ack = request.env['hr.notice.acknowledgment'].sudo()
        ack = Ack.search([('token', '=', token), ('notice_key', '=', NOTICE_KEY)], limit=1)
        if not ack:
            return Response(_page_not_found(), content_type='text/html; charset=utf-8', status=404)

        base = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://odoo.ueipab.edu.ve')
        portal_url = base + '/my/ari'
        ack_url    = base + '/notice-ack/' + ack.token
        emp_name   = ack.employee_id.name or 'Estimado/a trabajador/a'
        already    = ack.state == 'acknowledged'

        html = _build_page(emp_name, ack_url, portal_url, already)
        return Response(html, content_type='text/html; charset=utf-8')


def _page_not_found():
    return """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"/>
<title>Enlace inválido — Colegio Andrés Bello</title></head>
<body style="font-family:Arial,sans-serif;text-align:center;padding:60px;background:#f0f4f8;">
<h2 style="color:#0a1628;">Enlace no válido</h2>
<p style="color:#64748b;">Este enlace ya no existe o ha expirado.</p>
</body></html>"""


def _build_page(emp_name, ack_url, portal_url, already=False, generic=False):
    if already:
        ack_section = _ack_already_done()
    elif generic:
        ack_section = ''  # no ACK tracking on generic page
    else:
        ack_section = _ack_pending(ack_url)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Guía de Usuario — Portal AR-I ISLR | Colegio Andrés Bello</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;}}
    .wrap{{max-width:680px;margin:32px auto;border-radius:14px;overflow:hidden;
           box-shadow:0 6px 32px rgba(0,0,0,.13);}}
    .hdr{{background:linear-gradient(135deg,#0a1628,#1a3a6b);padding:36px 40px 28px;text-align:center;}}
    .logo{{width:72px;height:72px;border-radius:50%;border:3px solid #C8A951;overflow:hidden;display:block;margin:0 auto 14px;}}
    .hdr-eyebrow{{font-size:11px;font-weight:700;color:#C8A951;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;}}
    .hdr-title{{font-size:26px;font-weight:800;color:#FEFEFE;line-height:1.3;margin-bottom:6px;}}
    .hdr-sub{{font-size:13px;color:#8badd4;}}
    .banner{{background:linear-gradient(135deg,#a16207,#eab308);padding:14px 40px;}}
    .banner p{{font-size:13px;font-weight:700;color:#1a1a1a;}}
    .banner strong{{color:#1a1a1a;}}
    .sec{{padding:28px 40px;}}
    .sec.alt{{background:#f8faff;}}
    .sec.white{{background:#fff;}}
    .sec-title{{font-size:15px;font-weight:800;color:#0a1628;text-transform:uppercase;
                letter-spacing:1px;border-bottom:2px solid #C8A951;padding-bottom:8px;margin-bottom:16px;}}
    .prose{{font-size:13px;color:#374151;line-height:1.7;margin-bottom:14px;}}
    .card-red{{background:#fef2f2;border-left:4px solid #ef4444;border-radius:0 8px 8px 0;padding:14px 18px;margin-bottom:12px;}}
    .card-green{{background:#f0fdf4;border-left:4px solid #22c55e;border-radius:0 8px 8px 0;padding:14px 18px;}}
    .card-yellow{{background:#fef9c3;border-left:4px solid #eab308;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:20px;}}
    .card-title{{font-size:13px;font-weight:700;margin-bottom:6px;}}
    .card-body{{font-size:12px;color:#374151;line-height:1.7;}}
    .steps{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;}}
    .step{{flex:1;min-width:100px;text-align:center;}}
    .step-num{{width:36px;height:36px;background:#0a1628;border-radius:50%;color:#C8A951;
               font-size:15px;font-weight:800;line-height:36px;margin:0 auto 8px;}}
    .step-num.done{{background:#059669;color:#fff;}}
    .step-label{{font-size:11px;font-weight:700;color:#0a1628;margin-bottom:4px;}}
    .step-desc{{font-size:10px;color:#64748b;line-height:1.4;}}
    .cal{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px;}}
    .cal-item{{flex:1;min-width:80px;text-align:center;}}
    .cal-box{{background:#0a1628;border-radius:8px;padding:10px 6px;}}
    .cal-box.secondary{{background:#1a3a6b;}}
    .cal-num{{font-size:17px;font-weight:800;color:#C8A951;}}
    .cal-mon{{font-size:10px;font-weight:700;color:#FEFEFE;}}
    .cal-label{{font-size:9px;color:#374151;margin-top:4px;line-height:1.3;font-weight:700;}}
    .grid3{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;}}
    .grid3-item{{flex:1;min-width:120px;border-radius:10px;padding:12px;}}
    .grid3-title{{font-size:11px;font-weight:700;margin-bottom:4px;}}
    .grid3-body{{font-size:10px;color:#64748b;line-height:1.4;}}
    .state-row{{display:flex;align-items:center;gap:12px;padding:7px 0;border-bottom:1px solid #f1f5f9;}}
    .badge{{display:inline-block;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;white-space:nowrap;}}
    .state-desc{{font-size:12px;color:#374151;}}
    .faq-item{{padding:8px 0;border-bottom:1px solid #f1f5f9;}}
    .faq-q{{font-size:12px;font-weight:700;color:#0a1628;margin-bottom:4px;}}
    .faq-a{{font-size:12px;color:#64748b;line-height:1.5;}}
    .contact-box{{background:linear-gradient(135deg,#eff6ff,#f0fdf4);border:1px solid #bfdbfe;
                  border-radius:10px;padding:18px 22px;}}
    .contact-label{{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;
                    letter-spacing:1px;margin-bottom:4px;}}
    .contact-name{{font-size:13px;font-weight:700;color:#0a1628;margin-bottom:2px;}}
    .contact-email{{font-size:12px;color:#1d4ed8;text-decoration:none;}}
    .cta-wrap{{text-align:center;padding:24px 40px;background:#f8faff;}}
    .btn-portal{{display:inline-block;background:linear-gradient(135deg,#0a1628,#1a3a6b);
                 color:#C8A951;text-decoration:none;font-size:14px;font-weight:700;
                 padding:13px 40px;border-radius:50px;margin-bottom:10px;}}
    .ack-box{{background:linear-gradient(135deg,#052e16,#14532d);border-radius:12px;
              padding:28px;text-align:center;margin:0 40px 32px;}}
    .ack-eyebrow{{font-size:11px;font-weight:700;color:#86efac;letter-spacing:2px;
                  text-transform:uppercase;margin-bottom:8px;}}
    .ack-title{{font-size:18px;font-weight:800;color:#FEFEFE;margin-bottom:12px;}}
    .ack-desc{{font-size:12px;color:#bbf7d0;line-height:1.7;margin-bottom:20px;}}
    .btn-ack{{display:inline-block;background:#22c55e;color:#fff;text-decoration:none;
              font-size:15px;font-weight:800;padding:14px 48px;border-radius:50px;}}
    .ack-note{{font-size:10px;color:#4ade80;margin-top:14px;}}
    .done-box{{background:#f0fdf4;border:2px solid #22c55e;border-radius:12px;
               padding:28px;text-align:center;margin:0 40px 32px;}}
    .done-icon{{font-size:40px;margin-bottom:10px;}}
    .done-title{{font-size:18px;font-weight:800;color:#15803d;margin-bottom:8px;}}
    .done-desc{{font-size:13px;color:#374151;line-height:1.6;}}
    .ftr{{background:#0a1628;padding:22px 40px;text-align:center;}}
    .ftr-logo{{width:40px;height:40px;border-radius:50%;border:2px solid #C8A951;
               overflow:hidden;margin:0 auto 10px;}}
    .ftr-name{{font-size:12px;font-weight:700;color:#C8A951;margin-bottom:4px;}}
    .ftr-city{{font-size:11px;color:#8badd4;margin-bottom:6px;}}
    .ftr-email{{font-size:11px;color:#4b6080;text-decoration:none;}}
    .ftr-legal{{font-size:10px;color:#2d4060;margin-top:8px;line-height:1.5;}}
    @media(max-width:520px){{
      .sec,.hdr,.banner,.cta-wrap,.ftr{{padding-left:20px;padding-right:20px;}}
      .ack-box,.done-box{{margin-left:20px;margin-right:20px;}}
      .steps,.cal,.grid3{{flex-direction:column;}}
    }}
  </style>
</head>
<body>
<div class="wrap">

  <!-- HEADER -->
  <div class="hdr">
    <img class="logo" src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"
         alt="Colegio Andrés Bello" width="72" height="72"/>
    <p class="hdr-eyebrow">Recursos Humanos — Odoo Portal</p>
    <p class="hdr-title">Guía de Usuario<br/>Portal AR-I ISLR</p>
    <p class="hdr-sub">Declaración de Retención de Impuesto sobre la Renta · Personal UEIPAB</p>
  </div>

  <!-- URGENCY BANNER -->
  <div class="banner">
    <p>⚠️ <strong>Acción requerida, {emp_name}:</strong> Nuestros registros indican que tu AR-I
    tiene más de 90 días sin actualizar. Es obligatorio regularizarla para evitar la retención
    máxima de ISLR en tu quincena.</p>
  </div>

  <!-- SECTION 1: POR QUÉ ES OBLIGATORIO -->
  <div class="sec white">
    <p class="prose">El <strong>Formulario AR-I</strong> es tu declaración jurada anual ante el
    SENIAT que determina el porcentaje de retención de ISLR aplicado a cada pago de nómina.
    Presentarlo correctamente garantiza que se te descuente <strong>lo justo — ni más, ni menos</strong>.
    Ahora puedes completarlo y enviarlo directamente desde el <strong>portal Odoo</strong>.</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;">
      <div style="flex:1;min-width:120px;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;padding:14px;text-align:center;">
        <div style="font-size:24px;margin-bottom:6px;">⚖️</div>
        <p style="font-size:11px;font-weight:700;color:#15803d;margin-bottom:4px;">Base Legal</p>
        <p style="font-size:10px;color:#64748b;line-height:1.4;">Decreto N.° 1.808<br/>Gaceta Oficial 36.203<br/>LISLR Arts. 57, 59, 61</p>
      </div>
      <div style="flex:1;min-width:120px;background:#eff6ff;border-radius:10px;border:1px solid #bfdbfe;padding:14px;text-align:center;">
        <div style="font-size:24px;margin-bottom:6px;">💰</div>
        <p style="font-size:11px;font-weight:700;color:#1d4ed8;margin-bottom:4px;">Fija tu % ARI</p>
        <p style="font-size:10px;color:#64748b;line-height:1.4;">Se aplica como deducción de ISLR en tu recibo de pago cada quincena</p>
      </div>
      <div style="flex:1;min-width:120px;background:#fefce8;border-radius:10px;border:1px solid #fde68a;padding:14px;text-align:center;">
        <div style="font-size:24px;margin-bottom:6px;">🔄</div>
        <p style="font-size:11px;font-weight:700;color:#b45309;margin-bottom:4px;">Cada 90 Días</p>
        <p style="font-size:10px;color:#64748b;line-height:1.4;">5 fechas clave: 15 ene · 15 mar · 15 jun · 15 sep · 15 dic</p>
      </div>
    </div>
    <div class="card-red">
      <p class="card-title" style="color:#991b1b;">⚠️ Si NO presentas el AR-I a tiempo:</p>
      <p class="card-body">El patrono está obligado por ley a retener el <strong>máximo posible</strong>
      según tu nivel salarial, sin aplicar cargas familiares ni deducciones personales.</p>
    </div>
    <div class="card-green">
      <p class="card-title" style="color:#15803d;">✅ Si SÍ presentas el AR-I correctamente:</p>
      <p class="card-body">Se aplican tus rebajas personales (10 UT), cargas familiares (10 UT por cada una)
      y el desgravamen que corresponda. El resultado es un <strong>porcentaje proporcional y justo</strong>.</p>
    </div>
  </div>

  <!-- SECTION 2: CALENDARIO -->
  <div class="sec alt">
    <p class="sec-title">2 · Calendario de Declaraciones</p>
    <div class="cal">
      <div class="cal-item"><div class="cal-box"><div class="cal-num">15</div><div class="cal-mon">ENE</div></div>
        <p class="cal-label">Declaración<br/>Inicial Anual</p></div>
      <div class="cal-item"><div class="cal-box secondary"><div class="cal-num">15</div><div class="cal-mon">MAR</div></div>
        <p class="cal-label">1.er Trimestre</p></div>
      <div class="cal-item"><div class="cal-box secondary"><div class="cal-num">15</div><div class="cal-mon">JUN</div></div>
        <p class="cal-label">2.° Trimestre</p></div>
      <div class="cal-item"><div class="cal-box secondary"><div class="cal-num">15</div><div class="cal-mon">SEP</div></div>
        <p class="cal-label">3.er Trimestre</p></div>
      <div class="cal-item"><div class="cal-box secondary"><div class="cal-num">15</div><div class="cal-mon">DIC</div></div>
        <p class="cal-label">4.° Trimestre</p></div>
    </div>
  </div>

  <!-- SECTION 3: CÓMO USAR EL PORTAL -->
  <div class="sec white">
    <p class="sec-title">3 · Cómo Usar el Portal AR-I</p>
    <div class="steps">
      <div class="step"><div class="step-num">1</div>
        <p class="step-label">Accede</p>
        <p class="step-desc">odoo.ueipab.edu.ve/my/ari con tu cuenta Odoo</p></div>
      <div class="step"><div class="step-num">2</div>
        <p class="step-label">Nueva Declaración</p>
        <p class="step-desc">Clic en Nueva Declaración. Elige año fiscal</p></div>
      <div class="step"><div class="step-num">3</div>
        <p class="step-label">Completa</p>
        <p class="step-desc">Ingresos pre-llenados del contrato. Agrega cargas y deducciones</p></div>
      <div class="step"><div class="step-num">4</div>
        <p class="step-label">Envía</p>
        <p class="step-desc">Clic en Enviar para Revisión. RR.HH. aprueba y tu tasa ARI se actualiza</p></div>
      <div class="step"><div class="step-num done">✓</div>
        <p class="step-label" style="color:#059669;">Listo</p>
        <p class="step-desc">Descarga el Excel oficial SENIAT desde el portal</p></div>
    </div>
    <div class="card-yellow">
      <p class="card-body">💡 <strong>Consejo:</strong> El portal calcula automáticamente tu porcentaje ARI
      en la <strong>Sección J</strong> — no necesitas hacer ningún cálculo manual.</p>
    </div>
  </div>

  <!-- SECTION 4: SECCIONES DEL FORMULARIO -->
  <div class="sec alt">
    <p class="sec-title">4 · Qué Necesitas Completar</p>
    <div class="grid3">
      <div class="grid3-item" style="background:#f0fdf4;border:1px solid #bbf7d0;">
        <p class="grid3-title" style="color:#15803d;">📊 Sección A — Ingresos</p>
        <p class="grid3-body">Ingreso anual estimado — <strong>pre-llenado</strong> del contrato.</p></div>
      <div class="grid3-item" style="background:#eff6ff;border:1px solid #bfdbfe;">
        <p class="grid3-title" style="color:#1d4ed8;">📐 Sección B — Ingresos en UT</p>
        <p class="grid3-body">Total entre UT (Bs. 9.00). <strong>Cálculo automático.</strong></p></div>
      <div class="grid3-item" style="background:#fefce8;border:1px solid #fde68a;">
        <p class="grid3-title" style="color:#b45309;">🛡️ Sección C/E — Desgravamen</p>
        <p class="grid3-body">Único: 774 UT (la mayoría) · Detallado: médico, hipoteca, educación</p></div>
    </div>
    <div class="grid3">
      <div class="grid3-item" style="background:#fdf4ff;border:1px solid #e9d5ff;">
        <p class="grid3-title" style="color:#7e22ce;">👨‍👩‍👧 Sección H — Rebajas</p>
        <p class="grid3-body"><strong>10 UT</strong> personal + <strong>10 UT por carga</strong> (cónyuge, hijos, padres dependientes).</p></div>
      <div class="grid3-item" style="background:#fff1f2;border:1px solid #fecdd3;">
        <p class="grid3-title" style="color:#be123c;">📅 Sección K — Datos YTD</p>
        <p class="grid3-body">Solo para <strong>variaciones</strong>: lo cobrado y retenido hasta la fecha.</p></div>
      <div class="grid3-item" style="background:#f0fdf4;border:2px solid #22c55e;">
        <p class="grid3-title" style="color:#15803d;">✅ Sección J — Tu % ARI</p>
        <p class="grid3-body">El <strong>resultado final</strong>. Pasa automáticamente a tu contrato.</p></div>
    </div>
  </div>

  <!-- SECTION 5: ESTADOS -->
  <div class="sec white">
    <p class="sec-title">5 · Estados de tu Declaración</p>
    <div class="state-row"><span class="badge" style="background:#e2e8f0;color:#475569;">● BORRADOR</span>
      <span class="state-desc">Guardada pero no enviada a RR.HH. Puedes editarla libremente.</span></div>
    <div class="state-row"><span class="badge" style="background:#dbeafe;color:#1d4ed8;">● ENVIADA</span>
      <span class="state-desc">En revisión por Recursos Humanos. En espera de aprobación.</span></div>
    <div class="state-row"><span class="badge" style="background:#dcfce7;color:#15803d;">● APROBADA</span>
      <span class="state-desc">¡Listo! Tu % ARI fue actualizado. Descarga el Excel SENIAT.</span></div>
    <div class="state-row" style="border:none;"><span class="badge" style="background:#fee2e2;color:#b91c1c;">● RECHAZADA</span>
      <span class="state-desc">RR.HH. encontró un error. Revisa, corrige y vuelve a enviar.</span></div>
  </div>

  <!-- SECTION 6: FAQ -->
  <div class="sec alt">
    <p class="sec-title">6 · Preguntas Frecuentes</p>
    <div class="faq-item"><p class="faq-q">¿Qué UT debo usar?</p>
      <p class="faq-a">El valor actual es <strong>Bs. 9,00 por UT</strong>. Verifica siempre en
      <a href="https://www.seniat.gob.ve" style="color:#1d4ed8;">seniat.gob.ve</a>.</p></div>
    <div class="faq-item"><p class="faq-q">¿Puedo descargar el formulario oficial SENIAT?</p>
      <p class="faq-a">Sí. Una vez aprobada, el botón <strong>"Descargar Excel"</strong> genera el
      archivo en el formato oficial con todos tus datos completados.</p></div>
    <div class="faq-item"><p class="faq-q">¿Cada cuánto actualizo si no hubo cambios?</p>
      <p class="faq-a">Si no hubo cambios en ingresos, cargas ni UT, <strong>no son obligatorias
      las variaciones trimestrales</strong>. Solo la declaración de enero es anual obligatoria.</p></div>
    <div class="faq-item" style="border:none;"><p class="faq-q">¿Cuándo se refleja el nuevo % en mi recibo?</p>
      <p class="faq-a">A partir de la siguiente quincena luego de que RR.HH. apruebe tu declaración.</p></div>
  </div>

  <!-- ACCOUNTING HELP -->
  <div class="sec white" style="padding-top:0;">
    <div class="contact-box">
      <p style="font-size:13px;font-weight:700;color:#0a1628;margin-bottom:8px;">🧮 ¿Necesitas ayuda contable?</p>
      <p style="font-size:12px;color:#374151;line-height:1.7;margin-bottom:12px;">Si tienes dudas específicas
      sobre tu situación tributaria, deducciones detalladas o el cálculo de tu ISLR:</p>
      <div style="display:flex;gap:16px;flex-wrap:wrap;">
        <div style="flex:1;min-width:160px;">
          <p class="contact-label">Contacto</p>
          <p class="contact-name">Lic. Dubinis Cabeza</p>
          <a class="contact-email" href="mailto:dubinis.cabeza@ueipab.edu.ve">dubinis.cabeza@ueipab.edu.ve</a>
        </div>
        <div style="flex:1;min-width:160px;">
          <p class="contact-label">Con copia a</p>
          <p class="contact-name">Recursos Humanos</p>
          <a class="contact-email" href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
        </div>
      </div>
    </div>
  </div>

  <!-- PORTAL CTA -->
  <div class="cta-wrap">
    <p style="font-size:13px;font-weight:700;color:#0a1628;margin-bottom:8px;">
      Accede al portal y completa tu declaración AR-I:
    </p>
    <a class="btn-portal" href="{portal_url}">📋 Acceder al Portal AR-I</a>
  </div>

  <!-- ACK SECTION -->
  {ack_section}

  <!-- FOOTER -->
  <div class="ftr">
    <img class="ftr-logo" src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"
         alt="Colegio Andrés Bello" width="40" height="40"/>
    <p class="ftr-name">Recursos Humanos · Colegio Andrés Bello</p>
    <p class="ftr-city">El Tigre, Venezuela</p>
    <a class="ftr-email" href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
    <p class="ftr-legal">Base legal: Decreto N.° 1.808 · Gaceta Oficial N.° 36.203 (12-May-1997)<br/>
    LISLR Arts. 57, 59, 61 · Art. 7 Reglamento Parcial LISLR en Materia de Retenciones</p>
  </div>

</div>
</body>
</html>"""


def _ack_pending(ack_url):
    return f"""<div class="ack-box">
  <p class="ack-eyebrow">Confirmación de Lectura</p>
  <p class="ack-title">¿Ya leíste toda la guía?</p>
  <p class="ack-desc">Haz clic en el botón para confirmar que has leído y comprendido
  las instrucciones del Portal AR-I. <strong style="color:#FEFEFE;">RR.HH. registrará
  tu confirmación</strong> y tendrás acceso prioritario ante cualquier consulta.</p>
  <a class="btn-ack" href="{ack_url}">✅ Confirmo que leí esta guía</a>
  <p class="ack-note">Un solo clic · Sin iniciar sesión · Tu confirmación queda registrada</p>
</div>"""


def _ack_already_done():
    return """<div class="done-box">
  <div class="done-icon">✅</div>
  <p class="done-title">¡Ya confirmaste la lectura!</p>
  <p class="done-desc">Tu confirmación quedó registrada en el sistema.<br/>
  Puedes acceder al portal en cualquier momento para gestionar tu declaración AR-I.</p>
</div>"""
