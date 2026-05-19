#!/usr/bin/env python3
"""
Staff Guide — Votación Presupuestaria 2026-2027
================================================
Sends an HTML guide to customer support staff explaining how to handle
phone votes, in-person votes, and monitoring via Odoo.

Usage:
    python3 scripts/send_vote_staff_guide.py --live
"""
import argparse, json, logging, sys, xmlrpc.client

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

PROD_CFG  = '/opt/odoo-dev/config/production.json'
ODOO_URL  = 'https://odoo.ueipab.edu.ve'
LOGO_URL  = f'{ODOO_URL}/web/image/res.company/1/logo'
MONITOR_URL = f'{ODOO_URL}/web#action=840&cids=1&menu_id=580'

TO_EMAIL  = 'gustavo.perdomo@ueipab.edu.ve'
TO_NAME   = 'Gustavo Perdomo'

def _connect():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    uid = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")\
              .authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    m   = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    return m, cfg['db'], uid, cfg['api_key']

def _build_html():
    step_style = (
        "display:inline-block;background:#1a2c5b;color:#fff;"
        "border-radius:50%;width:22px;height:22px;text-align:center;"
        "line-height:22px;font-size:12px;font-weight:bold;margin-right:8px;"
        "flex-shrink:0;"
    )
    card_style = (
        "background:#fff;border:1px solid #dde;border-radius:10px;"
        "padding:18px 20px;margin-bottom:16px;"
    )
    scenario_hdr = (
        "background:linear-gradient(90deg,#1a2c5b,#2471a3);color:#fff;"
        "border-radius:8px 8px 0 0;padding:12px 18px;"
        "font-size:14px;font-weight:bold;margin:-18px -20px 16px -20px;"
    )
    tag_style = (
        "display:inline-block;padding:3px 10px;border-radius:12px;"
        "font-size:11px;font-weight:bold;margin-bottom:8px;"
    )
    warn_style = (
        "background:#fff3e0;border-left:4px solid #ff8f00;"
        "border-radius:0 6px 6px 0;padding:10px 14px;margin-top:12px;"
        "font-size:13px;color:#e65100;"
    )
    info_style = (
        "background:#e8f0fb;border-left:4px solid #1a2c5b;"
        "border-radius:0 6px 6px 0;padding:10px 14px;margin-top:12px;"
        "font-size:13px;color:#1a2c5b;"
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Guía Staff — Votación 2026-2027</title>
</head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;">
<tr><td align="center" style="padding:28px 12px;">
<table cellpadding="0" cellspacing="0" width="620"
       style="max-width:620px;background:#fff;border-radius:14px;overflow:hidden;
              box-shadow:0 4px 24px rgba(0,0,0,0.11);">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
               padding:30px 32px;text-align:center;">
      <img src="{LOGO_URL}" width="64" height="64" alt="Logo"
           style="border-radius:50%;border:3px solid rgba(255,255,255,0.3);
                  display:block;margin:0 auto 14px;"/>
      <div style="display:inline-block;background:rgba(255,255,255,0.18);
                  border:1px solid rgba(255,255,255,0.4);border-radius:20px;
                  padding:5px 18px;margin-bottom:10px;">
        <span style="color:rgba(255,255,255,0.85);font-size:12px;font-weight:bold;">
          USO INTERNO — STAFF ÚNICAMENTE
        </span>
      </div>
      <h1 style="margin:0;color:#fff;font-size:20px;font-weight:bold;">
        📋 Guía Operativa — Votación Presupuestaria 2026-2027
      </h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">
        Cómo registrar votos por teléfono, presencial y monitorear desde Odoo
      </p>
    </td>
  </tr>

  <!-- INTRO -->
  <tr>
    <td style="padding:22px 32px 8px;">
      <p style="margin:0;font-size:14px;color:#333;line-height:1.7;">
        Esta guía cubre los <strong>tres canales de voto</strong> disponibles
        y cómo manejarlos desde Odoo. Cada voto queda registrado con auditoría completa
        (usuario, canal, fecha y hora).
      </p>
      <!-- Quick facts -->
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f0f4fa;border-radius:8px;margin-top:16px;">
        <tr>
          <td style="padding:12px 18px;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td width="33%" style="text-align:center;padding:6px;">
                  <div style="font-size:24px;font-weight:bold;color:#1a2c5b;">177</div>
                  <div style="font-size:11px;color:#666;">Familias elegibles</div>
                </td>
                <td width="33%" style="text-align:center;padding:6px;
                    border-left:1px solid #dde;border-right:1px solid #dde;">
                  <div style="font-size:24px;font-weight:bold;color:#e65100;">89</div>
                  <div style="font-size:11px;color:#666;">Meta (50%+1)</div>
                </td>
                <td width="33%" style="text-align:center;padding:6px;">
                  <div style="font-size:24px;font-weight:bold;color:#2e7d32;">22–23 mayo</div>
                  <div style="font-size:11px;color:#666;">Período de votación</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- NAV ODOO -->
  <tr>
    <td style="padding:16px 32px 4px;">
      <div style="{card_style}">
        <div style="{scenario_hdr}">🖥️ Cómo llegar al registro de votos en Odoo</div>
        <p style="margin:0 0 10px;font-size:13px;color:#555;">
          Todos los registros están en:
          <strong>AI Agent → Operaciones → Comunicados a Representantes</strong>
        </p>
        <a href="{MONITOR_URL}"
           style="display:inline-block;background:#1a2c5b;color:#fff;
                  padding:9px 20px;border-radius:7px;font-size:13px;
                  font-weight:bold;text-decoration:none;">
          🔗 Abrir en Odoo →
        </a>
        <div style="{info_style}">
          <strong>Filtro rápido:</strong> Busca la campaña
          <code>budget_consulta_2026_2027</code> en el campo "Campaña".
          Usa <strong>Agrupar por → Decisión</strong> para ver el conteo en tiempo real.
        </div>
        <div style="margin-top:12px;font-size:13px;color:#555;">
          <strong>Colores:</strong> &nbsp;
          🟡 Amarillo = Pendiente &nbsp;|&nbsp;
          🟢 Verde = Opción A &nbsp;|&nbsp;
          🔵 Azul = Opción B
        </div>
      </div>
    </td>
  </tr>

  <!-- ESCENARIO 1: TELÉFONO -->
  <tr>
    <td style="padding:4px 32px;">
      <div style="{card_style}">
        <div style="{scenario_hdr}">📞 Escenario 1 — Representante vota por teléfono</div>

        <div style="display:flex;align-items:flex-start;margin-bottom:10px;">
          <span style="{step_style}">1</span>
          <span style="font-size:13px;color:#333;">
            Busca al representante en la lista de Comunicados a Representantes.
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:10px;">
          <span style="{step_style}">2</span>
          <span style="font-size:13px;color:#333;">
            Abre su registro haciendo clic en su nombre.
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:10px;">
          <span style="{step_style}">3</span>
          <span style="font-size:13px;color:#333;">
            Haz clic en <strong>"📞 Registrar voto asistido"</strong>
            (solo aparece si el estado es <em>Pendiente</em>).
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:10px;">
          <span style="{step_style}">4</span>
          <span style="font-size:13px;color:#333;">
            En el wizard: selecciona <strong>Opción A o B</strong>,
            canal = <strong>Teléfono</strong>, y escribe una nota breve
            (ej: <em>"Llamada entrante 10:32am, confirmó verbalmente Opción A"</em>).
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;">
          <span style="{step_style}">5</span>
          <span style="font-size:13px;color:#333;">
            Haz clic en <strong>"✅ Confirmar voto"</strong>.
            El sistema registra: tu usuario, canal=Teléfono, fecha/hora y la nota.
          </span>
        </div>
        <div style="{warn_style}">
          ⚠️ <strong>Antes de registrar:</strong> verifica que el representante
          esté solvente (2025-2026 al día). Si tiene deuda, orienta a
          <a href="mailto:pagos@ueipab.edu.ve">pagos@ueipab.edu.ve</a> primero.
        </div>
      </div>
    </td>
  </tr>

  <!-- ESCENARIO 2: PRESENCIAL -->
  <tr>
    <td style="padding:4px 32px;">
      <div style="{card_style}">
        <div style="{scenario_hdr}">🏫 Escenario 2 — Representante vota presencialmente en la oficina</div>

        <p style="margin:0 0 12px;font-size:13px;color:#555;">
          <strong>Opción A — El representante vota él mismo (recomendada):</strong>
        </p>
        <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
          <span style="{step_style}">1</span>
          <span style="font-size:13px;color:#333;">
            Busca y abre el registro del representante en Odoo.
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
          <span style="{step_style}">2</span>
          <span style="font-size:13px;color:#333;">
            Haz clic en <strong>"Abrir formulario de voto (tablet)"</strong>
            — se abre la página de votación en una nueva pestaña.
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:16px;">
          <span style="{step_style}">3</span>
          <span style="font-size:13px;color:#333;">
            Entrega la tablet al representante. Él elige su opción directamente.
            El sistema registra la IP de la oficina como evidencia presencial.
          </span>
        </div>

        <p style="margin:0 0 12px;font-size:13px;color:#555;">
          <strong>Opción B — Staff registra en nombre del representante:</strong>
        </p>
        <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
          <span style="{step_style}">1</span>
          <span style="font-size:13px;color:#333;">
            Usa el botón <strong>"📞 Registrar voto asistido"</strong>,
            canal = <strong>Presencial</strong>.
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;">
          <span style="{step_style}">2</span>
          <span style="font-size:13px;color:#333;">
            Anota en el campo de notas:
            <em>"Representante presente en oficina. Confirmó Opción X verbalmente. Cédula: V-XXXXXXXX"</em>.
          </span>
        </div>
      </div>
    </td>
  </tr>

  <!-- ESCENARIO 3: CORREO REBOTÓ / GLENDA -->
  <tr>
    <td style="padding:4px 32px;">
      <div style="{card_style}">
        <div style="{scenario_hdr}">💬 Escenario 3 — Correo rebotó / representante no recibió el email</div>

        <div style="{info_style}" style="margin-bottom:12px;">
          🤖 <strong>Glenda lo maneja automáticamente.</strong>
          El sistema detecta correos rebotados y envía un WhatsApp al representante
          con las opciones y el enlace a la presentación. El representante responde
          <strong>A</strong> o <strong>B</strong> y Glenda registra el voto.
        </div>

        <p style="margin:12px 0 8px;font-size:13px;color:#555;">
          <strong>Si el representante llama y dice que no recibió el correo:</strong>
        </p>
        <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
          <span style="{step_style}">1</span>
          <span style="font-size:13px;color:#333;">
            Revisa si tiene estado <em>Pendiente</em> en Comunicados a Representantes.
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;margin-bottom:8px;">
          <span style="{step_style}">2</span>
          <span style="font-size:13px;color:#333;">
            Si ya recibió el WA de Glenda: dile que responda A o B por WhatsApp.
          </span>
        </div>
        <div style="display:flex;align-items:flex-start;">
          <span style="{step_style}">3</span>
          <span style="font-size:13px;color:#333;">
            Si prefiere votar por teléfono en ese momento: usa
            <strong>"📞 Registrar voto asistido"</strong> directamente.
          </span>
        </div>

        <p style="margin:14px 0 4px;font-size:13px;color:#555;">
          <strong>Monitoreo de votos WA en FreeScout:</strong>
          Revisa el buzón <strong>votacion@ueipab.edu.ve</strong> — cada rebote
          abre una conversación. Cerrada = votó. Abierta = pendiente de seguimiento.
        </p>
      </div>
    </td>
  </tr>

  <!-- REGLAS CLAVE -->
  <tr>
    <td style="padding:4px 32px;">
      <div style="{card_style}">
        <div style="{scenario_hdr}">⚖️ Reglas clave — leer antes de actuar</div>
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td style="padding:5px 0;font-size:13px;color:#333;vertical-align:top;">
              ✅ <strong>Un voto por familia.</strong>
              El sistema bloquea automáticamente un segundo voto.
            </td>
          </tr>
          <tr>
            <td style="padding:5px 0;font-size:13px;color:#333;vertical-align:top;">
              ✅ <strong>Verifica identidad</strong> antes de registrar:
              nombre completo + cédula del representante registrado.
            </td>
          </tr>
          <tr>
            <td style="padding:5px 0;font-size:13px;color:#333;vertical-align:top;">
              ✅ <strong>Siempre usa el wizard</strong> — nunca cambies el estado manualmente
              desde el campo de estado; el wizard registra tu usuario como evidencia.
            </td>
          </tr>
          <tr>
            <td style="padding:5px 0;font-size:13px;color:#333;vertical-align:top;">
              ✅ <strong>Escribe la nota</strong> en el campo de auditoría —
              es el respaldo legal si hay impugnación.
            </td>
          </tr>
          <tr>
            <td style="padding:5px 0;font-size:13px;color:#e53935;vertical-align:top;">
              ❌ <strong>No registres votos sin confirmación explícita</strong>
              del representante ("Opción A" o "Opción B").
            </td>
          </tr>
          <tr>
            <td style="padding:5px 0;font-size:13px;color:#e53935;vertical-align:top;">
              ❌ <strong>No uses "Reiniciar a Pendiente"</strong> salvo error comprobado
              y con autorización de dirección.
            </td>
          </tr>
        </table>
      </div>
    </td>
  </tr>

  <!-- MONITORING -->
  <tr>
    <td style="padding:4px 32px;">
      <div style="{card_style}">
        <div style="{scenario_hdr}">📊 Monitoreo en tiempo real</div>
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#333;vertical-align:top;">
              📧 <strong>Digest automático</strong> cada 15 min a la dirección →
              incluye tally A/B y barra de progreso hacia la meta (89 votos).
            </td>
          </tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#333;vertical-align:top;">
              🖥️ <strong>Lista en vivo:</strong>
              <a href="{MONITOR_URL}" style="color:#1a2c5b;">
                AI Agent → Operaciones → Comunicados a Representantes
              </a>
              → Agrupar por Decisión.
            </td>
          </tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#333;vertical-align:top;">
              💬 <strong>FreeScout votacion@:</strong> convs abiertas = esperando WA de Glenda.
              Cerradas = voto registrado.
            </td>
          </tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#333;vertical-align:top;">
              📌 <strong>Período:</strong> 22–23 mayo 2026.
              Resultados: <strong>26 mayo 2026</strong>.
            </td>
          </tr>
        </table>
        <a href="{MONITOR_URL}"
           style="display:inline-block;margin-top:12px;background:#1a2c5b;color:#fff;
                  padding:9px 20px;border-radius:7px;font-size:13px;
                  font-weight:bold;text-decoration:none;">
          📊 Ver tally en vivo →
        </a>
      </div>
    </td>
  </tr>

  <!-- CONTACT -->
  <tr>
    <td style="padding:4px 32px 24px;">
      <div style="background:#f8f9fa;border-radius:8px;padding:14px 18px;
                  font-size:13px;color:#555;text-align:center;">
        ¿Dudas sobre el proceso?
        Escribe a <a href="mailto:votacion@ueipab.edu.ve"
                     style="color:#1a2c5b;font-weight:bold;">votacion@ueipab.edu.ve</a>
        o contacta a dirección.
      </div>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#f8f9fa;border-top:1px solid #e0e0e0;
               padding:14px 32px;text-align:center;">
      <p style="margin:0;font-size:11px;color:#aaa;">
        Documento interno — Consulta Presupuestaria 2026-2027 ·
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def main(live):
    m, db, uid, key = _connect()
    html = _build_html()

    if not live:
        log.info("DRY RUN — would send staff guide to %s", TO_EMAIL)
        return

    mail_id = m.execute_kw(db, uid, key, 'mail.mail', 'create', [[{
        'subject':    '📋 Guía Staff — Cómo registrar votos presupuestarios en Odoo',
        'email_from': 'Colegio Andrés Bello <votacion@ueipab.edu.ve>',
        'email_to':   f'{TO_NAME} <{TO_EMAIL}>',
        'body_html':  html,
        'state':      'outgoing',
    }]])
    result = m.execute_kw(db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])
    log.info("Sent — mail.mail id=%s", mail_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    main(live=args.live)
