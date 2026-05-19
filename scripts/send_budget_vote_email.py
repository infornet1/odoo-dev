#!/usr/bin/env python3
"""
Consulta Presupuestaria 2026-2027 — Vote Email Sender
======================================================
Envía el correo de votación para la propuesta presupuestaria 2026-2027
con las opciones A ($218,88) y B ($236,58).

Uso (Odoo shell):

  # Dry run — ver destinatarios sin crear registros
  docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
    < /opt/odoo-dev/scripts/send_budget_vote_email.py

  # Prueba — solo al CEO (gustavo.perdomo@gmail.com)
  TEST=true LIVE=true docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
    < /opt/odoo-dev/scripts/send_budget_vote_email.py

  # Envío real a todos los representantes
  LIVE=true docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
    < /opt/odoo-dev/scripts/send_budget_vote_email.py
"""

import os
import time

# ── Configuración ─────────────────────────────────────────────────────────────

DRY_RUN    = os.environ.get('LIVE', '').lower() not in ('true', '1', 'yes')
TEST_MODE  = os.environ.get('TEST', '').lower() in ('true', '1', 'yes')
SEND_DELAY = float(os.environ.get('SEND_DELAY', '0.2'))

NOTICE_KEY   = 'budget_consulta_2026_2027'
NOTICE_LABEL = 'Consulta Presupuestaria 2026-2027'
BASE_URL     = env['ir.config_parameter'].sudo().get_param('web.base.url', 'https://odoo.ueipab.edu.ve')
LOGO_URL     = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'

# CEO test recipient
CEO_PARTNER_ID = 7
CEO_TEST_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'

print("=" * 70)
mode = "*** TEST — solo CEO ***" if TEST_MODE else ("*** ENVÍO REAL ***" if not DRY_RUN else "*** DRY RUN ***")
print(f"CONSULTA PRESUPUESTARIA 2026-2027 — {mode}")
print("=" * 70)


# ── Partner query ──────────────────────────────────────────────────────────────

def _get_recipients():
    """Return list of res.partner to send the vote email to."""
    if TEST_MODE:
        partner = env['res.partner'].browse(CEO_PARTNER_ID)
        return partner if partner.exists() else env['res.partner']

    # All Representantes (tag 25), not Inactivo (tag 29), with email
    return env['res.partner'].sudo().search([
        ('active', '=', True),
        ('email', '!=', False),
        ('email', '!=', ''),
        ('category_id', 'in', [25]),       # Representante
        ('category_id', 'not in', [29]),   # exclude Inactivo
    ])


# ── Email HTML builder ────────────────────────────────────────────────────────

def _build_html(partner_name, si_url, no_url, is_test=False):
    test_banner = (
        '<div style="background:#c0392b;color:#fff;text-align:center;padding:10px;'
        'font-size:13px;font-weight:bold;">'
        '⚠️ PRUEBA DE REVISIÓN — Los botones funcionan, pero este voto no cuenta para '
        'el resultado final.</div>'
    ) if is_test else ''

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Consulta Presupuestaria 2026-2027</title>
</head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
{test_banner}
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;">
<tr><td align="center" style="padding:28px 12px;">
<table cellpadding="0" cellspacing="0" width="600"
       style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden;
              box-shadow:0 4px 28px rgba(0,0,0,0.11);">

  <!-- ══ HEADER ══ -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
               padding:36px 32px 30px;text-align:center;">
      <img src="{LOGO_URL}" alt="Colegio Andrés Bello" width="80" height="80"
           style="border-radius:50%;border:3px solid rgba(255,255,255,0.3);
                  display:block;margin:0 auto 14px;"/>
      <h1 style="margin:0;color:#fff;font-size:21px;font-weight:bold;line-height:1.3;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </h1>
      <p style="margin:5px 0 16px;color:rgba(255,255,255,0.8);font-size:13px;">
        El Tigre, Estado Anzo&aacute;tegui
      </p>
      <div style="display:inline-block;background:rgba(255,255,255,0.18);
                  border:1px solid rgba(255,255,255,0.4);border-radius:20px;
                  padding:7px 22px;">
        <span style="color:#fff;font-size:14px;font-weight:bold;">
          🗳️ CONSULTA PRESUPUESTARIA 2026-2027
        </span>
      </div>
    </td>
  </tr>

  <!-- ══ GREETING ══ -->
  <tr>
    <td style="padding:28px 32px 6px;">
      <p style="margin:0 0 12px;color:#1a2c5b;font-size:15px;line-height:1.6;">
        Estimado(a) <strong>{partner_name}</strong>,
      </p>
      <p style="margin:0;color:#444;font-size:14px;line-height:1.75;">
        Conforme a lo establecido en las Resoluciones 0009 y 024-2020 del MPPE,
        el <strong>Comit&eacute; de Contralor&iacute;a</strong> analiz&oacute; la propuesta
        econ&oacute;mica 2026-2027 y emiti&oacute; su informe <strong>sin objeciones</strong>.
        A continuaci&oacute;n le presentamos las dos opciones para que ejerza su voto.
      </p>
    </td>
  </tr>

  <!-- ══ CONTEXT BOX ══ -->
  <tr>
    <td style="padding:12px 32px 6px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fff8e7;border-left:4px solid #f0a500;
                    border-radius:0 8px 8px 0;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 10px;font-size:11px;color:#b37a00;font-weight:bold;
                      text-transform:uppercase;letter-spacing:0.5px;">
              Contexto Econ&oacute;mico — Justificaci&oacute;n del Ajuste
            </p>
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td width="33%" style="text-align:center;padding:6px 4px;">
                  <div style="font-size:22px;font-weight:bold;color:#1a2c5b;">611,86%</div>
                  <div style="font-size:11px;color:#666;margin-top:2px;">Inflaci&oacute;n 2025</div>
                </td>
                <td width="33%" style="text-align:center;padding:6px 4px;
                    border-left:1px solid #f0d080;border-right:1px solid #f0d080;">
                  <div style="font-size:22px;font-weight:bold;color:#1a2c5b;">Bs. 487,12</div>
                  <div style="font-size:11px;color:#666;margin-top:2px;">Tipo de cambio</div>
                </td>
                <td width="33%" style="text-align:center;padding:6px 4px;">
                  <div style="font-size:22px;font-weight:bold;color:#1a2c5b;">8,5%</div>
                  <div style="font-size:11px;color:#666;margin-top:2px;">Crecimiento econ.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ SECTION TITLE ══ -->
  <tr>
    <td style="padding:22px 32px 10px;text-align:center;">
      <h2 style="margin:0;color:#1a2c5b;font-size:17px;">
        Seleccione su opci&oacute;n de mensualidad para 2026-2027
      </h2>
      <p style="margin:6px 0 0;color:#777;font-size:13px;">
        Ambas opciones incluyen los mismos servicios educativos STEAM+G
      </p>
    </td>
  </tr>

  <!-- ══ OPTION CARDS ══ -->
  <tr>
    <td style="padding:4px 32px 16px;">
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <!-- OPCIÓN A -->
          <td width="48%" valign="top"
              style="background:#f0f7ff;border:2px solid #1a2c5b;
                     border-radius:12px;overflow:hidden;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td style="background:#1a2c5b;padding:11px 14px;text-align:center;">
                  <span style="color:#fff;font-size:13px;font-weight:bold;
                               text-transform:uppercase;letter-spacing:1px;">OPCIÓN A</span>
                </td>
              </tr>
              <tr>
                <td style="padding:18px 14px 6px;text-align:center;">
                  <div style="font-size:12px;color:#666;margin-bottom:3px;">Mensualidad</div>
                  <div style="font-size:36px;font-weight:bold;color:#1a2c5b;line-height:1.1;">
                    $218,88
                  </div>
                  <div style="display:inline-block;background:#e8f5e9;border-radius:12px;
                               padding:3px 10px;margin-top:6px;">
                    <span style="font-size:11px;color:#2e7d32;">+10,89% vs año anterior</span>
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 14px;">
                  <table cellpadding="5" cellspacing="0" width="100%"
                         style="background:#dceefb;border-radius:7px;font-size:12px;">
                    <tr>
                      <td style="color:#555;padding-bottom:0;">💰 Pronto pago (1–10 c/mes)</td>
                    </tr>
                    <tr>
                      <td style="text-align:center;padding-top:2px;">
                        <span style="font-size:20px;font-weight:bold;color:#1a2c5b;">$207,93</span>
                        <span style="font-size:11px;color:#2e7d32;"> — ahorras $10,95</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:4px 14px 6px;font-size:12px;color:#555;text-align:center;">
                  📅 Costo anual est.: <strong style="color:#1a2c5b;">$2.845,45</strong>
                </td>
              </tr>
              <tr>
                <td style="padding:10px 14px 16px;text-align:center;">
                  <a href="{si_url}"
                     style="display:block;background:#1a2c5b;color:#fff;font-size:14px;
                            font-weight:bold;text-decoration:none;padding:13px 8px;
                            border-radius:8px;">
                    ✅ Votar Opci&oacute;n A
                  </a>
                </td>
              </tr>
            </table>
          </td>

          <td width="4%"></td>

          <!-- OPCIÓN B -->
          <td width="48%" valign="top"
              style="background:#f5f0ff;border:2px solid #6c3483;
                     border-radius:12px;overflow:hidden;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td style="background:#6c3483;padding:11px 14px;text-align:center;">
                  <span style="color:#fff;font-size:13px;font-weight:bold;
                               text-transform:uppercase;letter-spacing:1px;">OPCIÓN B</span>
                </td>
              </tr>
              <tr>
                <td style="padding:18px 14px 6px;text-align:center;">
                  <div style="font-size:12px;color:#666;margin-bottom:3px;">Mensualidad</div>
                  <div style="font-size:36px;font-weight:bold;color:#6c3483;line-height:1.1;">
                    $236,58
                  </div>
                  <div style="display:inline-block;background:#f3e5f5;border-radius:12px;
                               padding:3px 10px;margin-top:6px;">
                    <span style="font-size:11px;color:#6c3483;">+19,86% vs año anterior</span>
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 14px;">
                  <table cellpadding="5" cellspacing="0" width="100%"
                         style="background:#ede7f6;border-radius:7px;font-size:12px;">
                    <tr>
                      <td style="color:#555;padding-bottom:0;">💰 Pronto pago (1–10 c/mes)</td>
                    </tr>
                    <tr>
                      <td style="text-align:center;padding-top:2px;">
                        <span style="font-size:20px;font-weight:bold;color:#6c3483;">$224,75</span>
                        <span style="font-size:11px;color:#2e7d32;"> — ahorras $11,82</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:4px 14px 6px;font-size:12px;color:#555;text-align:center;">
                  📅 Costo anual est.: <strong style="color:#6c3483;">$3.075,55</strong>
                </td>
              </tr>
              <tr>
                <td style="padding:10px 14px 16px;text-align:center;">
                  <a href="{no_url}"
                     style="display:block;background:#6c3483;color:#fff;font-size:14px;
                            font-weight:bold;text-decoration:none;padding:13px 8px;
                            border-radius:8px;">
                    ✅ Votar Opci&oacute;n B
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ DESCUENTOS HERMANOS ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;">
        <tr>
          <td style="padding:12px 18px;">
            <p style="margin:0 0 8px;font-size:12px;font-weight:bold;color:#1a2c5b;
                      text-transform:uppercase;">
              🏫 Descuentos por familia numerosa (ambas opciones)
            </p>
            <table cellpadding="3" cellspacing="0" width="100%"
                   style="font-size:13px;color:#444;">
              <tr>
                <td>1er hijo/representado</td>
                <td style="text-align:right;">5% descuento</td>
              </tr>
              <tr style="background:#f0f0f0;">
                <td>2do hijo/representado</td>
                <td style="text-align:right;">8% descuento</td>
              </tr>
              <tr>
                <td>3ro y sucesivos</td>
                <td style="text-align:right;">11% descuento</td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ COSTOS ANUALES ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fff8e7;border:1px solid #ffc107;border-radius:8px;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 8px;font-size:12px;font-weight:bold;color:#1a2c5b;
                      text-transform:uppercase;">
              📋 Costos &Uacute;nicos Anuales por Alumno
              <span style="font-weight:normal;color:#777;font-size:11px;
                            text-transform:none;"> — pagaderos en inscripci&oacute;n</span>
            </p>
            <table cellpadding="4" cellspacing="0" width="100%"
                   style="font-size:13px;color:#444;">
              <tr>
                <td>Seguro escolar (Seguros Caracas)</td>
                <td style="text-align:right;">$30,58</td>
              </tr>
              <tr style="background:rgba(0,0,0,0.04);">
                <td>Gu&iacute;a de ingl&eacute;s</td>
                <td style="text-align:right;">$25,00</td>
              </tr>
              <tr>
                <td>Olimpiadas recreativas</td>
                <td style="text-align:right;">$10,00</td>
              </tr>
              <tr style="background:rgba(0,0,0,0.04);">
                <td>Enciclopedia digital (todos los niveles)</td>
                <td style="text-align:right;">$36,00</td>
              </tr>
              <tr style="border-top:2px solid #ffc107;">
                <td style="font-weight:bold;color:#1a2c5b;padding-top:7px;">
                  Total por alumno
                </td>
                <td style="text-align:right;font-weight:bold;color:#1a2c5b;padding-top:7px;">
                  $101,58
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ SEGURO ESCOLAR ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fafafa;border:1px solid #e0e0e0;border-radius:8px;">
        <tr>
          <td style="padding:14px 18px;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td valign="middle" width="36"
                    style="font-size:26px;padding-right:12px;">🛡️</td>
                <td valign="middle">
                  <p style="margin:0 0 3px;font-size:12px;font-weight:bold;color:#1a2c5b;
                            text-transform:uppercase;letter-spacing:0.4px;">
                    Seguro Escolar 2026-2027 &mdash; Seguros Caracas
                  </p>
                  <p style="margin:0;font-size:13px;color:#555;line-height:1.55;">
                    Cobertura para todos los estudiantes incluida en el costo anual
                    ($30,58/alumno). Reclamaciones:
                    <a href="https://wa.me/584149033738" style="color:#1a2c5b;">WA 0414-903.3738</a>
                    &nbsp;/&nbsp;
                    <a href="mailto:amis@grupov.com.ve" style="color:#1a2c5b;">amis@grupov.com.ve</a>.
                    Asesora: Johanna Hern&aacute;ndez.
                  </p>
                </td>
                <td valign="middle" style="padding-left:16px;white-space:nowrap;">
                  <a href="https://drive.google.com/file/d/1KLJ5i9IgE5f0BhN1sGJvmVUCZMX7-mtU/view?usp=drive_link"
                     style="display:inline-block;background:#fff;color:#1a2c5b;font-size:12px;
                            font-weight:bold;text-decoration:none;padding:8px 14px;
                            border:1.5px solid #1a2c5b;border-radius:6px;white-space:nowrap;">
                    Ver p&oacute;liza ↗
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ OFERTA INSCRIPCIÓN ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);
                    border-radius:8px;border:1px solid #a5d6a7;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 4px;font-size:12px;font-weight:bold;color:#1b5e20;
                      text-transform:uppercase;">
              🎉 Oferta de Inscripci&oacute;n Anticipada — hasta el 31 de julio
            </p>
            <p style="margin:0;font-size:14px;color:#1b5e20;">
              Inscripci&oacute;n: <strong>$187,51</strong>
              &nbsp;&middot;&nbsp;
              Mensualidad septiembre: <strong>$197,38</strong>
            </p>
            <p style="margin:4px 0 0;font-size:11px;color:#555;">
              Requisito: solvencia completa 2025-2026. Descuentos por familia numerosa aplicables.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ CRONOGRAMA ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f0f4fa;border-radius:8px;border:1px solid #c9d7eb;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 10px;font-size:12px;font-weight:bold;color:#1a2c5b;
                      text-transform:uppercase;">
              📅 Cronograma del Proceso
            </p>
            <table cellpadding="4" cellspacing="0" width="100%" style="font-size:13px;">
              <tr>
                <td width="22" style="color:#27ae60;">✅</td>
                <td><strong>18 mayo:</strong> Comit&eacute; de Contralor&iacute;a — aprobado sin objeciones</td>
              </tr>
              <tr style="background:rgba(26,44,91,0.04);">
                <td style="color:#27ae60;">✅</td>
                <td><strong>19–20 mayo:</strong> Videollamadas de consulta (3:00 pm y 2:00 pm)</td>
              </tr>
              <tr>
                <td style="color:#f0a500;font-weight:bold;">🗳️</td>
                <td>
                  <strong>21–22 mayo:</strong> Per&iacute;odo de votaci&oacute;n —
                  <strong style="color:#c0392b;">ACTIVO AHORA</strong>
                </td>
              </tr>
              <tr style="background:rgba(26,44,91,0.04);">
                <td style="color:#aaa;">📊</td>
                <td style="color:#888;"><strong>26 mayo:</strong> Publicaci&oacute;n de resultados</td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ POLÍTICA DE MORA ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fafafa;border:1px solid #e0e0e0;border-radius:8px;">
        <tr>
          <td style="padding:14px 18px;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td valign="middle" width="36"
                    style="font-size:26px;padding-right:12px;">⚖️</td>
                <td valign="middle">
                  <p style="margin:0 0 3px;font-size:12px;font-weight:bold;color:#1a2c5b;
                            text-transform:uppercase;letter-spacing:0.4px;">
                    Pol&iacute;tica de Convivencia Financiera
                  </p>
                  <p style="margin:0;font-size:13px;color:#555;line-height:1.55;">
                    El proceso es progresivo y dialogado en 4 etapas — desde un convenio de pago
                    hasta la notificaci&oacute;n a organismos competentes.
                    <strong style="color:#1a2c5b;">El estudiante contin&uacute;a asistiendo
                    regularmente en todo momento.</strong>
                  </p>
                </td>
                <td valign="middle" style="padding-left:16px;white-space:nowrap;">
                  <a href="https://odoo.ueipab.edu.ve/mora-policy/"
                     style="display:inline-block;background:#fff;color:#1a2c5b;font-size:12px;
                            font-weight:bold;text-decoration:none;padding:8px 14px;
                            border:1.5px solid #1a2c5b;border-radius:6px;white-space:nowrap;">
                    Ver pol&iacute;tica ↗
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ BOTONES FINALES ══ -->
  <tr>
    <td style="padding:16px 32px 28px;text-align:center;">
      <p style="margin:0 0 16px;font-size:13px;color:#555;">
        Vote antes del <strong>22 de mayo de 2026</strong>.
        Puede consultar a Glenda sus dudas sobre las opciones.
      </p>
      <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
        <tr>
          <td style="padding:0 6px;">
            <a href="{si_url}"
               style="display:inline-block;background:#1a2c5b;color:#fff;font-weight:bold;
                      font-size:14px;text-decoration:none;padding:13px 22px;border-radius:8px;">
              ✅ Votar Opci&oacute;n A — $218,88
            </a>
          </td>
          <td style="padding:0 6px;">
            <a href="{no_url}"
               style="display:inline-block;background:#6c3483;color:#fff;font-weight:bold;
                      font-size:14px;text-decoration:none;padding:13px 22px;border-radius:8px;">
              ✅ Votar Opci&oacute;n B — $236,58
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ FOOTER ══ -->
  <tr>
    <td style="background:#f8f9fa;border-top:1px solid #e0e0e0;
               padding:18px 32px;text-align:center;">
      <p style="margin:0 0 6px;font-size:12px;color:#888;">¿Preguntas? Estamos para ayudarle:</p>
      <p style="margin:0;font-size:13px;color:#555;">
        ✉️ <a href="mailto:votacion@ueipab.edu.ve" style="color:#1a2c5b;">votacion@ueipab.edu.ve</a>
        &nbsp;|&nbsp;
        💬 <a href="https://wa.me/584148321989" style="color:#1a2c5b;">Glenda WhatsApp</a>
        &nbsp;|&nbsp;
        📱 <a href="https://t.me/GlendaUeipabBot" style="color:#1a2c5b;">Glenda Telegram</a>
      </p>
      <p style="margin:8px 0 0;font-size:10px;color:#bbb;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo; &mdash; El Tigre, Estado Anzo&aacute;tegui
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Send logic ────────────────────────────────────────────────────────────────

recipients = _get_recipients()
print(f"\nDestinatarios encontrados: {len(recipients)}")

sent = 0
skipped = 0

for partner in recipients:
    # Determine email address
    email = partner.email or ''
    if not email:
        print(f"  SKIP {partner.name} — sin email")
        skipped += 1
        continue

    # For test mode, override email to CEO gmail
    send_to = CEO_TEST_EMAIL if TEST_MODE else email

    # Find or create ack record
    ack = env['partner.communication.ack'].sudo().search([
        ('notice_key', '=', NOTICE_KEY),
        ('partner_id', '=', partner.id),
    ], limit=1)

    if ack and ack.state != 'pending':
        print(f"  SKIP {partner.name} — ya votó ({ack.state})")
        skipped += 1
        continue

    if DRY_RUN:
        print(f"  DRY  {partner.name} <{send_to}>")
        continue

    if not ack:
        ack = env['partner.communication.ack'].sudo().create({
            'notice_key':    NOTICE_KEY,
            'notice_label':  NOTICE_LABEL,
            'partner_id':    partner.id,
            'partner_name':  partner.name,
            'partner_email': send_to,
        })

    si_url = f"{BASE_URL}/partner-ack/{ack.token}/si"
    no_url = f"{BASE_URL}/partner-ack/{ack.token}/no"

    html = _build_html(
        partner_name=partner.name,
        si_url=si_url,
        no_url=no_url,
        is_test=TEST_MODE,
    )

    env['mail.mail'].sudo().create({
        'subject':    'Consulta Presupuestaria 2026-2027 — Ejerza su voto',
        'email_from': 'Colegio Andrés Bello <votacion@ueipab.edu.ve>',
        'email_to':   f'{partner.name} <{send_to}>',
        'email_cc':   'votacion@ueipab.edu.ve',
        'reply_to':   'votacion@ueipab.edu.ve',
        'body_html':  html,
        'state':      'outgoing',
    })

    print(f"  QUEUED {partner.name} <{send_to}>")
    sent += 1

    if SEND_DELAY:
        time.sleep(SEND_DELAY)

env.cr.commit()

# Trigger mail queue
if not DRY_RUN and sent > 0:
    try:
        env['ir.actions.server'].sudo().browse(3).run()
        print("\n✅ Cola de correos disparada.")
    except Exception:
        env.ref('base.ir_cron_mail_scheduler_action').sudo().method_direct_trigger()
        print("\n✅ Cola de correos disparada (cron).")

print(f"\n{'='*70}")
print(f"ENVIADOS: {sent} | OMITIDOS: {skipped}")
print(f"{'='*70}\n")
