#!/usr/bin/env python3
"""
Cashea Campaign v2 — Email Template (SIN PRECIO)
Versión genérica: no menciona $197,38 — válida para cualquier mes/tarifa.

Ejecutar con Odoo shell:
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
      < /opt/odoo-dev/scripts/create_cashea_campaign_template_v2.py
"""

import sys

print("=" * 70)
print("CAMPAÑA CASHEA v2 (SIN PRECIO) — CREANDO PLANTILLA DE CORREO")
print("=" * 70)

LOGO_URL = "https://dev.ueipab.edu.ve/flyers/school_logo.png"
LOGO_TAG = (
    f'<img src="{LOGO_URL}" alt="Instituto Privado Andrés Bello" '
    f'height="54" style="display:block;max-height:54px;width:auto;border:0;" />'
)
print(f"\n[0] Logo OK — {LOGO_URL}")

SUBJECT = "¡Ahora puedes pagar en el colegio en cuotas quincenales sin interés!"

BODY_HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Cashea — Instituto Privado Andrés Bello</title>
</head>
<body style="margin:0;padding:0;background-color:#EFEFEF;
             font-family:Arial,Helvetica,sans-serif;-webkit-text-size-adjust:100%;">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background-color:#EFEFEF;">
  <tr><td align="center" style="padding:24px 12px;">

    <!-- CARD 600px -->
    <table width="600" cellpadding="0" cellspacing="0" border="0"
           style="max-width:600px;width:100%;background-color:#FFFFFF;
                  border-radius:12px;overflow:hidden;
                  box-shadow:0 6px 24px rgba(0,0,0,0.14);">

      <!-- CABECERA -->
      <tr>
        <td style="background-color:#FFFFFF;padding:20px 28px 0;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align:middle;width:60%;">
                {LOGO_TAG}
              </td>
              <td style="text-align:right;vertical-align:middle;width:40%;">
                <span style="display:inline-block;background-color:#111111;
                             color:#FFD600;font-size:20px;font-weight:900;
                             padding:7px 20px;border-radius:24px;
                             letter-spacing:1px;font-family:Arial,sans-serif;">
                  cashea
                </span>
              </td>
            </tr>
          </table>
          <div style="margin-top:18px;height:4px;
                      background-color:#FFD600;border-radius:2px;"></div>
        </td>
      </tr>

      <!-- HERO -->
      <tr>
        <td style="background-color:#111111;padding:44px 32px 40px;
                   text-align:center;">
          <div style="font-size:11px;color:#FFD600;letter-spacing:3px;
                       text-transform:uppercase;margin-bottom:14px;
                       font-weight:700;">
            ¡NUEVA FORMA DE PAGAR EN EL COLEGIO!
          </div>
          <h1 style="color:#FFFFFF;font-size:26px;font-weight:900;
                      line-height:1.35;margin:0 0 12px;
                      font-family:Arial,sans-serif;">
            Divide tu mensualidad en<br>
            <span style="color:#FFD600;">cuotas quincenales</span>
            sin interés
          </h1>
          <!-- Pill genérica sin precio -->
          <div style="display:inline-block;background-color:#FFD600;
                       color:#111111;font-size:20px;font-weight:900;
                       padding:10px 30px;border-radius:30px;
                       margin:10px 0 18px;letter-spacing:0.5px;">
            0% de interés &nbsp;·&nbsp; 0 recargos extra
          </div>
          <p style="color:#CCCCCC;font-size:14px;line-height:1.7;
                     margin:0 auto;max-width:440px;">
            Gracias a nuestra alianza con
            <strong style="color:#FFD600;">Cashea</strong>,
            ahora puedes cancelar la mensualidad del colegio en
            <strong style="color:#FFFFFF;">cómodas cuotas quincenales</strong>,
            sin recargos y sin intereses.
          </p>
        </td>
      </tr>

      <!-- INTRO -->
      <tr>
        <td style="background-color:#FFFFFF;padding:28px 32px 8px;">
          <p style="color:#555555;font-size:14px;line-height:1.7;margin:0;">
            Nos complace anunciar que el
            <strong>Instituto Privado Andrés Bello</strong> es ahora
            un <strong>comercio aliado de Cashea</strong>. Esto significa que
            puede pagar la mensualidad escolar en cómodas cuotas quincenales,
            completamente <strong style="color:#111111;">sin intereses</strong>.
          </p>
        </td>
      </tr>

      <!-- DEPENDIENDO DE TU NIVEL -->
      <tr>
        <td style="padding:20px 32px 8px;background-color:#FFFFFF;">

          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="border-radius:10px;overflow:hidden;
                         border:2px solid #FFD600;margin-bottom:16px;">

            <!-- Título -->
            <tr>
              <td colspan="4"
                  style="background-color:#111111;color:#FFD600;
                         font-size:11px;font-weight:700;text-align:center;
                         padding:8px 12px 2px;letter-spacing:2px;">
                DEPENDIENDO DE TU NIVEL
              </td>
            </tr>
            <tr>
              <td colspan="4"
                  style="background-color:#111111;color:#FFFFFF;
                         font-size:12px;font-weight:700;text-align:center;
                         padding:2px 12px 10px;letter-spacing:0.5px;">
                DESGLOSE DE TU PAGO CON CASHEA
              </td>
            </tr>

            <!-- Cabecera columnas -->
            <tr style="background-color:#FFFDE7;">
              <td style="padding:8px 10px;color:#555;font-size:11px;
                          font-weight:700;border-bottom:1px solid #FFD600;
                          width:30%;">NIVEL</td>
              <td style="padding:8px 6px;color:#555;font-size:11px;
                          font-weight:700;border-bottom:1px solid #FFD600;
                          text-align:center;width:25%;">INICIAL (D&iacute;a 0)</td>
              <td style="padding:8px 6px;color:#555;font-size:11px;
                          font-weight:700;border-bottom:1px solid #FFD600;
                          text-align:center;width:25%;">CUOTA (D&iacute;a 14)</td>
              <td style="padding:8px 6px;color:#555;font-size:11px;
                          font-weight:700;border-bottom:1px solid #FFD600;
                          text-align:center;width:20%;">INTER&Eacute;S</td>
            </tr>

            <!-- Nivel 1 — Semilla -->
            <tr style="background-color:#FFFFFF;">
              <td style="padding:10px 10px;border-bottom:1px solid #F0F0F0;">
                <span style="display:inline-block;background-color:#E0E0E0;
                             color:#555;font-size:10px;font-weight:700;
                             padding:2px 6px;border-radius:8px;">Nv.1</span>
                <span style="color:#333;font-size:12px;margin-left:4px;">
                  🌱 Semilla</span>
                <div style="color:#888;font-size:10px;margin-top:2px;
                             padding-left:2px;">Nuevo usuario</div>
              </td>
              <td style="padding:10px 6px;text-align:center;font-weight:700;
                          font-size:14px;color:#111;
                          border-bottom:1px solid #F0F0F0;">60%</td>
              <td style="padding:10px 6px;text-align:center;font-size:12px;
                          color:#444;border-bottom:1px solid #F0F0F0;">resto en día 14</td>
              <td style="padding:10px 6px;text-align:center;font-size:13px;
                          color:#00A040;font-weight:700;
                          border-bottom:1px solid #F0F0F0;">$0,00</td>
            </tr>

            <!-- Nivel 2 — Raíz -->
            <tr style="background-color:#FFFDE7;">
              <td style="padding:10px 10px;border-bottom:1px solid #F0F0F0;">
                <span style="display:inline-block;background-color:#FFD600;
                             color:#111;font-size:10px;font-weight:700;
                             padding:2px 6px;border-radius:8px;">Nv.2</span>
                <span style="color:#333;font-size:12px;margin-left:4px;">
                  🌿 Ra&iacute;z</span>
                <div style="color:#888;font-size:10px;margin-top:2px;
                             padding-left:2px;">5 pagos o $120</div>
              </td>
              <td style="padding:10px 6px;text-align:center;font-weight:700;
                          font-size:14px;color:#111;
                          border-bottom:1px solid #F0F0F0;">50%</td>
              <td style="padding:10px 6px;text-align:center;font-size:12px;
                          color:#444;border-bottom:1px solid #F0F0F0;">50% en día 14</td>
              <td style="padding:10px 6px;text-align:center;font-size:13px;
                          color:#00A040;font-weight:700;
                          border-bottom:1px solid #F0F0F0;">$0,00</td>
            </tr>

            <!-- Nivel 3 — Hoja -->
            <tr style="background-color:#FFFFFF;">
              <td style="padding:10px 10px;border-bottom:1px solid #F0F0F0;">
                <span style="display:inline-block;background-color:#FFD600;
                             color:#111;font-size:10px;font-weight:700;
                             padding:2px 6px;border-radius:8px;">Nv.3</span>
                <span style="color:#333;font-size:12px;margin-left:4px;">
                  🍃 Hoja</span>
                <div style="color:#888;font-size:10px;margin-top:2px;
                             padding-left:2px;">10 pagos o $400</div>
              </td>
              <td style="padding:10px 6px;text-align:center;font-weight:700;
                          font-size:14px;color:#111;
                          border-bottom:1px solid #F0F0F0;">40%</td>
              <td style="padding:10px 6px;text-align:center;font-size:12px;
                          color:#444;border-bottom:1px solid #F0F0F0;">m&aacute;s cuotas</td>
              <td style="padding:10px 6px;text-align:center;font-size:13px;
                          color:#00A040;font-weight:700;
                          border-bottom:1px solid #F0F0F0;">$0,00</td>
            </tr>

            <!-- Niveles 4-6 -->
            <tr>
              <td colspan="4" style="background-color:#111111;padding:10px 12px;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td>
                      <span style="color:#FFD600;font-size:11px;font-weight:700;">
                        🌳 Nv.4 Tronco &nbsp;·&nbsp;
                        🌲 Nv.5 &Aacute;rbol &nbsp;·&nbsp;
                        🌻 Nv.6 Araguaney
                      </span><br>
                      <span style="color:#CCCCCC;font-size:11px;line-height:1.5;">
                        Inicial desde
                        <strong style="color:#FFD600;">25%</strong>
                        hasta <strong style="color:#FFD600;">0%</strong>
                        con socios selectos &mdash; condiciones a&uacute;n m&aacute;s favorables
                      </span>
                    </td>
                    <td style="text-align:right;vertical-align:middle;
                                white-space:nowrap;padding-left:8px;">
                      <span style="color:#FFD600;font-size:16px;">&#9733;&#9733;&#9733;</span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Pie fijo -->
            <tr style="background-color:#FFFDE7;">
              <td colspan="4"
                  style="padding:8px 12px;text-align:center;
                         font-size:12px;color:#555;">
                En todos los niveles:
                <strong style="color:#111111;">Intereses = $0,00 siempre</strong>
              </td>
            </tr>
          </table>

          <!-- Nota cómo subir de nivel -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0"
                 style="background-color:#F8F8F8;border-radius:8px;
                         border-left:3px solid #FFD600;margin-bottom:16px;">
            <tr>
              <td style="padding:12px 16px;">
                <div style="color:#111111;font-size:12px;font-weight:700;
                             margin-bottom:4px;">&#128200; &iquest;C&oacute;mo subir de nivel?</div>
                <div style="color:#555555;font-size:12px;line-height:1.65;">
                  Cada cuota pagada a tiempo acumula puntos y te sube de nivel.
                  Con solo <strong>5 pagos puntuales</strong> alcanzas el
                  <strong>Nivel 2 (Ra&iacute;z)</strong> y tu inicial baja al 50%.
                  Con <strong>10 pagos o $400</strong> en compras llegas al
                  <strong>Nivel 3 (Hoja)</strong> con condiciones a&uacute;n mejores.
                  ¡Entre m&aacute;s usas Cashea, menos pagas por adelantado!
                </div>
              </td>
            </tr>
          </table>

        </td>
      </tr>

      <!-- ¿QUÉ ES CASHEA? -->
      <tr>
        <td style="background-color:#F8F8F8;padding:28px 32px;">
          <h2 style="color:#111111;font-size:16px;font-weight:900;
                      margin:0 0 10px;font-family:Arial,sans-serif;">
            ¿Qué es Cashea?
          </h2>
          <p style="color:#444444;font-size:13px;line-height:1.75;margin:0;">
            Cashea es la
            <strong>plataforma venezolana líder de pagos a cuotas</strong>
            — más de <strong>5 millones de usuarios</strong> y
            <strong>5.000 comercios aliados</strong> en todo el país.
            Funciona bajo el modelo <em>compra ahora, paga después</em>:
            pagas una parte al comprar y el resto 14 días después,
            <strong>sin ningún tipo de interés</strong>.
          </p>
        </td>
      </tr>

      <!-- 3 PASOS -->
      <tr>
        <td style="background-color:#FFFFFF;padding:28px 32px 24px;">
          <h2 style="color:#111111;font-size:16px;font-weight:900;
                      text-align:center;margin:0 0 22px;
                      font-family:Arial,sans-serif;">
            Cómo pagar en 3 pasos simples
          </h2>
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td width="33%" style="text-align:center;padding:0 8px;
                                      vertical-align:top;">
                <div style="width:52px;height:52px;background-color:#FFD600;
                             border-radius:50%;margin:0 auto 12px;
                             line-height:52px;color:#111111;
                             font-size:22px;font-weight:900;">1</div>
                <div style="color:#111111;font-weight:700;font-size:13px;
                             margin-bottom:6px;">Descarga Cashea</div>
                <div style="color:#666;font-size:12px;line-height:1.6;">
                  Regístrate en la app en menos de 3 minutos y recibe tu
                  línea de crédito al instante.
                </div>
              </td>
              <td width="33%" style="text-align:center;padding:0 8px;
                                      vertical-align:top;">
                <div style="width:52px;height:52px;background-color:#111111;
                             border-radius:50%;margin:0 auto 12px;
                             line-height:52px;color:#FFD600;
                             font-size:22px;font-weight:900;">2</div>
                <div style="color:#111111;font-weight:700;font-size:13px;
                             margin-bottom:6px;">Elige Cashea al pagar</div>
                <div style="color:#666;font-size:12px;line-height:1.6;">
                  En la caja del colegio, selecciona
                  <strong>Cashea</strong> como tu método de pago.
                </div>
              </td>
              <td width="33%" style="text-align:center;padding:0 8px;
                                      vertical-align:top;">
                <div style="width:52px;height:52px;background-color:#FFD600;
                             border-radius:50%;margin:0 auto 12px;
                             line-height:52px;color:#111111;
                             font-size:22px;font-weight:900;">3</div>
                <div style="color:#111111;font-weight:700;font-size:13px;
                             margin-bottom:6px;">Paga en cuotas</div>
                <div style="color:#666;font-size:12px;line-height:1.6;">
                  Tu inicial hoy y el resto en 14 días.
                  <strong>Sin intereses. Sin recargos.</strong>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- BENEFICIOS -->
      <tr>
        <td style="background-color:#F8F8F8;padding:24px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td width="50%" style="padding:6px 8px 6px 0;vertical-align:top;">
                <table cellpadding="0" cellspacing="0" border="0"><tr>
                  <td style="width:22px;vertical-align:top;">
                    <div style="width:20px;height:20px;background-color:#FFD600;
                                 border-radius:50%;text-align:center;
                                 line-height:20px;color:#111;font-size:12px;
                                 font-weight:900;">&#10003;</div>
                  </td>
                  <td style="padding-left:8px;color:#444;font-size:13px;
                              line-height:1.6;">
                    <strong>0% de interés</strong> siempre
                  </td>
                </tr></table>
              </td>
              <td width="50%" style="padding:6px 0 6px 8px;vertical-align:top;">
                <table cellpadding="0" cellspacing="0" border="0"><tr>
                  <td style="width:22px;vertical-align:top;">
                    <div style="width:20px;height:20px;background-color:#FFD600;
                                 border-radius:50%;text-align:center;
                                 line-height:20px;color:#111;font-size:12px;
                                 font-weight:900;">&#10003;</div>
                  </td>
                  <td style="padding-left:8px;color:#444;font-size:13px;
                              line-height:1.6;">
                    <strong>Aprobación inmediata</strong> en 3 min
                  </td>
                </tr></table>
              </td>
            </tr>
            <tr>
              <td width="50%" style="padding:6px 8px 6px 0;vertical-align:top;">
                <table cellpadding="0" cellspacing="0" border="0"><tr>
                  <td style="width:22px;vertical-align:top;">
                    <div style="width:20px;height:20px;background-color:#FFD600;
                                 border-radius:50%;text-align:center;
                                 line-height:20px;color:#111;font-size:12px;
                                 font-weight:900;">&#10003;</div>
                  </td>
                  <td style="padding-left:8px;color:#444;font-size:13px;
                              line-height:1.6;">
                    <strong>Inicial desde 60%</strong> (nuevo) hasta 0%*
                  </td>
                </tr></table>
              </td>
              <td width="50%" style="padding:6px 0 6px 8px;vertical-align:top;">
                <table cellpadding="0" cellspacing="0" border="0"><tr>
                  <td style="width:22px;vertical-align:top;">
                    <div style="width:20px;height:20px;background-color:#FFD600;
                                 border-radius:50%;text-align:center;
                                 line-height:20px;color:#111;font-size:12px;
                                 font-weight:900;">&#10003;</div>
                  </td>
                  <td style="padding-left:8px;color:#444;font-size:13px;
                              line-height:1.6;">
                    <strong>Recordatorios</strong> automáticos de cuota
                  </td>
                </tr></table>
              </td>
            </tr>
            <tr>
              <td width="50%" style="padding:6px 8px 6px 0;vertical-align:top;">
                <table cellpadding="0" cellspacing="0" border="0"><tr>
                  <td style="width:22px;vertical-align:top;">
                    <div style="width:20px;height:20px;background-color:#FFD600;
                                 border-radius:50%;text-align:center;
                                 line-height:20px;color:#111;font-size:12px;
                                 font-weight:900;">&#10003;</div>
                  </td>
                  <td style="padding-left:8px;color:#444;font-size:13px;
                              line-height:1.6;">
                    <strong>+5 millones</strong> de venezolanos lo usan
                  </td>
                </tr></table>
              </td>
              <td width="50%" style="padding:6px 0 6px 8px;vertical-align:top;">
                <table cellpadding="0" cellspacing="0" border="0"><tr>
                  <td style="width:22px;vertical-align:top;">
                    <div style="width:20px;height:20px;background-color:#FFD600;
                                 border-radius:50%;text-align:center;
                                 line-height:20px;color:#111;font-size:12px;
                                 font-weight:900;">&#10003;</div>
                  </td>
                  <td style="padding-left:8px;color:#444;font-size:13px;
                              line-height:1.6;">
                    <strong>Disponible</strong> en caja del colegio
                  </td>
                </tr></table>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- CTA -->
      <tr>
        <td style="background-color:#111111;padding:36px 32px;
                   text-align:center;">
          <h2 style="color:#FFD600;font-size:20px;font-weight:900;
                      margin:0 0 10px;font-family:Arial,sans-serif;">
            ¡Descarga Cashea y empieza hoy!
          </h2>
          <p style="color:#CCCCCC;font-size:14px;line-height:1.7;
                     margin:0 auto 24px;max-width:400px;">
            Crea tu cuenta en minutos, obtén tu línea de crédito
            y paga tu próxima mensualidad en cómodas cuotas sin interés.
          </p>
          <table cellpadding="0" cellspacing="0" border="0" align="center">
            <tr>
              <td style="padding:0 6px 8px;">
                <a href="https://play.google.com/store/apps/details?id=com.cashea.app"
                   style="display:inline-block;background-color:#FFD600;
                          color:#111111;text-decoration:none;font-size:13px;
                          font-weight:700;padding:13px 22px;border-radius:26px;
                          font-family:Arial,sans-serif;letter-spacing:0.5px;">
                  &#128242; Google Play (Android)
                </a>
              </td>
              <td style="padding:0 6px 8px;">
                <a href="https://apps.apple.com/ve/app/cashea/id1620708795"
                   style="display:inline-block;background-color:#FFD600;
                          color:#111111;text-decoration:none;font-size:13px;
                          font-weight:700;padding:13px 22px;border-radius:26px;
                          font-family:Arial,sans-serif;letter-spacing:0.5px;">
                  &#127822; App Store (iPhone)
                </a>
              </td>
            </tr>
            <tr>
              <td colspan="2" style="padding:4px 6px 0;text-align:center;">
                <a href="https://www.cashea.app/"
                   style="display:inline-block;background-color:transparent;
                          color:#FFD600;text-decoration:none;font-size:12px;
                          font-weight:700;padding:9px 22px;border-radius:26px;
                          border:2px solid #FFD600;
                          font-family:Arial,sans-serif;letter-spacing:0.5px;">
                  &#127760; cashea.app
                </a>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- CONTACTO -->
      <tr>
        <td style="background-color:#FFFFFF;padding:0;">
          <div style="height:3px;background-color:#FFD600;"></div>
          <div style="padding:20px 32px;text-align:center;">
            <p style="color:#666666;font-size:12px;line-height:1.7;margin:0;">
              ¿Tiene dudas sobre cómo usar Cashea en el colegio?<br>
              Escríbanos a
              <a href="mailto:pagos@ueipab.edu.ve"
                 style="color:#111111;text-decoration:none;font-weight:700;">
                pagos@ueipab.edu.ve
              </a>
              y con gusto le orientamos.
            </p>
          </div>
        </td>
      </tr>

      <!-- PIE -->
      <tr>
        <td style="background-color:#111111;padding:22px 32px;
                   text-align:center;">
          <p style="color:#FFFFFF;font-size:12px;font-weight:700;
                     margin:0 0 4px;letter-spacing:0.5px;">
            Instituto Privado Andrés Bello &mdash; UEIPAB
          </p>
          <p style="color:#888888;font-size:11px;line-height:1.6;margin:0 0 8px;">
            El Tigre, Anzoátegui &mdash; Venezuela
          </p>
          <p style="color:#555555;font-size:10px;line-height:1.5;margin:0;">
            Este correo fue enviado a nuestra comunidad de representantes.<br>
            Consultas: <a href="mailto:pagos@ueipab.edu.ve"
                          style="color:#FFD600;text-decoration:none;">
              pagos@ueipab.edu.ve</a>
          </p>
        </td>
      </tr>

    </table><!-- /CARD -->

  </td></tr>
</table><!-- /WRAPPER -->

</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# Crear / actualizar plantilla en Odoo
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_NAME = "Cashea — Campaña v2 (sin precio)"

print(f"\n[1] Buscando modelo res.partner...")
partner_model = env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
if not partner_model:
    print("ERROR: modelo res.partner no encontrado")
    sys.exit(1)
print(f"    OK — id={partner_model.id}")

print(f"\n[2] Verificando si la plantilla ya existe...")
Template = env['mail.template']
existing = Template.search([('name', '=', TEMPLATE_NAME)], limit=1)

if existing:
    print(f"    Plantilla existente (id={existing.id}) — actualizando...")
    existing.write({
        'subject': SUBJECT,
        'body_html': BODY_HTML,
        'email_from': '"Instituto Privado Andrés Bello" <pagos@ueipab.edu.ve>',
        'email_to': '{{ object.email }}',
        'auto_delete': False,
    })
    tmpl = existing
    print(f"    Plantilla actualizada (id={tmpl.id})")
else:
    print(f"    No existe — creando nueva...")
    tmpl = Template.create({
        'name': TEMPLATE_NAME,
        'model_id': partner_model.id,
        'subject': SUBJECT,
        'body_html': BODY_HTML,
        'email_from': '"Instituto Privado Andrés Bello" <pagos@ueipab.edu.ve>',
        'email_to': '{{ object.email }}',
        'auto_delete': False,
        'lang': 'es_VE',
    })
    print(f"    Plantilla creada (id={tmpl.id})")

env.cr.commit()

print("\n" + "=" * 70)
print(f"PLANTILLA v2 LISTA — id={tmpl.id} | '{tmpl.name}'")
print(f"Asunto : {tmpl.subject}")
print("=" * 70)
