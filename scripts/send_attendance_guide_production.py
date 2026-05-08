#!/usr/bin/env python3
"""
Gestión de Control de Asistencia — Guía Visual
Crea el mail.template en producción (DB_UEIPAB) y envía a todos los empleados.

Uso (directamente en el host, NO via docker exec):
  python3 /opt/odoo-dev/scripts/send_attendance_guide_production.py

Conecta a producción via XML-RPC. Usa psycopg2 inside Docker para el JSONB fix.
"""

import json
import xmlrpc.client

# ── Production config ─────────────────────────────────────────────────────────
with open('/opt/odoo-dev/config/production.json') as f:
    cfg = json.load(f)['production']['xmlrpc']

PROD_URL = cfg['url']        # https://odoo.ueipab.edu.ve
PROD_DB  = cfg['db']         # DB_UEIPAB
PROD_USER = cfg['user']
PROD_KEY  = cfg['api_key']

common = xmlrpc.client.ServerProxy(f"{PROD_URL}/xmlrpc/2/common")
models = xmlrpc.client.ServerProxy(f"{PROD_URL}/xmlrpc/2/object")

PROD_UID = common.authenticate(PROD_DB, PROD_USER, PROD_KEY, {})
print(f"Authenticated as uid={PROD_UID} on {PROD_URL}")

# ── Template config ───────────────────────────────────────────────────────────
BASE_URL    = "https://dev.ueipab.edu.ve/flyers"
LOGO_URL    = f"{BASE_URL}/ueipab_logo.png"
TMPL_NAME   = "Gestión de Control de Asistencia — Guía Visual para Empleados"
SUBJECT_STR = "Gestión de Control de Asistencia - Guía Visual | Andrés Bello"

# ── Recipients ────────────────────────────────────────────────────────────────
RECIPIENTS = [
    "alejandra.lopez@ueipab.edu.ve",
    "andres.morales@ueipab.edu.ve",
    "arcides.arzola@ueipab.edu.ve",
    "audrey.garcia@ueipab.edu.ve",
    "camila.rossato@ueipab.edu.ve",
    "daniel.bongianni@ueipab.edu.ve",
    "david.hernandez@ueipab.edu.ve",
    "dixia.bellorin@ueipab.edu.ve",
    "elis.mejias@ueipab.edu.ve",
    "emilio.isea@ueipab.edu.ve",
    "flormar.hernandez@ueipab.edu.ve",
    "gabriel.espana@ueipab.edu.ve",
    "gabriela.uray@ueipab.edu.ve",
    "giovanni.vezza@ueipab.edu.ve",
    "gladys.brito@ueipab.edu.ve",
    "heydi.ron@ueipab.edu.ve",
    "ismary.arcila@ueipab.edu.ve",
    "jessica.bolivar@ueipab.edu.ve",
    "jesus.dicesare@ueipab.edu.ve",
    "jose.hernandez@ueipab.edu.ve",
    "josefina.rodriguez@ueipab.edu.ve",
    "laray@ueipab.edu.ve",
    "lorena.reyes@ueipab.edu.ve",
    "luis.rodriguez@ueipab.edu.ve",
    "luisa.abreu@ueipab.edu.ve",
    "magyelis.mata@ueipab.edu.ve",
    "mairelsy.motta@ueipab.edu.ve",
    "maria.figuera@ueipab.edu.ve",
    "maria.nieto@ueipab.edu.ve",
    "mariela.prado@ueipab.edu.ve",
    "mirian.hernandez@ueipab.edu.ve",
    "nelci.brito@ueipab.edu.ve",
    "nidya.lira@ueipab.edu.ve",
    "norka.larosa@ueipab.edu.ve",
    "pablo.navarro@ueipab.edu.ve",
    "rafael.perez@ueipab.edu.ve",
    "ramon.bello@ueipab.edu.ve",
    "robert.quijada@ueipab.edu.ve",
    "sergio.maneiro@ueipab.edu.ve",
    "teresa.marin@ueipab.edu.ve",
    "virginia.verde@ueipab.edu.ve",
    "yaritza.bruces@ueipab.edu.ve",
    "yudelys.brito@ueipab.edu.ve",
    "zareth.farias@ueipab.edu.ve",
    "gustavo.perdomo@ueipab.edu.ve",
    "alberto.perdomo@ueipab.edu.ve",
]

# ── Email body (QWeb syntax for employee name) ────────────────────────────────
BODY = f"""<div style="margin:0;padding:0;background-color:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4fa;padding:24px 10px;">
    <tr>
      <td align="center">
        <table width="620" cellpadding="0" cellspacing="0"
               style="max-width:620px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 4px 18px rgba(0,0,0,0.10);">
          <tr>
            <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);padding:28px 40px 24px;text-align:center;">
              <img src="{LOGO_URL}" height="72" alt="Instituto Andrés Bello"
                   style="display:block;margin:0 auto 16px;max-width:320px;">
              <div style="color:#ffffff;font-size:22px;font-weight:bold;line-height:1.25;margin-bottom:8px;">
                GESTI&Oacute;N DE CONTROL<br>DE ASISTENCIA
              </div>
              <div style="display:inline-block;background:rgba(255,255,255,0.15);border-radius:20px;padding:6px 20px;margin-top:4px;">
                <span style="color:#ffffff;font-size:13px;">Guía visual para todos los empleados &nbsp;|&nbsp; Mayo 2026</span>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 40px 16px;">
              <p style="margin:0 0 12px;color:#1a2c5b;font-size:16px;font-weight:bold;">
                Estimado/a <span style="color:#2471a3;"><t t-out="object.name"/></span>,
              </p>
              <p style="margin:0;color:#444;font-size:15px;line-height:1.65;">
                Le compartimos una <strong>guía visual en 4 partes</strong> sobre el sistema de
                gestión de control de asistencia. Por favor revise cada sección deslizando
                las tarjetas hacia la derecha.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 28px 22px;">
              <p style="margin:0 0 10px;color:#2471a3;font-size:12px;font-weight:bold;letter-spacing:0.5px;">
                &#8592; &nbsp; DESLICE PARA VER LAS 4 PARTES &nbsp; &#8594;
              </p>
              <div style="overflow-x:auto;-webkit-overflow-scrolling:touch;white-space:nowrap;padding-bottom:6px;">
                <table cellpadding="0" cellspacing="0" style="border-collapse:separate;border-spacing:0;">
                  <tr>
                    <td style="padding:0 10px 0 0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #1a2c5b;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s1.png" width="210" height="373" alt="Parte 1" style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;color:#2471a3;font-weight:bold;width:216px;">1 &middot; EL SISTEMA</p>
                    </td>
                    <td style="padding:0 10px 0 0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #2471a3;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s2.png?v=2" width="210" height="373" alt="Parte 2" style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;color:#2471a3;font-weight:bold;width:216px;">2 &middot; C&Oacute;MO REGISTRAR</p>
                    </td>
                    <td style="padding:0 10px 0 0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #2471a3;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s3.png" width="210" height="373" alt="Parte 3" style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;color:#2471a3;font-weight:bold;width:216px;">3 &middot; TU REPORTE QUINCENAL</p>
                    </td>
                    <td style="padding:0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #2471a3;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s4.png" width="210" height="373" alt="Parte 4" style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;color:#2471a3;font-weight:bold;width:216px;">4 &middot; QU&Eacute; DEBES HACER</p>
                    </td>
                  </tr>
                </table>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:4px 40px 18px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#f0f4fa;border-radius:10px;border-left:5px solid #1a2c5b;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 14px;color:#1a2c5b;font-size:15px;font-weight:bold;letter-spacing:0.3px;">RESUMEN R&Aacute;PIDO</p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">&#10004; &nbsp;<strong>Kiosko</strong> (Oficina de Administraci&oacute;n) &mdash; m&eacute;todo obligatorio para todos</p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">&#10004; &nbsp;<strong>Dashboard Odoo &rarr; Check In/Out</strong> &mdash; contingencia digital (usuarios con cuenta Odoo)</p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">&#10004; &nbsp;<strong>Control de Asistencias / WiFi</strong> &mdash; contingencia autom&aacute;tica seg&uacute;n rol</p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">&#10004; &nbsp;Recibir&aacute; un <strong>reporte quincenal</strong> por correo los d&iacute;as 1 y 16 de cada mes</p>
                    <p style="margin:0;color:#333;font-size:14px;line-height:1.5;">&#10004; &nbsp;Confirme la recepci&oacute;n con el <strong style="color:#28a745;">bot&oacute;n verde</strong> en el reporte</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#fde8e8;border-radius:10px;border-left:5px solid #dc3545;">
                <tr>
                  <td style="padding:16px 22px;">
                    <p style="margin:0 0 6px;color:#721c24;font-size:14px;font-weight:bold;">&#9888; IMPORTANTE &mdash; A PARTIR DEL 1 DE JUNIO 2026</p>
                    <p style="margin:0;color:#721c24;font-size:13px;line-height:1.55;">
                      Las ausencias injustificadas podr&aacute;n generar <strong>descuentos en n&oacute;mina</strong>.
                      Reporte cualquier error de registro <strong>antes del cierre de cada quincena</strong>
                      usando el enlace en el correo del reporte.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:0 40px 28px;text-align:center;">
              <p style="margin:0 0 4px;color:#888;font-size:13px;">&iquest;Preguntas o correcciones de registro?</p>
              <p style="margin:0;color:#2471a3;font-size:15px;font-weight:bold;">recursoshumanos@ueipab.edu.ve</p>
            </td>
          </tr>
          <tr>
            <td style="background:#1a2c5b;padding:22px 40px;text-align:center;">
              <p style="margin:0 0 4px;color:#adc8e6;font-size:13px;">Cordialmente,</p>
              <p style="margin:0 0 2px;color:#ffffff;font-size:15px;font-weight:bold;">Recursos Humanos</p>
              <p style="margin:0;color:#adc8e6;font-size:13px;">Instituto Privado Andr&eacute;s Bello, C.A. &nbsp;|&nbsp; El Tigre, Anzo&aacute;tegui</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</div>"""

# ── Step 1: Find or create mail.template via XML-RPC ─────────────────────────
existing = models.execute_kw(
    PROD_DB, PROD_UID, PROD_KEY,
    'mail.template', 'search',
    [[['name', '=', TMPL_NAME]]], {'limit': 1}
)

tmpl_vals = {
    'name':       TMPL_NAME,
    'model':      'hr.employee',
    'subject':    SUBJECT_STR,
    'body_html':  BODY,
    'email_from': '"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>',
    'email_to':   '{{ object.work_email }}',
    'auto_delete': False,
}

if existing:
    tmpl_id = existing[0]
    models.execute_kw(PROD_DB, PROD_UID, PROD_KEY,
                      'mail.template', 'write', [[tmpl_id], tmpl_vals])
    print(f"Template UPDATED — prod id={tmpl_id}")
else:
    tmpl_id = models.execute_kw(PROD_DB, PROD_UID, PROD_KEY,
                                'mail.template', 'create', [tmpl_vals])
    print(f"Template CREATED — prod id={tmpl_id}")

# ── Step 2: Fix body_html JSONB — write both language keys via XML-RPC ────────
# The ORM create() only writes the current lang key; we need en_US AND es_VE.
# Solution: write() with explicit lang context for each language.
lang_fix_vals = {'body_html': BODY, 'subject': SUBJECT_STR}

for lang in ('es_VE', 'en_US'):
    models.execute_kw(
        PROD_DB, PROD_UID, PROD_KEY,
        'mail.template', 'write', [[tmpl_id], lang_fix_vals],
        {'context': {'lang': lang}}
    )
    print(f"  body_html written for lang={lang}")
print(f"JSONB multilingual fix done for template id={tmpl_id}")

# ── Step 3: Send to each recipient ───────────────────────────────────────────
print(f"\nSending to {len(RECIPIENTS)} recipients...")
sent_ok, skipped = [], []

for email in RECIPIENTS:
    emp_ids = models.execute_kw(
        PROD_DB, PROD_UID, PROD_KEY,
        'hr.employee', 'search',
        [[['work_email', '=', email], ['active', '=', True]]],
        {'limit': 1}
    )
    if not emp_ids:
        # fallback: ilike match
        emp_ids = models.execute_kw(
            PROD_DB, PROD_UID, PROD_KEY,
            'hr.employee', 'search',
            [[['work_email', 'ilike', email.split('@')[0]], ['active', '=', True]]],
            {'limit': 1}
        )
    if not emp_ids:
        skipped.append(email)
        print(f"  SKIP  {email} — no active employee found")
        continue

    emp_id = emp_ids[0]
    emp_name = models.execute_kw(
        PROD_DB, PROD_UID, PROD_KEY,
        'hr.employee', 'read', [[emp_id]], {'fields': ['name']}
    )[0]['name']

    try:
        msg_id = models.execute_kw(
            PROD_DB, PROD_UID, PROD_KEY,
            'mail.template', 'send_mail',
            [tmpl_id, emp_id],
            {'force_send': True, 'email_values': {'email_to': email}}
        )
        sent_ok.append(email)
        print(f"  OK    {email}  ({emp_name})  msg={msg_id}")
    except Exception as e:
        skipped.append(email)
        print(f"  ERR   {email}  ({emp_name})  {e}")

print(f"\n{'='*60}")
print(f"Sent:    {len(sent_ok)}/{len(RECIPIENTS)}")
if skipped:
    print(f"Skipped: {skipped}")
