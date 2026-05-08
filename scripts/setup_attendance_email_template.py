"""
Updates the "Guía Visual de Asistencia" mail.template (id=83) in testing DB.
Fixes:
  - Employee name now uses QWeb  <t t-out="object.name"/>  (not Jinja2)
  - School logo added to header
  - Title updated to "REGISTRO DE CONTROL DE ASISTENCIA"
  - body_html set via direct SQL to bypass ORM Html sanitizer
  - Test recipient: gustavo.perdomo@ueipab.edu.ve

Run with:
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < /opt/odoo-dev/scripts/setup_attendance_email_template.py
"""
import json

BASE_URL  = "https://dev.ueipab.edu.ve/flyers"
LOGO_URL  = f"{BASE_URL}/ueipab_logo.png"
TMPL_ID   = 83

BODY = f"""<div style="margin:0;padding:0;background-color:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">

  <!-- WRAPPER -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f0f4fa;padding:24px 10px;">
    <tr>
      <td align="center">
        <table width="620" cellpadding="0" cellspacing="0"
               style="max-width:620px;width:100%;background:#ffffff;
                      border-radius:14px;overflow:hidden;
                      box-shadow:0 4px 18px rgba(0,0,0,0.10);">

          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
                       padding:28px 40px 24px;text-align:center;">
              <img src="{LOGO_URL}" height="72" alt="Instituto Andrés Bello"
                   style="display:block;margin:0 auto 16px;max-width:320px;">
              <div style="color:#ffffff;font-size:22px;font-weight:bold;
                          line-height:1.25;margin-bottom:8px;">
                GESTI&Oacute;N DE CONTROL<br>DE ASISTENCIA
              </div>
              <div style="display:inline-block;background:rgba(255,255,255,0.15);
                          border-radius:20px;padding:6px 20px;margin-top:4px;">
                <span style="color:#ffffff;font-size:13px;">
                  Guía visual para todos los empleados &nbsp;|&nbsp; Mayo 2026
                </span>
              </div>
            </td>
          </tr>

          <!-- GREETING — uses QWeb t-out for employee name -->
          <tr>
            <td style="padding:28px 40px 16px;">
              <p style="margin:0 0 12px;color:#1a2c5b;font-size:16px;font-weight:bold;">
                Estimado/a
                <span style="color:#2471a3;"><t t-out="object.name"/></span>,
              </p>
              <p style="margin:0;color:#444;font-size:15px;line-height:1.65;">
                Le compartimos una <strong>guía visual en 4 partes</strong> sobre el sistema de
                gestión de control de asistencia. Por favor revise cada sección deslizando
                las tarjetas hacia la derecha.
              </p>
            </td>
          </tr>

          <!-- STORY CAROUSEL -->
          <tr>
            <td style="padding:8px 28px 22px;">
              <p style="margin:0 0 10px;color:#2471a3;font-size:12px;font-weight:bold;
                        letter-spacing:0.5px;">
                &#8592; &nbsp; DESLICE PARA VER LAS 4 PARTES &nbsp; &#8594;
              </p>
              <div style="overflow-x:auto;-webkit-overflow-scrolling:touch;
                          white-space:nowrap;padding-bottom:6px;">
                <table cellpadding="0" cellspacing="0"
                       style="border-collapse:separate;border-spacing:0;">
                  <tr>

                    <td style="padding:0 10px 0 0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #1a2c5b;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s1.png"
                             width="210" height="373" alt="Parte 1"
                             style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;
                                color:#2471a3;font-weight:bold;width:216px;">
                        1 &middot; EL SISTEMA
                      </p>
                    </td>

                    <td style="padding:0 10px 0 0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #2471a3;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s2.png"
                             width="210" height="373" alt="Parte 2"
                             style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;
                                color:#2471a3;font-weight:bold;width:216px;">
                        2 &middot; C&Oacute;MO REGISTRAR
                      </p>
                    </td>

                    <td style="padding:0 10px 0 0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #2471a3;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s3.png"
                             width="210" height="373" alt="Parte 3"
                             style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;
                                color:#2471a3;font-weight:bold;width:216px;">
                        3 &middot; TU REPORTE QUINCENAL
                      </p>
                    </td>

                    <td style="padding:0;vertical-align:top;white-space:normal;width:216px;">
                      <div style="border-radius:12px;overflow:hidden;border:3px solid #2471a3;display:inline-block;">
                        <img src="{BASE_URL}/asistencia_story_s4.png"
                             width="210" height="373" alt="Parte 4"
                             style="display:block;">
                      </div>
                      <p style="margin:6px 0 0;text-align:center;font-size:11px;
                                color:#2471a3;font-weight:bold;width:216px;">
                        4 &middot; QU&Eacute; DEBES HACER
                      </p>
                    </td>

                  </tr>
                </table>
              </div>
            </td>
          </tr>

          <!-- QUICK SUMMARY -->
          <tr>
            <td style="padding:4px 40px 18px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#f0f4fa;border-radius:10px;border-left:5px solid #1a2c5b;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 14px;color:#1a2c5b;font-size:15px;
                               font-weight:bold;letter-spacing:0.3px;">
                      RESUMEN R&Aacute;PIDO
                    </p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">
                      &#10004; &nbsp;<strong>Kiosko</strong> (Oficina de Administraci&oacute;n) &mdash;
                      m&eacute;todo obligatorio para todos
                    </p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">
                      &#10004; &nbsp;<strong>Dashboard Odoo &rarr; Check In/Out</strong> &mdash;
                      contingencia digital (usuarios con cuenta Odoo)
                    </p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">
                      &#10004; &nbsp;<strong>Control de Asistencias / WiFi</strong> &mdash;
                      contingencia autom&aacute;tica seg&uacute;n rol
                    </p>
                    <p style="margin:0 0 9px;color:#333;font-size:14px;line-height:1.5;">
                      &#10004; &nbsp;Recibir&aacute; un <strong>reporte quincenal</strong> por correo
                      los d&iacute;as 1 y 16 de cada mes
                    </p>
                    <p style="margin:0;color:#333;font-size:14px;line-height:1.5;">
                      &#10004; &nbsp;Confirme la recepci&oacute;n con el
                      <strong style="color:#28a745;">bot&oacute;n verde</strong> en el reporte
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- IMPORTANT DATE -->
          <tr>
            <td style="padding:0 40px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#fde8e8;border-radius:10px;border-left:5px solid #dc3545;">
                <tr>
                  <td style="padding:16px 22px;">
                    <p style="margin:0 0 6px;color:#721c24;font-size:14px;font-weight:bold;">
                      &#9888; IMPORTANTE &mdash; A PARTIR DEL 1 DE JUNIO 2026
                    </p>
                    <p style="margin:0;color:#721c24;font-size:13px;line-height:1.55;">
                      Las ausencias injustificadas podr&aacute;n generar
                      <strong>descuentos en n&oacute;mina</strong>.
                      Reporte cualquier error de registro
                      <strong>antes del cierre de cada quincena</strong>
                      usando el enlace en el correo del reporte.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CONTACT -->
          <tr>
            <td style="padding:0 40px 28px;text-align:center;">
              <p style="margin:0 0 4px;color:#888;font-size:13px;">
                &iquest;Preguntas o correcciones de registro?
              </p>
              <p style="margin:0;color:#2471a3;font-size:15px;font-weight:bold;">
                recursoshumanos@ueipab.edu.ve
              </p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background:#1a2c5b;padding:22px 40px;text-align:center;">
              <p style="margin:0 0 4px;color:#adc8e6;font-size:13px;">Cordialmente,</p>
              <p style="margin:0 0 2px;color:#ffffff;font-size:15px;font-weight:bold;">
                Recursos Humanos
              </p>
              <p style="margin:0;color:#adc8e6;font-size:13px;">
                Instituto Privado Andr&eacute;s Bello, C.A. &nbsp;|&nbsp; El Tigre, Anzo&aacute;tegui
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</div>"""

# ── Update template via direct SQL — write ALL language keys ────────────────────
# System lang is es_VE; ORM reads that key. Must update en_US AND es_VE together.
SUBJECT = "Gestion de Control de Asistencia - Guia Visual | Andres Bello"
body_jsonb    = json.dumps({'en_US': BODY,    'es_VE': BODY})
subject_jsonb = json.dumps({'en_US': SUBJECT, 'es_VE': SUBJECT})

env.cr.execute(
    "UPDATE mail_template SET body_html = %s::jsonb, subject = %s::jsonb, email_to = %s WHERE id = %s",
    [body_jsonb, subject_jsonb, "gustavo.perdomo@ueipab.edu.ve", TMPL_ID]
)
env.cr.commit()
print(f"Template {TMPL_ID} — body_html (en_US + es_VE) updated via SQL — OK")

# ── Send test emails ─────────────────────────────────────────────────────────────
tmpl = env['mail.template'].browse(TMPL_ID)

test_recipients = [
    'gustavo.perdomo@ueipab.edu.ve',
    'alberto.perdomo@ueipab.edu.ve',
]

for email in test_recipients:
    emp = env['hr.employee'].search([('work_email', 'ilike', email.split('@')[0])], limit=1)
    if not emp:
        emp = env['hr.employee'].search([], limit=1)
    # Override email_to for this send
    msg_id = tmpl.send_mail(emp.id, force_send=True,
                             email_values={'email_to': email})
    env.cr.commit()
    print(f"Sent to {email}  (record: {emp.name})  mail.mail id={msg_id}")
