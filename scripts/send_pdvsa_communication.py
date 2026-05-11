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

LETTER_URL = 'https://docs.google.com/document/d/1z9_Dr3qvWdytEcrDUCp7NcVoJQHq4MKiveNoV_kC2jE/edit?tab=t.0'


def _build_email_html(partner_name, si_url, no_url):
    """Return the HTML email body — decision-first layout, 3-bullet summary."""
    first_name = partner_name.split()[0].capitalize() if partner_name else 'Representante'
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
    <td align="center" style="padding:24px 10px 32px;">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;background:#ffffff;border-radius:10px;
                    box-shadow:0 2px 16px rgba(0,0,0,0.11);">

        <!-- ── HEADER ── -->
        <tr>
          <td style="background-color:#1a2c5b;padding:24px 32px 20px;
                     border-radius:10px 10px 0 0;text-align:center;">
            <img src="https://dev.ueipab.edu.ve/flyers/ueipab_logo.png"
                 alt="Colegio Andr&eacute;s Bello"
                 width="190" height="79"
                 style="display:block;margin:0 auto;border:0;outline:none;"/>
          </td>
        </tr>

        <!-- ── HERO: question + greeting ── -->
        <tr>
          <td style="padding:28px 36px 0;text-align:center;">
            <h1 style="margin:0 0 10px;font-size:21px;color:#1a2c5b;line-height:1.3;">
              &iquest;Continuar&aacute; en el Colegio<br/>para el per&iacute;odo
              <span style="white-space:nowrap;">2026&ndash;2027?</span>
            </h1>
            <p style="margin:0 0 6px;font-size:14px;color:#555;line-height:1.5;">
              Estimado(a) <strong>{partner_name}</strong>, le comunicamos un cambio
              importante en nuestra pol&iacute;tica de pagos.<br/>
              Por favor ind&iacute;quenos su intenci&oacute;n con un clic:
            </p>
          </td>
        </tr>

        <!-- ── ACTION BLOCK (above fold) ── -->
        <tr>
          <td style="padding:20px 36px 8px;">

            <!-- 1. Ghost: Ver comunicado (read before deciding) -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td>
                  <a href="{LETTER_URL}"
                     style="display:block;background-color:#ffffff;
                            color:#1a2c5b;padding:14px 20px;border-radius:8px;
                            font-size:14px;font-weight:bold;text-decoration:none;
                            border:2px solid #1a2c5b;text-align:center;">
                    &#128196;&nbsp; Ver comunicado completo
                  </a>
                </td>
              </tr>
            </table>

            <!-- 2. YES -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td>
                  <a href="{si_url}"
                     style="display:block;background-color:#1a2c5b;
                            color:#ffffff;padding:15px 20px;border-radius:8px;
                            font-size:15px;font-weight:bold;text-decoration:none;
                            text-align:center;">
                    &#10003;&nbsp; S&iacute;, continuar&eacute; en 2026-2027
                  </a>
                </td>
              </tr>
            </table>

            <!-- 3. NO -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td>
                  <a href="{no_url}"
                     style="display:block;background-color:#5d6d7e;
                            color:#ffffff;padding:15px 20px;border-radius:8px;
                            font-size:15px;font-weight:bold;text-decoration:none;
                            text-align:center;">
                    No continuar&eacute;
                  </a>
                </td>
              </tr>
            </table>

          </td>
        </tr>

        <!-- ── DEADLINE CALLOUT ── -->
        <tr>
          <td style="padding:16px 36px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background-color:#fff8e1;border:1px solid #ffe082;
                           border-radius:8px;padding:13px 18px;text-align:center;">
                  <p style="margin:0;font-size:13px;color:#5d4037;line-height:1.5;">
                    &#128197;&nbsp;
                    <strong>Fecha l&iacute;mite: lunes 08 de junio de 2026 &mdash; 12:30 p.m.</strong>
                    <br/>
                    <span style="font-size:12px;">
                      Si no responde antes de esta fecha, el sistema asumir&aacute; que
                      acepta las nuevas condiciones.
                    </span>
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── DIVIDER ── -->
        <tr>
          <td style="padding:24px 36px 0;">
            <hr style="border:none;border-top:1px solid #e0e7ef;margin:0;"/>
          </td>
        </tr>

        <!-- ── 3-BULLET SUMMARY ── -->
        <tr>
          <td style="padding:20px 36px 0;">
            <p style="margin:0 0 14px;font-size:13px;color:#888;
                      text-transform:uppercase;letter-spacing:0.8px;font-weight:bold;">
              Resumen del comunicado
            </p>
            <!-- Bullet 1 -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td width="28" valign="top"
                    style="font-size:18px;color:#2471a3;padding-top:1px;">&#8226;</td>
                <td style="font-size:13px;color:#333;line-height:1.6;">
                  El descuento discrecional del <strong>35%</strong> (tipo cr&eacute;dito)
                  finaliza el <strong>1&deg; de septiembre de 2026</strong>. Esta medida
                  es necesaria para sostener los compromisos salariales del plantel.
                </td>
              </tr>
            </table>
            <!-- Bullet 2 -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td width="28" valign="top"
                    style="font-size:18px;color:#2471a3;padding-top:1px;">&#8226;</td>
                <td style="font-size:13px;color:#333;line-height:1.6;">
                  Para 2026&ndash;2027 se proyecta un ajuste de matr&iacute;cula de
                  <strong>20% a 34%</strong>. Los conceptos de seguro escolar,
                  olimpiadas e ingl&eacute;s no est&aacute;n incluidos en la cuota mensual.
                </td>
              </tr>
            </table>
            <!-- Bullet 3 -->
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td width="28" valign="top"
                    style="font-size:18px;color:#2471a3;padding-top:1px;">&#8226;</td>
                <td style="font-size:13px;color:#333;line-height:1.6;">
                  Se evaluar&aacute;n <strong>Casos Especiales</strong> para familias con
                  alumnos de m&eacute;ritos excepcionales (acad&eacute;micos, deportivos,
                  art&iacute;sticos). Escr&iacute;banos a
                  <a href="mailto:votacion@ueipab.edu.ve"
                     style="color:#2471a3;">votacion@ueipab.edu.ve</a>.
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── SIGNATURE ── -->
        <tr>
          <td style="padding:20px 36px 24px;">
            <hr style="border:none;border-top:1px solid #e0e7ef;margin:0 0 16px;"/>
            <p style="margin:0 0 2px;font-size:13px;color:#555;">Atentamente,</p>
            <p style="margin:0;font-size:13px;color:#1a2c5b;font-weight:bold;">
              La Administraci&oacute;n &mdash; Colegio &ldquo;Andr&eacute;s Bello&rdquo;
            </p>
            <p style="margin:2px 0 0;font-size:12px;color:#888;">
              El Tigre, 08 de mayo de 2026
            </p>
          </td>
        </tr>

        <!-- ── FOOTER ── -->
        <tr>
          <td style="background-color:#1a2c5b;padding:16px 32px;
                     border-radius:0 0 10px 10px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#a8bfda;line-height:1.6;">
              Este enlace es personal e intransferible &mdash;
              <a href="mailto:votacion@ueipab.edu.ve"
                 style="color:#a8bfda;">votacion@ueipab.edu.ve</a>
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
            'subject':    f'Responder encuesta continuidad — Período 2026-2027 | {partner.name}',
            'email_from': 'Colegio Andrés Bello <votacion@ueipab.edu.ve>',
            'reply_to':   'votacion@ueipab.edu.ve',
            'email_to':   to_addrs,
            'email_cc':   'votacion@ueipab.edu.ve',
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
