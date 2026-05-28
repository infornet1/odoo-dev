"""
AR-I Portal Staff Guide email — with employee acknowledgment tracking.

Usage (test):
    python3 scripts/create_ari_portal_guide_email.py --env testing

Usage (bulk production send — one email + ACK token per employee):
    python3 scripts/create_ari_portal_guide_email.py --env production --bulk

ACK tracking: creates one hr.notice.acknowledgment record per employee
(notice_key='ari_guide_2026_v1'). Token link embedded in each email.
RR.HH. is CC'd on every send. Acknowledgment visible in Odoo backend.
"""
import json, xmlrpc.client, argparse

cfg  = json.load(open('/opt/odoo-dev/config/production.json'))
ENVS = {
    'testing':    ('http://localhost:8019',                          'testing',   2, '35baa2abcc6dee920fa75014f0274c8e551871ce'),
    'production': (cfg['production']['xmlrpc']['url'],              cfg['production']['xmlrpc']['db'],
                   2,                                               cfg['production']['xmlrpc']['api_key']),
}
WEB_BASE = {
    'testing':    'https://dev.ueipab.edu.ve',
    'production': 'https://odoo.ueipab.edu.ve',
}
PORTAL_URL = {
    'testing':    'https://dev.ueipab.edu.ve/my/ari',
    'production': 'https://odoo.ueipab.edu.ve/my/ari',
}

NOTICE_KEY = 'ari_guide_2026_v1'
SUBJECT    = 'Llegó la AR-I digital y debemos actualizarla cada 90 días  - 📋 Guía para nuestros trabajadoras y trabajadores — Portal AR-I ISLR | Colegio Andrés Bello'
FROM       = 'Recursos Humanos — Colegio Andrés Bello <recursoshumanos@ueipab.edu.ve>'
CC         = 'recursoshumanos@ueipab.edu.ve'
TO_TEST    = 'Gustavo Perdomo <gustavo.perdomo@ueipab.edu.ve>'


def build_body(employee_name, ack_url, portal_url):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Guía de Usuario — Portal AR-I ISLR</title>
  <meta name="color-scheme" content="light"/>
  <meta name="supported-color-schemes" content="light"/>
  <style type="text/css">
    @media only screen and (max-width:480px) {{
      .rwd-col  {{ display:block !important; width:100% !important; box-sizing:border-box; padding:6px 0 !important; }}
      .rwd-hide {{ display:none !important; font-size:0 !important; max-height:0 !important; overflow:hidden; }}
      .rwd-cal  {{ display:inline-block !important; width:44% !important; margin:3px 2% !important; vertical-align:top; }}
    }}
  </style>
</head>
<body class="body" style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<style type="text/css">
  u + .body .gbs {{ background:#000000 !important; mix-blend-mode:screen !important; }}
  u + .body .gbd {{ background:#000000 !important; mix-blend-mode:difference !important; }}
</style>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0f4f8;">
<tr><td align="center" style="padding:28px 12px;">
<table width="620" cellpadding="0" cellspacing="0" border="0"
       style="max-width:620px;width:100%;border-radius:14px;overflow:hidden;
              box-shadow:0 6px 32px rgba(0,0,0,0.13);">

  <!-- ── HEADER ── -->
  <tr>
    <td style="background-color:#0a1628;background:linear-gradient(135deg,#0a1628 0%,#1a3a6b 100%);
               padding:36px 40px 28px;text-align:center;">
      <div style="width:72px;height:72px;border-radius:50%;border:3px solid #C8A951;
                  overflow:hidden;display:block;margin:0 auto 16px;">
        <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"
             alt="Colegio Andrés Bello" width="72" height="72"
             style="display:block;width:72px;height:72px;"/>
      </div>
      <div class="gbs"><div class="gbd">
      <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#C8A951;
                letter-spacing:2px;text-transform:uppercase;">Recursos Humanos — Odoo Portal</p>
      <p style="margin:0 0 8px;font-size:26px;font-weight:800;color:#FEFEFE;line-height:1.3;">
        Guía de Usuario<br/>Portal AR-I ISLR
      </p>
      <p style="margin:0;font-size:14px;color:#8badd4;">
        Declaración de Retención de Impuesto sobre la Renta · Personal UEIPAB
      </p>
      </div></div>
    </td>
  </tr>

  <!-- ── URGENCY BANNER ── -->
  <tr>
    <td style="background-color:#a16207;background:linear-gradient(135deg,#a16207 0%,#eab308 100%);padding:0;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding:16px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td width="42px" style="vertical-align:middle;padding-right:14px;">
                  <div style="width:42px;height:42px;background:rgba(0,0,0,0.12);
                              border-radius:50%;text-align:center;line-height:42px;font-size:22px;">
                    ⚠️
                  </div>
                </td>
                <td style="vertical-align:middle;">
                  <p style="margin:0 0 2px;font-size:14px;font-weight:800;color:#1a1a1a;">
                    Acción requerida: estamos activando un nuevo módulo para mejorar el seguimiento de tu AR-I y debemos actualizarla
                  </p>
                  <p style="margin:0;font-size:12px;color:#422006;line-height:1.5;">
                    Estimado/a <strong style="color:#1a1a1a;">{employee_name}</strong>,
                    nuestros registros indican que tu AR-I tiene más de 90 días sin actualizar.
                    Es obligatorio regularizarla para evitar una retención máxima de ISLR en tu quincena.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── INTRO ── -->
  <tr>
    <td style="background:#ffffff;padding:32px 40px 24px;">
      <p style="margin:0 0 16px;font-size:15px;color:#374151;line-height:1.7;">
        El <strong>Formulario AR-I</strong> es tu declaración jurada anual ante el SENIAT que determina
        el porcentaje de retención de ISLR aplicado a cada pago de nómina.
        Presentarlo correctamente garantiza que se te descuente <strong>lo justo — ni más, ni menos</strong>.
        Ahora puedes completarlo y enviarlo directamente desde el <strong>portal Odoo</strong>,
        sin formularios físicos.
      </p>

      <!-- 3 intro cards -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td class="rwd-col" width="31%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;
                        padding:16px 12px;text-align:center;">
              <div style="font-size:28px;margin-bottom:8px;">⚖️</div>
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#15803d;">Base Legal</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                Decreto N.° 1.808<br/>Gaceta Oficial 36.203<br/>LISLR Arts. 57, 59, 61
              </p>
            </div>
          </td>
          <td class="rwd-hide" width="4%"></td>
          <td class="rwd-col" width="31%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#eff6ff;border-radius:10px;border:1px solid #bfdbfe;
                        padding:16px 12px;text-align:center;">
              <div style="font-size:28px;margin-bottom:8px;">💰</div>
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#1d4ed8;">Fija tu % ARI</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                El resultado se aplica a cada quincena como deducción de ISLR en tu recibo de pago
              </p>
            </div>
          </td>
          <td class="rwd-hide" width="4%"></td>
          <td class="rwd-col" width="31%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#fefce8;border-radius:10px;border:1px solid #fde68a;
                        padding:16px 12px;text-align:center;">
              <div style="font-size:28px;margin-bottom:8px;">🔄</div>
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#b45309;">Cada 90 Días</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                5 fechas clave al año: 15 ene · 15 mar · 15 jun · 15 sep · 15 dic
              </p>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 1: POR QUÉ ES OBLIGATORIO ── -->
  <tr>
    <td style="background:#f8faff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        1 · Por Qué es Obligatorio
      </p>
      <p style="margin:0 0 16px;font-size:13px;color:#374151;line-height:1.7;">
        El <strong>Art. 7 del Decreto N.° 1.808</strong> establece que todo trabajador bajo relación
        de dependencia debe presentar el AR-I a su patrono para fijar cuánto ISLR se le retiene en
        cada cobro de nómina. La presentación es <strong>responsabilidad exclusiva del empleado</strong> —
        no del patrono.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:14px;">
        <tr>
          <td style="background:#fef2f2;border-left:4px solid #ef4444;border-radius:0 8px 8px 0;
                     padding:14px 18px;">
            <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#991b1b;">
              ⚠️ Si NO presentas el AR-I a tiempo:
            </p>
            <p style="margin:0;font-size:12px;color:#374151;line-height:1.7;">
              El patrono está obligado por ley a calcular la retención tomando como base
              tu remuneración anual estimada <strong>sin aplicar cargas familiares ni deducciones personales</strong>.
              Resultado: te descuentan <strong>el máximo posible</strong> según tu nivel salarial,
              directamente en cada quincena.
            </p>
          </td>
        </tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background:#f0fdf4;border-left:4px solid #22c55e;border-radius:0 8px 8px 0;
                     padding:14px 18px;">
            <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#15803d;">
              ✅ Si SÍ presentas el AR-I correctamente:
            </p>
            <p style="margin:0;font-size:12px;color:#374151;line-height:1.7;">
              Se aplican tus rebajas personales (10 UT), cargas familiares (10 UT por cada una)
              y el desgravamen que corresponda (único 774 UT o detallado). El resultado
              es un <strong>porcentaje proporcional y justo</strong> a tu situación real.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 2: CALENDARIO ── -->
  <tr>
    <td style="background:#ffffff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        2 · Calendario de Declaraciones
      </p>
      <p style="margin:0 0 18px;font-size:13px;color:#374151;line-height:1.6;">
        El ciclo AR-I tiene <strong>cinco fechas límite por año</strong>. La primera es la declaración
        inicial anual; las siguientes son actualizaciones trimestrales si hubo cambios en tu situación.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td class="rwd-cal" width="18%" style="text-align:center;vertical-align:top;padding:0 3px;">
            <div style="background:#0a1628;border-radius:10px;padding:14px 8px;">
              <p style="margin:0 0 2px;font-size:18px;font-weight:800;color:#C8A951;">15</p>
              <p style="margin:0;font-size:11px;font-weight:700;color:#FEFEFE;">ENE</p>
            </div>
            <p style="margin:8px 0 0;font-size:10px;color:#374151;line-height:1.4;font-weight:700;">
              Declaración<br/>Inicial Anual
            </p>
            <p style="margin:4px 0 0;font-size:10px;color:#64748b;line-height:1.3;">
              Obligatoria para todos
            </p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:18px;vertical-align:top;padding-top:18px;">›</td>
          <td class="rwd-cal" width="18%" style="text-align:center;vertical-align:top;padding:0 3px;">
            <div style="background:#1a3a6b;border-radius:10px;padding:14px 8px;">
              <p style="margin:0 0 2px;font-size:18px;font-weight:800;color:#C8A951;">15</p>
              <p style="margin:0;font-size:11px;font-weight:700;color:#FEFEFE;">MAR</p>
            </div>
            <p style="margin:8px 0 0;font-size:10px;color:#374151;line-height:1.4;font-weight:700;">1.er Trimestre</p>
            <p style="margin:4px 0 0;font-size:10px;color:#64748b;line-height:1.3;">Si hubo cambios</p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:18px;vertical-align:top;padding-top:18px;">›</td>
          <td class="rwd-cal" width="18%" style="text-align:center;vertical-align:top;padding:0 3px;">
            <div style="background:#1a3a6b;border-radius:10px;padding:14px 8px;">
              <p style="margin:0 0 2px;font-size:18px;font-weight:800;color:#C8A951;">15</p>
              <p style="margin:0;font-size:11px;font-weight:700;color:#FEFEFE;">JUN</p>
            </div>
            <p style="margin:8px 0 0;font-size:10px;color:#374151;line-height:1.4;font-weight:700;">2.° Trimestre</p>
            <p style="margin:4px 0 0;font-size:10px;color:#64748b;line-height:1.3;">Si hubo cambios</p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:18px;vertical-align:top;padding-top:18px;">›</td>
          <td class="rwd-cal" width="18%" style="text-align:center;vertical-align:top;padding:0 3px;">
            <div style="background:#1a3a6b;border-radius:10px;padding:14px 8px;">
              <p style="margin:0 0 2px;font-size:18px;font-weight:800;color:#C8A951;">15</p>
              <p style="margin:0;font-size:11px;font-weight:700;color:#FEFEFE;">SEP</p>
            </div>
            <p style="margin:8px 0 0;font-size:10px;color:#374151;line-height:1.4;font-weight:700;">3.er Trimestre</p>
            <p style="margin:4px 0 0;font-size:10px;color:#64748b;line-height:1.3;">Si hubo cambios</p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:18px;vertical-align:top;padding-top:18px;">›</td>
          <td class="rwd-cal" width="18%" style="text-align:center;vertical-align:top;padding:0 3px;">
            <div style="background:#1a3a6b;border-radius:10px;padding:14px 8px;">
              <p style="margin:0 0 2px;font-size:18px;font-weight:800;color:#C8A951;">15</p>
              <p style="margin:0;font-size:11px;font-weight:700;color:#FEFEFE;">DIC</p>
            </div>
            <p style="margin:8px 0 0;font-size:10px;color:#374151;line-height:1.4;font-weight:700;">4.° Trimestre</p>
            <p style="margin:4px 0 0;font-size:10px;color:#64748b;line-height:1.3;">Si hubo cambios</p>
          </td>
        </tr>
      </table>
      <p style="margin:22px 0 10px;font-size:13px;font-weight:700;color:#0a1628;">
        📌 ¿Cuándo debo actualizar mi AR-I?
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="48%" style="vertical-align:top;font-size:12px;color:#374151;line-height:1.8;padding-right:10px;">
            🔹 Recibiste un <strong>aumento de sueldo</strong><br/>
            🔹 Tuviste un <strong>nuevo hijo o carga familiar</strong><br/>
            🔹 Contrajiste <strong>matrimonio</strong>
          </td>
          <td width="48%" style="vertical-align:top;font-size:12px;color:#374151;line-height:1.8;">
            🔹 El SENIAT actualizó el <strong>valor de la UT</strong><br/>
            🔹 Cambiaron tus <strong>ingresos o deducciones</strong><br/>
            🔹 Es tu <strong>primer año</strong> en la institución
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 3: CÓMO USAR EL PORTAL ── -->
  <tr>
    <td style="background:#f8faff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        3 · Cómo Usar el Portal AR-I
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
        <tr>
          <td width="20%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">1</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Accede</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Ingresa a<br/><strong>odoo.ueipab.edu.ve/my/ari</strong><br/>con tu cuenta Odoo
            </p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:20px;vertical-align:middle;">›</td>
          <td class="rwd-col" width="20%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">2</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Nueva Declaración</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Clic en <strong>Nueva Declaración</strong>. Elige año fiscal e inicial o variación
            </p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:20px;vertical-align:middle;">›</td>
          <td class="rwd-col" width="20%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">3</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Completa</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Tus ingresos se pre-llenan del contrato. Indica deducciones y cargas familiares
            </p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:20px;vertical-align:middle;">›</td>
          <td class="rwd-col" width="20%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">4</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Envía</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Clic en <strong>Enviar para Revisión</strong>. RR.HH. aprueba y tu tasa ARI se actualiza
            </p>
          </td>
          <td class="rwd-hide" width="2%" style="text-align:center;color:#C8A951;font-size:20px;vertical-align:middle;">›</td>
          <td width="20%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#059669;border-radius:50%;
                        color:#FEFEFE;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">✓</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#059669;">Listo</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Descarga el Excel oficial SENIAT desde el portal en cualquier momento
            </p>
          </td>
        </tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;padding:12px 16px;">
            <p style="margin:0;font-size:12px;color:#78350f;line-height:1.6;">
              💡 <strong>Consejo:</strong> El portal calcula automáticamente tu porcentaje ARI en la
              <strong>Sección J</strong> a medida que completas las secciones anteriores.
              No necesitas hacer ningún cálculo manual — el sistema aplica la tabla progresiva del Art. 57 LISLR.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 4: SECCIONES DEL FORMULARIO ── -->
  <tr>
    <td style="background:#ffffff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        4 · Qué Necesitas Completar
      </p>
      <p style="margin:0 0 16px;font-size:13px;color:#374151;">
        El formulario se divide en secciones. El portal pre-llena lo que ya está en tu contrato
        — solo debes revisar y agregar tus datos personales.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td class="rwd-col" width="30%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;padding:14px;">
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#15803d;">📊 Sección A — Ingresos</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                Ingreso anual estimado — <strong>pre-llenado</strong> del contrato. Agrega otros empleadores si aplica.
              </p>
            </div>
          </td>
          <td class="rwd-hide" width="3%"></td>
          <td class="rwd-col" width="30%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#eff6ff;border-radius:10px;border:1px solid #bfdbfe;padding:14px;">
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#1d4ed8;">📐 Sección B — Ingresos en UT</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                Total entre UT (Bs. 9.00 actualmente). <strong>Cálculo automático</strong>.
              </p>
            </div>
          </td>
          <td class="rwd-hide" width="3%"></td>
          <td class="rwd-col" width="30%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#fefce8;border-radius:10px;border:1px solid #fde68a;padding:14px;">
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#b45309;">🛡️ Sección C/E — Desgravamen</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                • <strong>Único:</strong> 774 UT (la mayoría)<br/>
                • <strong>Detallado:</strong> médico, hipoteca, educación
              </p>
            </div>
          </td>
        </tr>
        <tr><td colspan="5" style="height:10px;"></td></tr>
        <tr>
          <td class="rwd-col" width="30%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#fdf4ff;border-radius:10px;border:1px solid #e9d5ff;padding:14px;">
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#7e22ce;">👨‍👩‍👧 Sección H — Rebajas</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                <strong>10 UT</strong> personal + <strong>10 UT por carga</strong> (cónyuge, hijos, padres dependientes).
              </p>
            </div>
          </td>
          <td class="rwd-hide" width="3%"></td>
          <td class="rwd-col" width="30%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#fff1f2;border-radius:10px;border:1px solid #fecdd3;padding:14px;">
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#be123c;">📅 Sección K — Datos YTD</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                Solo para <strong>variaciones</strong> (mar/jun/sep/dic): lo cobrado y retenido hasta la fecha.
              </p>
            </div>
          </td>
          <td class="rwd-hide" width="3%"></td>
          <td class="rwd-col" width="30%" style="vertical-align:top;padding:0 4px 8px;">
            <div style="background:#f0fdf4;border-radius:10px;border:2px solid #22c55e;padding:14px;">
              <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#15803d;">✅ Sección J — Tu % ARI</p>
              <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
                El <strong>resultado final</strong>. Pasa automáticamente a tu contrato tras la aprobación de RR.HH.
              </p>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 5: ESTADOS ── -->
  <tr>
    <td style="background:#f8faff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        5 · Estados de tu Declaración
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding:7px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#e2e8f0;color:#475569;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;">● BORRADOR</span>
          </td>
          <td style="padding:7px 0 7px 12px;font-size:12px;color:#374151;">
            Guardada pero <strong>no enviada</strong> a RR.HH. Puedes editarla libremente.
          </td>
        </tr>
        <tr>
          <td style="padding:7px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#dbeafe;color:#1d4ed8;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;">● ENVIADA</span>
          </td>
          <td style="padding:7px 0 7px 12px;font-size:12px;color:#374151;">
            En revisión por Recursos Humanos. <strong>En espera de aprobación.</strong>
          </td>
        </tr>
        <tr>
          <td style="padding:7px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#dcfce7;color:#15803d;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;">● APROBADA</span>
          </td>
          <td style="padding:7px 0 7px 12px;font-size:12px;color:#374151;">
            <strong>¡Listo!</strong> Tu % ARI fue actualizado. Descarga el Excel SENIAT desde el portal.
          </td>
        </tr>
        <tr>
          <td style="padding:7px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#fee2e2;color:#b91c1c;font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;">● RECHAZADA</span>
          </td>
          <td style="padding:7px 0 7px 12px;font-size:12px;color:#374151;">
            RR.HH. encontró un error. Revisa el motivo, corrige y vuelve a enviar.
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 6: FAQ ── -->
  <tr>
    <td style="background:#ffffff;padding:28px 40px 20px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        6 · Preguntas Frecuentes
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">¿Qué UT debo usar?</p>
            <p style="margin:0;font-size:12px;color:#64748b;line-height:1.5;">
              El valor actual es <strong>Bs. 9,00 por UT</strong>. Verifica siempre en
              <a href="https://www.seniat.gob.ve" style="color:#1d4ed8;">seniat.gob.ve</a> antes de declarar.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">¿Puedo descargar el formulario oficial SENIAT?</p>
            <p style="margin:0;font-size:12px;color:#64748b;line-height:1.5;">
              Sí. Una vez aprobada, el botón <strong>"Descargar Excel"</strong> genera el archivo
              en el formato oficial SENIAT con todos tus datos completados.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;">
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">¿Cada cuánto debo actualizar si no hubo cambios?</p>
            <p style="margin:0;font-size:12px;color:#64748b;line-height:1.5;">
              Si no hubo cambios en ingresos, cargas ni UT, <strong>no son obligatorias las variaciones trimestrales</strong>.
              Solo la declaración de enero es anual obligatoria para todos.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:8px 0;">
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">¿Cuándo se reflejará el nuevo % en mi recibo?</p>
            <p style="margin:0;font-size:12px;color:#64748b;line-height:1.5;">
              A partir de la siguiente quincena luego de que RR.HH. apruebe tu declaración.
              El porcentaje se aplica automáticamente en el momento de la aprobación.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── ACCOUNTING HELP ── -->
  <tr>
    <td style="background:#ffffff;padding:0 40px 28px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background-color:#eff6ff;background:linear-gradient(135deg,#eff6ff,#f0fdf4);
                     border:1px solid #bfdbfe;border-radius:10px;padding:18px 22px;">
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#0a1628;">
              🧮 ¿Necesitas ayuda contable profesional?
            </p>
            <p style="margin:0 0 12px;font-size:12px;color:#374151;line-height:1.7;">
              Si tienes dudas específicas sobre tu situación tributaria, deducciones detalladas
              o el cálculo de tu ISLR, puedes comunicarte con nuestro asesor contable:
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td width="48%" style="vertical-align:top;">
                  <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Contacto</p>
                  <p style="margin:0 0 2px;font-size:13px;font-weight:700;color:#0a1628;">Lic. Dubinis Cabeza</p>
                  <a href="mailto:dubinis.cabeza@ueipab.edu.ve" style="font-size:12px;color:#1d4ed8;text-decoration:none;">
                    dubinis.cabeza@ueipab.edu.ve
                  </a>
                </td>
                <td width="4%"></td>
                <td width="48%" style="vertical-align:top;">
                  <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Con copia a</p>
                  <p style="margin:0 0 2px;font-size:13px;font-weight:700;color:#0a1628;">Recursos Humanos</p>
                  <a href="mailto:recursoshumanos@ueipab.edu.ve" style="font-size:12px;color:#1d4ed8;text-decoration:none;">
                    recursoshumanos@ueipab.edu.ve
                  </a>
                  <p style="margin:4px 0 0;font-size:10px;color:#64748b;">(para seguimiento interno)</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── CTA — PORTAL ── -->
  <tr>
    <td style="background:#f8faff;padding:24px 40px 0;text-align:center;">
      <p style="margin:0 0 8px;font-size:14px;font-weight:700;color:#0a1628;">
        Accede al portal y completa tu declaración AR-I ahora:
      </p>
      <p style="margin:0 0 20px;font-size:12px;color:#64748b;">
        Recuerda: la fecha límite de la declaración inicial es el <strong>15 de enero</strong> de cada año.
        Las actualizaciones de variación son antes del 15 de marzo, junio, septiembre y diciembre.
      </p>
      <a href="{portal_url}"
         style="display:inline-block;background-color:#0a1628;background:linear-gradient(135deg,#0a1628,#1a3a6b);
                color:#C8A951;text-decoration:none;font-size:15px;font-weight:700;
                padding:14px 44px;border-radius:50px;letter-spacing:0.5px;">
        📋 Acceder al Portal AR-I
      </a>
    </td>
  </tr>

  <!-- ── ACK SECTION ── -->
  <tr>
    <td style="background:#f8faff;padding:24px 40px 32px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background-color:#052e16;background:linear-gradient(135deg,#052e16,#14532d);
                     border-radius:12px;padding:24px 28px;text-align:center;">
            <div class="gbs"><div class="gbd">
            <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#86efac;
                      letter-spacing:2px;text-transform:uppercase;">Confirmación de Lectura</p>
            <p style="margin:0 0 12px;font-size:17px;font-weight:800;color:#FEFEFE;">
              ¿Ya leíste esta guía?
            </p>
            <p style="margin:0 0 20px;font-size:12px;color:#bbf7d0;line-height:1.7;">
              Haz clic en el botón para confirmar que has leído y comprendido<br/>
              las instrucciones del Portal AR-I. <strong style="color:#FEFEFE;">RR.HH. registrará tu confirmación</strong><br/>
              y tendrás acceso prioritario ante cualquier consulta.
            </p>
            <a href="{ack_url}"
               style="display:inline-block;background:#22c55e;
                      color:#FEFEFE;text-decoration:none;font-size:15px;font-weight:800;
                      padding:14px 48px;border-radius:50px;letter-spacing:0.5px;">
              ✅ Confirmo que leí esta guía
            </a>
            <p style="margin:16px 0 0;font-size:10px;color:#4ade80;line-height:1.5;">
              Un solo clic · Sin iniciar sesión · Tu confirmación queda registrada en el sistema
            </p>
            </div></div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── FOOTER ── -->
  <tr>
    <td style="background:#0a1628;padding:22px 40px;text-align:center;">
      <div style="width:40px;height:40px;border-radius:50%;border:2px solid #C8A951;
                  overflow:hidden;display:block;margin:0 auto 10px;">
        <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"
             alt="Colegio Andrés Bello" width="40" height="40"
             style="display:block;width:40px;height:40px;"/>
      </div>
      <div class="gbs"><div class="gbd">
      <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#C8A951;">
        Recursos Humanos · Colegio Andrés Bello
      </p>
      <p style="margin:0 0 8px;font-size:11px;color:#8badd4;">El Tigre, Venezuela</p>
      <p style="margin:0 0 6px;font-size:11px;color:#4b6080;">
        <a href="mailto:recursoshumanos@ueipab.edu.ve" style="color:#4b6080;text-decoration:none;">
          recursoshumanos@ueipab.edu.ve
        </a>
      </p>
      <p style="margin:0;font-size:10px;color:#2d4060;line-height:1.5;">
        Base legal: Decreto N.° 1.808 · Gaceta Oficial N.° 36.203 (12-May-1997)<br/>
        LISLR Arts. 57, 59, 61 · Art. 7 Reglamento Parcial LISLR en Materia de Retenciones
      </p>
      </div></div>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def get_or_create_ack(call, employee_id, web_base):
    """Return (ack_id, token_url) — reuse existing pending ACK if present."""
    existing = call('hr.notice.acknowledgment', 'search_read',
                    [[['employee_id', '=', employee_id],
                      ['notice_key', '=', NOTICE_KEY],
                      ['state', '=', 'pending']]],
                    {'fields': ['id', 'token'], 'limit': 1})
    if existing:
        token = existing[0]['token']
    else:
        ack_id = call('hr.notice.acknowledgment', 'create', [[{
            'employee_id': employee_id,
            'notice_key' : NOTICE_KEY,
        }]])
        # Odoo 17 create_multi returns a list of IDs
        if isinstance(ack_id, list):
            ack_id = ack_id[0]
        rec = call('hr.notice.acknowledgment', 'read', [[ack_id]], {'fields': ['token']})[0]
        token = rec['token']
    return f"{web_base}/notice-ack/{token}"


def _make_call(env_name):
    url, db, uid, key = ENVS[env_name]
    m = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    def call(model, method, args=None, kw=None):
        return m.execute_kw(db, uid, key, model, method, args or [], kw or {})
    return call


def send_test(env_name, employee_id, employee_name, to_email):
    call     = _make_call(env_name)
    web_base = WEB_BASE[env_name]
    portal   = PORTAL_URL[env_name]

    ack_url = get_or_create_ack(call, employee_id, web_base)
    body    = build_body(employee_name, ack_url, portal)

    new_id = call('mail.mail', 'create', [[{
        'subject'   : SUBJECT,
        'body_html' : body,
        'email_to'  : to_email,
        'email_from': FROM,
        'email_cc'  : CC,
        'state'     : 'outgoing',
    }]])
    call('ir.cron', 'method_direct_trigger', [[3]])
    print(f"✓ [{env_name}] mail.mail id={new_id} → {to_email}  (ack: {ack_url})")
    return new_id


# Exclude test accounts (tdv.devs) by email
_EXCLUDE_EMAILS = {'tdv.devs@gmail.com'}
# Exclude employees whose contracts are being terminated (not active)
_EXCLUDE_EMP_IDS = {608}  # RAMON BELLO — contract termination in progress (LIQUID_VE_V2)


def bulk_send(env_name, dry_run=False):
    call     = _make_call(env_name)
    web_base = WEB_BASE[env_name]
    portal   = PORTAL_URL[env_name]

    # Resolve employee list from the latest MAYO31 batch
    batches = call('hr.payslip.run', 'search_read',
                   [[['name', 'ilike', 'MAYO31']]],
                   {'fields': ['id', 'name', 'state'], 'order': 'id desc', 'limit': 1})
    if batches:
        batch = batches[0]
        print(f"Batch: [{batch['id']}] {batch['name']} (state={batch['state']})")
        slips = call('hr.payslip', 'search_read',
                     [[['payslip_run_id', '=', batch['id']]]],
                     {'fields': ['employee_id']})
        emp_ids = list({s['employee_id'][0] for s in slips if s['employee_id']})
    else:
        print("WARNING: No MAYO31 batch found — falling back to open contracts")
        contracts = call('hr.contract', 'search_read',
                         [[['state', '=', 'open']]],
                         {'fields': ['employee_id']})
        emp_ids = list({c['employee_id'][0] for c in contracts if c['employee_id']})

    employees = call('hr.employee', 'read', [emp_ids],
                     {'fields': ['id', 'name', 'work_email']})
    employees = [e for e in employees
                 if e.get('work_email')
                 and e['work_email'] not in _EXCLUDE_EMAILS
                 and e['id'] not in _EXCLUDE_EMP_IDS]
    print(f"Employees to notify: {len(employees)}")

    mail_ids = []
    skipped  = []
    for emp in employees:
        to_email = emp['work_email']
        if dry_run:
            ack_url = f"{web_base}/notice-ack/DRY-RUN"
            print(f"  DRY [{emp['id']}] {emp['name']} → {to_email}")
            continue
        ack_url = get_or_create_ack(call, emp['id'], web_base)
        body    = build_body(emp['name'], ack_url, portal)
        new_id  = call('mail.mail', 'create', [[{
            'subject'   : SUBJECT,
            'body_html' : body,
            'email_to'  : to_email,
            'email_from': FROM,
            'email_cc'  : CC,
            'state'     : 'outgoing',
        }]])
        if isinstance(new_id, list):
            new_id = new_id[0]
        mail_ids.append(new_id)
        print(f"  ✓ [{emp['id']}] {emp['name']} → {to_email}  (mail.mail id={new_id})")

    if not dry_run and mail_ids:
        call('ir.cron', 'method_direct_trigger', [[3]])
        print(f"\nDone: {len(mail_ids)} emails queued and mail cron triggered.")
    elif dry_run:
        print(f"\nDry-run complete — {len(employees)} employees would be notified. Re-run without --dry-run to send.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--env',      choices=['testing', 'production'], default='testing')
    parser.add_argument('--bulk',     action='store_true', help='Send to all MAYO31 batch employees')
    parser.add_argument('--dry-run',  action='store_true', help='List recipients without sending (use with --bulk)')
    parser.add_argument('--to',          default=TO_TEST)
    parser.add_argument('--employee-id', type=int, default=761, help='hr.employee id for ACK token (test mode)')
    parser.add_argument('--employee-name', default='Gustavo Perdomo', help='Display name in urgency banner (test mode)')
    args = parser.parse_args()

    if args.bulk:
        bulk_send(args.env, dry_run=args.dry_run)
    else:
        send_test(args.env, args.employee_id, args.employee_name, args.to)
