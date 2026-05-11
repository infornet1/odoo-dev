#!/usr/bin/env python3
"""
Send Representante Communication — Período 2026-2027
=====================================================
Survey email to all partners tagged "Representante" (non-PDVSA) asking
whether they intend to continue in the institution for 2026-2027.

Infrastructure is identical to the PDVSA campaign (partner.communication.ack
model, /partner-ack/<token>/si|no routes). Only the letter content differs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BEFORE SENDING: fill in the four TODO blocks below.
  The script will REFUSE to run until all four are set.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Uso (Odoo shell):
    # Dry run — lists recipients, nothing created
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \\
      < /opt/odoo-dev/scripts/send_representante_communication.py

    # Live — all Representante partners with email
    { echo "import os; os.environ['LIVE']='true'"; \\
      cat /opt/odoo-dev/scripts/send_representante_communication.py; } \\
      | docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http

    # Live — single partner (for test, replace N with partner id)
    { echo "import os; os.environ['LIVE']='true'; os.environ['PARTNER_ID']='N'"; \\
      cat /opt/odoo-dev/scripts/send_representante_communication.py; } \\
      | docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http
"""

import os
import sys
import time

# ══════════════════════════════════════════════════════════════════════════════
# ✏️  FILL THESE IN WHEN THE LETTER IS READY — script blocks until all are set
# ══════════════════════════════════════════════════════════════════════════════

# URL to the full letter document (Google Doc or similar public link)
LETTER_URL = ''  # TODO: e.g. 'https://docs.google.com/document/d/...'

# Three bullet points summarising the key facts from the letter.
# Keep each under ~180 chars. HTML allowed (bold with <strong>, links with <a>).
BULLET_1 = ''  # TODO: e.g. 'El <strong>descuento X</strong> finaliza el...'
BULLET_2 = ''  # TODO: e.g. 'La matrícula 2026-2027 tendrá un ajuste de...'
BULLET_3 = ''  # TODO: e.g. 'Casos especiales con méritos serán evaluados...'

# One-line headline shown at the top of the email (below the logo).
# Keep under ~60 chars. No HTML.
EMAIL_HEADLINE = ''  # TODO: e.g. '¿Continuará en el Colegio para 2026-2027?'

# ══════════════════════════════════════════════════════════════════════════════

# ── Runtime guard ─────────────────────────────────────────────────────────────
_MISSING = [name for name, val in [
    ('LETTER_URL',    LETTER_URL),
    ('BULLET_1',      BULLET_1),
    ('BULLET_2',      BULLET_2),
    ('BULLET_3',      BULLET_3),
    ('EMAIL_HEADLINE', EMAIL_HEADLINE),
] if not val.strip()]

if _MISSING:
    print("=" * 70)
    print("⛔  SCRIPT BLOQUEADO — contenido de la carta pendiente")
    print()
    print("   Edita send_representante_communication.py y rellena:")
    for name in _MISSING:
        print(f"   • {name}")
    print()
    print("   Una vez completados, vuelve a ejecutar el script.")
    print("=" * 70)
    sys.exit(0)

# ── Fixed campaign config ──────────────────────────────────────────────────────

DRY_RUN    = os.environ.get('LIVE', '').lower() not in ('true', '1', 'yes')
PARTNER_ID = int(os.environ.get('PARTNER_ID', '0'))
SEND_DELAY = float(os.environ.get('SEND_DELAY', '0.3'))

NOTICE_KEY   = 'representante_continuacion_2026_2027'
NOTICE_LABEL = 'Comunicado Representantes — Continuidad Período 2026-2027'
TAG_NAME     = 'Representante'

# Deadline shown in email — update if different from PDVSA campaign
DEADLINE_DISPLAY = 'lunes 08 de junio de 2026 a las 12:30 p.m.'
DEADLINE_SHORT   = '08 de junio de 2026'

print("=" * 70)
print(f"COMUNICADO REPRESENTANTES 2026-2027 — {'*** DRY RUN ***' if DRY_RUN else '*** ENVÍO REAL ***'}")
print("=" * 70)

# ── Email builder ──────────────────────────────────────────────────────────────

def _build_email_html(partner_name, si_url, no_url):
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

        <!-- ── HERO ── -->
        <tr>
          <td style="padding:28px 36px 0;text-align:center;">
            <h1 style="margin:0 0 10px;font-size:21px;color:#1a2c5b;line-height:1.3;">
              {EMAIL_HEADLINE}
            </h1>
            <p style="margin:0 0 6px;font-size:14px;color:#555;line-height:1.5;">
              Estimado(a) representante <strong>{partner_name}</strong>,
              le comunicamos un cambio importante.<br/>
              Por favor ind&iacute;quenos su intenci&oacute;n con un clic:
            </p>
          </td>
        </tr>

        <!-- ── ACTION BLOCK ── -->
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
                    <strong>Fecha l&iacute;mite: {DEADLINE_DISPLAY}</strong>
                    <br/>
                    <span style="font-size:12px;">
                      Si no responde antes de esta fecha, el sistema asumir&aacute;
                      que acepta las nuevas condiciones.
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
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td width="28" valign="top"
                    style="font-size:18px;color:#2471a3;padding-top:1px;">&#8226;</td>
                <td style="font-size:13px;color:#333;line-height:1.6;">{BULLET_1}</td>
              </tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td width="28" valign="top"
                    style="font-size:18px;color:#2471a3;padding-top:1px;">&#8226;</td>
                <td style="font-size:13px;color:#333;line-height:1.6;">{BULLET_2}</td>
              </tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="margin:0 0 10px;">
              <tr>
                <td width="28" valign="top"
                    style="font-size:18px;color:#2471a3;padding-top:1px;">&#8226;</td>
                <td style="font-size:13px;color:#333;line-height:1.6;">{BULLET_3}</td>
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

# Find Representante tag
Tag = env['res.partner.category']
rep_tag = Tag.search([('name', '=', TAG_NAME)], limit=1)
if not rep_tag:
    all_tags = Tag.search([])
    for t in all_tags:
        if t.name and t.name.lower() == TAG_NAME.lower():
            rep_tag = t
            break
    if not rep_tag:
        print(f"ERROR: Tag '{TAG_NAME}' not found.")
        sys.exit(1)

print(f"Tag: id={rep_tag.id} '{rep_tag.name}'")

# Find partners
if PARTNER_ID:
    partners = env['res.partner'].browse(PARTNER_ID)
    if not partners.exists():
        print(f"ERROR: Partner id={PARTNER_ID} not found")
        sys.exit(1)
    print(f"Testing with partner id={PARTNER_ID}: {partners.name}")
else:
    partners = env['res.partner'].search([
        ('category_id', 'in', [rep_tag.id]),
        ('active', '=', True),
        ('email', '!=', False),
        ('email', '!=', ''),
    ], order='name')
    print(f"Found {len(partners)} partners with tag '{TAG_NAME}' and email")

base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
print(f"Base URL: {base_url}")
print()

Ack  = env['partner.communication.ack']
Mail = env['mail.mail']

sent = skipped = errors = 0

for partner in partners:
    emails = [e.strip() for e in (partner.email or '').split(';') if e.strip()]
    if not emails:
        print(f"  SKIP (no email): {partner.name}")
        skipped += 1
        continue

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
        ack = Ack.create({
            'notice_key':   NOTICE_KEY,
            'notice_label': NOTICE_LABEL,
            'partner_id':   partner.id,
        })
        env.cr.commit()

        si_url = ack._get_si_url()
        no_url = ack._get_no_url()
        html   = _build_email_html(partner.name, si_url, no_url)

        to_addrs = ', '.join(
            f'{partner.name} <{e}>' if i == 0 else f'<{e}>'
            for i, e in enumerate(emails)
        )

        mail = Mail.create({
            'subject':    f'Responder encuesta continuidad — Período 2026-2027 | {partner.name}',
            'email_from': 'Colegio Andrés Bello <soporte@ueipab.edu.ve>',
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
