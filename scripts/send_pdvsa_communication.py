#!/usr/bin/env python3
"""
Send PDVSA Representative Communication — Período 2026-2027
============================================================
Envía el comunicado sobre el cese del descuento del 35% a todos los
representantes con la etiqueta "Representante PDVSA".

Crea un registro partner.communication.ack por representante y genera
correos mail.mail (state=outgoing) para envío por la cola de Odoo.

Uso (Odoo shell):
    # Dry run — ver destinatarios sin crear registros
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \\
      < /opt/odoo-dev/scripts/send_pdvsa_communication.py

    # Envío real (todos los PDVSA)
    LIVE=true docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \\
      < /opt/odoo-dev/scripts/send_pdvsa_communication.py

    # Probar con un partner específico (usar su ID de Odoo)
    PARTNER_ID=3676 LIVE=true docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \\
      < /opt/odoo-dev/scripts/send_pdvsa_communication.py
"""

import os
import sys
import time

# ── Configuración ─────────────────────────────────────────────────────────────

DRY_RUN    = os.environ.get('LIVE', '').lower() not in ('true', '1', 'yes')
PARTNER_ID = int(os.environ.get('PARTNER_ID', '0'))   # 0 = todos
SEND_DELAY = float(os.environ.get('SEND_DELAY', '0.3'))

NOTICE_KEY   = 'pdvsa_continuacion_2026_2027'
NOTICE_LABEL = 'Comunicado PDVSA — Continuidad Período 2026-2027'
TAG_NAME     = 'Representante PDVSA'

print("=" * 70)
print(f"COMUNICADO PDVSA 2026-2027 — {'*** DRY RUN ***' if DRY_RUN else '*** ENVÍO REAL ***'}")
print("=" * 70)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_email_html(partner_name, si_url, no_url):
    """Return the full HTML email body for the PDVSA communication."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body style="margin:0;padding:0;background-color:#f0f4fa;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f0f4fa;">
    <tr>
      <td align="center" style="padding:30px 10px;">
        <table width="640" cellpadding="0" cellspacing="0" border="0"
               style="max-width:640px;background:#ffffff;border-radius:8px;
                      box-shadow:0 2px 12px rgba(0,0,0,0.10);">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#1a2c5b;padding:32px 36px;
                       border-radius:8px 8px 0 0;text-align:center;">
              <p style="margin:0 0 4px;font-size:11px;color:#a8bfda;
                        letter-spacing:2px;text-transform:uppercase;">
                Instituto Privado
              </p>
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:bold;">
                &ldquo;Andr&eacute;s Bello&rdquo; C.A.
              </h1>
              <p style="margin:8px 0 0;font-size:13px;color:#a8bfda;">
                El Tigre, Estado Anzo&aacute;tegui
              </p>
            </td>
          </tr>

          <!-- DATE + TITLE -->
          <tr>
            <td style="padding:28px 36px 0;border-bottom:2px solid #1a2c5b;">
              <p style="margin:0 0 6px;font-size:12px;color:#888;">
                El Tigre, 08 de mayo de 2026
              </p>
              <h2 style="margin:0 0 20px;font-size:20px;color:#1a2c5b;
                          letter-spacing:1px;text-transform:uppercase;">
                Comunicado
              </h2>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:24px 36px;font-size:14px;color:#333;line-height:1.7;">

              <p style="margin:0 0 18px;">
                <strong>Estimado(a) representante {partner_name}:</strong>
              </p>
              <p style="margin:0 0 18px;">
                Reciba un cordial saludo cargado de gratitud por la confianza depositada
                en el Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;. Como instituci&oacute;n,
                siempre hemos navegado junto a ustedes los desaf&iacute;os econ&oacute;micos
                de nuestro pa&iacute;s, priorizando la permanencia de nuestros alumnos
                por encima de los m&aacute;rgenes financieros.
              </p>

              <!-- Section 1 -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin:0 0 18px;">
                <tr>
                  <td style="border-left:3px solid #2471a3;padding:12px 16px;
                              background:#f8faff;border-radius:0 6px 6px 0;">
                    <p style="margin:0 0 8px;font-size:14px;color:#1a2c5b;font-weight:bold;">
                      1. Cese de la Pol&iacute;tica de Descuento Discrecional (35%)
                    </p>
                    <p style="margin:0;font-size:13px;color:#444;line-height:1.7;">
                      Durante los &uacute;ltimos a&ntilde;os, el colegio realiz&oacute; un esfuerzo
                      extraordinario al otorgar un descuento discrecional del 35%
                      (bajo una modalidad de cr&eacute;dito similar a &ldquo;Cashea&rdquo;) para
                      apoyar a las familias del sector industria y otros convenios.
                      Sin embargo, la realidad socioecon&oacute;mica actual y el incremento
                      de los costos operativos nos obligan a tomar una decisi&oacute;n
                      dif&iacute;cil pero necesaria para la continuidad del plantel.
                      <br/><br/>
                      <strong>Informamos que, a partir del 1&deg; de septiembre de 2026,
                      la instituci&oacute;n no estar&aacute; en capacidad de mantener la
                      modalidad de aporte del 35% para factura a cr&eacute;dito.</strong>
                      Esta medida responde estrictamente a la necesidad de honrar nuestras
                      obligaciones contractuales con nuestros trabajadores (docentes y
                      administrativos) y proveedores.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Section 2 -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin:0 0 18px;">
                <tr>
                  <td style="border-left:3px solid #2471a3;padding:12px 16px;
                              background:#f8faff;border-radius:0 6px 6px 0;">
                    <p style="margin:0 0 8px;font-size:14px;color:#1a2c5b;font-weight:bold;">
                      2. Resoluci&oacute;n y Casos Especiales
                    </p>
                    <p style="margin:0;font-size:13px;color:#444;line-height:1.7;">
                      Entendemos que este cambio puede generar inquietudes. Reiteramos
                      que este beneficio fue siempre una concesi&oacute;n voluntaria y no
                      un derecho adquirido; no obstante, estamos abiertos al di&aacute;logo.
                      Aquellos representantes que deseen canalizar planteamientos o dudas
                      pueden escribir a
                      <a href="mailto:pagos@ueipab.edu.ve"
                         style="color:#2471a3;">pagos@ueipab.edu.ve</a>.
                      <br/><br/>
                      La instituci&oacute;n evaluar&aacute; <strong>Casos Especiales</strong>
                      de familias con alumnas/os que posean m&eacute;ritos excepcionales
                      (excelente rendimiento acad&eacute;mico, atletas con medallas nacionales,
                      m&uacute;sicos activos del Sistema de Orquestas Juveniles y/o habilidades
                      destacadas reconocidas). Estos casos podr&aacute;n solicitar una revisi&oacute;n
                      individual v&iacute;a correo electr&oacute;nico.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Section 3 -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin:0 0 18px;">
                <tr>
                  <td style="border-left:3px solid #2471a3;padding:12px 16px;
                              background:#f8faff;border-radius:0 6px 6px 0;">
                    <p style="margin:0 0 8px;font-size:14px;color:#1a2c5b;font-weight:bold;">
                      3. Fecha L&iacute;mite de Confirmaci&oacute;n
                    </p>
                    <p style="margin:0;font-size:13px;color:#444;line-height:1.7;">
                      Deseamos que cada familia tome esta decisi&oacute;n con la previsi&oacute;n
                      necesaria. Por ello, establecemos como plazo m&aacute;ximo el
                      <strong>lunes 08 de junio de 2026 a las 12:30 p.m.</strong>
                      para informar si desea continuar en la instituci&oacute;n.
                      <br/><br/>
                      De no recibir comunicaci&oacute;n, el sistema asumir&aacute;
                      autom&aacute;ticamente que usted acepta las nuevas condiciones
                      para el per&iacute;odo 2026-2027.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Section 4 -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin:0 0 18px;">
                <tr>
                  <td style="border-left:3px solid #2471a3;padding:12px 16px;
                              background:#f8faff;border-radius:0 6px 6px 0;">
                    <p style="margin:0 0 8px;font-size:14px;color:#1a2c5b;font-weight:bold;">
                      4. Proyecciones para el Per&iacute;odo 2026-2027
                    </p>
                    <p style="margin:0;font-size:13px;color:#444;line-height:1.7;">
                      Para su planificaci&oacute;n familiar, informamos que se estima presentar
                      ante el Comit&eacute; de Contralor&iacute;a un ajuste de la matr&iacute;cula base
                      de entre un <strong>20% a 34%</strong>, calculado sobre indicadores
                      de inflaci&oacute;n, salarios del sector privado y riesgo pa&iacute;s.
                      <br/><br/>
                      Recordamos que conceptos como seguro escolar, olimpiadas acad&eacute;micas,
                      gu&iacute;as de texto/ingl&eacute;s, concursos nacionales (rob&oacute;tica,
                      qu&iacute;mica, etc.) y eventos externos, <strong>no est&aacute;n incluidos
                      en la matr&iacute;cula</strong> y deben ser cubiertos seg&uacute;n el
                      desempe&ntilde;o y participaci&oacute;n del alumno.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Section 5 -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin:0 0 24px;">
                <tr>
                  <td style="border-left:3px solid #2471a3;padding:12px 16px;
                              background:#f8faff;border-radius:0 6px 6px 0;">
                    <p style="margin:0 0 8px;font-size:14px;color:#1a2c5b;font-weight:bold;">
                      5. Alianzas y Beneficios Locales
                    </p>
                    <p style="margin:0;font-size:13px;color:#444;line-height:1.7;">
                      Conscientes de la situaci&oacute;n econ&oacute;mica en El Tigre,
                      hemos consolidado alianzas comerciales con <strong>Almac&eacute;n
                      Par&iacute;s</strong>, <strong>Comercial Caracas</strong> y
                      <strong>Ferretera Veramar</strong>. Nuestros representantes
                      disfrutar&aacute;n de descuentos especiales en uniformes y &uacute;tiles
                      escolares en estos establecimientos. Pronto informaremos sobre el
                      aliado autorizado para la adquisici&oacute;n o bordado del
                      distintivo escolar oficial.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Signature -->
              <p style="margin:0 0 4px;font-size:14px;color:#555;">Atentamente,</p>
              <p style="margin:0;font-size:14px;color:#1a2c5b;font-weight:bold;">
                La Administraci&oacute;n
              </p>
              <p style="margin:2px 0 0;font-size:12px;color:#888;">
                Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo; C.A.
              </p>

            </td>
          </tr>

          <!-- DECISION SECTION -->
          <tr>
            <td style="background-color:#f0f4fa;padding:28px 36px;
                       border-top:3px solid #1a2c5b;">
              <h3 style="margin:0 0 8px;font-size:16px;color:#1a2c5b;text-align:center;">
                &iquest;Desea continuar en nuestra instituci&oacute;n<br/>
                para el per&iacute;odo 2026-2027?
              </h3>
              <p style="margin:0 0 20px;font-size:13px;color:#555;text-align:center;">
                Por favor confirme antes del <strong>08 de junio de 2026</strong>
                a las 12:30 p.m.
              </p>

              <!-- Buttons -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center">
                    <table cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="padding:0 8px;">
                          <a href="{si_url}"
                             style="display:inline-block;background-color:#1a2c5b;
                                    color:#ffffff;padding:14px 28px;border-radius:8px;
                                    font-size:15px;font-weight:bold;text-decoration:none;
                                    letter-spacing:0.3px;">
                            &#10003;&nbsp; S&iacute;, continuar&eacute; en 2026-2027
                          </a>
                        </td>
                        <td style="padding:0 8px;">
                          <a href="{no_url}"
                             style="display:inline-block;background-color:#5d6d7e;
                                    color:#ffffff;padding:14px 28px;border-radius:8px;
                                    font-size:15px;font-weight:bold;text-decoration:none;
                                    letter-spacing:0.3px;">
                            No continuar&eacute;
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <p style="margin:20px 0 0;font-size:11px;color:#999;text-align:center;">
                Si no responde antes del plazo, el sistema asumir&aacute; autom&aacute;ticamente
                que acepta las nuevas condiciones para el per&iacute;odo 2026-2027.<br/>
                Este enlace es personal e intransferible.
              </p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#1a2c5b;padding:20px 36px;
                       border-radius:0 0 8px 8px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#a8bfda;">
                Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo; &bull;
                El Tigre, Edo. Anzo&aacute;tegui &bull;
                <a href="mailto:pagos@ueipab.edu.ve"
                   style="color:#a8bfda;">pagos@ueipab.edu.ve</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

# Find PDVSA tag
Tag = env['res.partner.category']
pdvsa_tag = Tag.search([('name', '=', TAG_NAME)], limit=1)
if not pdvsa_tag:
    # Try case-insensitive search
    all_tags = Tag.search([])
    for t in all_tags:
        if t.name and t.name.lower() == TAG_NAME.lower():
            pdvsa_tag = t
            break
    if not pdvsa_tag:
        print(f"ERROR: Tag '{TAG_NAME}' not found. Available tags:")
        for t in all_tags:
            print(f"  id={t.id}: {t.name!r}")
        sys.exit(1)

print(f"Tag: id={pdvsa_tag.id} '{pdvsa_tag.name}'")

# Find partners
if PARTNER_ID:
    partners = env['res.partner'].browse(PARTNER_ID)
    if not partners.exists():
        print(f"ERROR: Partner id={PARTNER_ID} not found")
        sys.exit(1)
    print(f"Testing with partner id={PARTNER_ID}: {partners.name}")
else:
    partners = env['res.partner'].search([
        ('category_id', 'in', [pdvsa_tag.id]),
        ('active', '=', True),
        ('email', '!=', False),
        ('email', '!=', ''),
    ], order='name')
    print(f"Found {len(partners)} partners with tag '{TAG_NAME}' and email")

# Get base URL for links
base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
print(f"Base URL: {base_url}")
print()

Ack = env['partner.communication.ack']
Mail = env['mail.mail']

sent = 0
skipped = 0
errors = 0

for partner in partners:
    emails = [e.strip() for e in (partner.email or '').split(';') if e.strip()]
    if not emails:
        print(f"  SKIP (no email): {partner.name}")
        skipped += 1
        continue

    # Idempotency: skip if already sent for this campaign
    existing = Ack.search([
        ('partner_id', '=', partner.id),
        ('notice_key', '=', NOTICE_KEY),
    ], limit=1)
    if existing:
        print(f"  SKIP (already sent, state={existing.state}): {partner.name}")
        skipped += 1
        continue

    print(f"  {'[DRY]' if DRY_RUN else '[SEND]'} {partner.name} → {partner.email}")

    if DRY_RUN:
        sent += 1
        continue

    try:
        # Create ACK record
        ack = Ack.create({
            'notice_key':   NOTICE_KEY,
            'notice_label': NOTICE_LABEL,
            'partner_id':   partner.id,
        })
        env.cr.commit()

        si_url = ack._get_si_url()
        no_url = ack._get_no_url()
        html   = _build_email_html(partner.name, si_url, no_url)

        # Send to all semicolon-separated emails
        to_addrs = ', '.join(
            f'{partner.name} <{e}>' if i == 0 else f'<{e}>'
            for i, e in enumerate(emails)
        )

        mail = Mail.create({
            'subject':    f'Comunicado Importante — Período 2026-2027 | {partner.name}',
            'email_from': 'Administración UEIPAB <pagos@ueipab.edu.ve>',
            'email_to':   to_addrs,
            'body_html':  html,
            'state':      'outgoing',
        })
        env.cr.commit()

        print(f"         ack_id={ack.id}  mail_id={mail.id}")
        sent += 1

        if SEND_DELAY > 0:
            time.sleep(SEND_DELAY)

    except Exception as exc:
        print(f"  ERROR: {partner.name}: {exc}")
        env.cr.rollback()
        errors += 1

print()
print("=" * 70)
print(f"RESUMEN:")
print(f"  Enviados  : {sent}")
print(f"  Omitidos  : {skipped}")
print(f"  Errores   : {errors}")
if DRY_RUN:
    print()
    print("*** DRY RUN — no se crearon registros ni se enviaron correos ***")
    print("Usa: LIVE=true para envío real")
print("=" * 70)
