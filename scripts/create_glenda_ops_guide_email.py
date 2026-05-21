"""
Creates the Glenda AI Agent Operational Guide email template in Odoo
and sends a test to gustavo.perdomo@ueipab.edu.ve

Usage:
    python3 scripts/create_glenda_ops_guide_email.py --env testing
    python3 scripts/create_glenda_ops_guide_email.py --env production
"""
import json, xmlrpc.client, argparse

cfg  = json.load(open('/opt/odoo-dev/config/production.json'))
ENVS = {
    'testing':    ('http://localhost:8019', 'testing',   2, '35baa2abcc6dee920fa75014f0274c8e551871ce'),
    'production': (cfg['production']['xmlrpc']['url'], cfg['production']['xmlrpc']['db'],
                   2, cfg['production']['xmlrpc']['api_key']),
}

SUBJECT = '🤖 Guía Operativa — Glenda AI Agent | Colegio Andrés Bello'
FROM    = 'Colegio Andrés Bello <soporte@ueipab.edu.ve>'
TO_TEST = 'Gustavo Perdomo <gustavo.perdomo@ueipab.edu.ve>'

BODY = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Guía Operativa — Glenda AI Agent</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0f4f8;">
<tr><td align="center" style="padding:28px 12px;">
<table width="620" cellpadding="0" cellspacing="0" border="0"
       style="max-width:620px;width:100%;border-radius:14px;overflow:hidden;
              box-shadow:0 6px 32px rgba(0,0,0,0.13);">

  <!-- ── HEADER ── -->
  <tr>
    <td style="background:linear-gradient(135deg,#0a1628 0%,#1a3a6b 100%);
               padding:36px 40px 28px;text-align:center;">
      <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"
           alt="Colegio Andrés Bello" width="72" height="72"
           style="border-radius:50%;border:3px solid #C8A951;
                  display:block;margin:0 auto 16px;object-fit:cover;"/>
      <p style="margin:0 0 6px;font-size:11px;font-weight:700;color:#C8A951;
                letter-spacing:2px;text-transform:uppercase;">Módulo AI Agent — Odoo</p>
      <h1 style="margin:0 0 8px;font-size:26px;font-weight:800;color:#ffffff;">
        Guía Operativa<br/>Glenda AI Agent
      </h1>
      <p style="margin:0;font-size:14px;color:#8badd4;">
        Para el equipo de atención al cliente · Colegio Andrés Bello
      </p>
    </td>
  </tr>

  <!-- ── INTRO ── -->
  <tr>
    <td style="background:#ffffff;padding:32px 40px 20px;">
      <p style="margin:0 0 16px;font-size:15px;color:#374151;line-height:1.7;">
        Esta guía te explica cómo usar <strong>Glenda</strong>, nuestra asistente virtual de
        inteligencia artificial, para gestionar conversaciones con representantes desde Odoo.
        No necesitas experiencia previa — sigue los pasos y Glenda hace el trabajo.
      </p>

      <!-- WHAT IS GLENDA — 3 cards -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:8px;">
        <tr>
          <td width="31%" style="background:#f0f9ff;border-radius:10px;border:1px solid #bae6fd;
                                  padding:16px 12px;text-align:center;vertical-align:top;">
            <div style="font-size:28px;margin-bottom:8px;">🤖</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0369a1;">Bot WhatsApp</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Responde automáticamente en WhatsApp y Telegram
            </p>
          </td>
          <td width="4%"></td>
          <td width="31%" style="background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;
                                  padding:16px 12px;text-align:center;vertical-align:top;">
            <div style="font-size:28px;margin-bottom:8px;">💰</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#15803d;">Experta en Pagos</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Conoce mensualidades, saldos y propuesta 2026-2027
            </p>
          </td>
          <td width="4%"></td>
          <td width="31%" style="background:#fefce8;border-radius:10px;border:1px solid #fde68a;
                                  padding:16px 12px;text-align:center;vertical-align:top;">
            <div style="font-size:28px;margin-bottom:8px;">⚡</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#b45309;">24/7 Activa</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Responde al instante por Telegram, cada 5 min por WA
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 1: HOW TO START ── -->
  <tr>
    <td style="background:#f8faff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        1 · Cómo Iniciar una Conversación
      </p>
      <!-- Steps -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <!-- Step 1 -->
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">1</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Menú AI Agent</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Odoo → AI Agent → Operaciones → <strong>Iniciar Conversación</strong>
            </p>
          </td>
          <td width="4%" style="text-align:center;color:#C8A951;font-size:20px;
                                  vertical-align:middle;padding-top:0;">›</td>
          <!-- Step 2 -->
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">2</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Elige Canal</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Selecciona <strong>WhatsApp</strong> o <strong>Telegram</strong>, luego Skill, Contacto y Teléfono
            </p>
          </td>
          <td width="4%" style="text-align:center;color:#C8A951;font-size:20px;
                                  vertical-align:middle;padding-top:0;">›</td>
          <!-- Step 3 -->
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">3</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Pega el Mensaje</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Si el representante ya escribió por otro canal, pégalo en el campo <em>"Mensaje del representante"</em>
            </p>
          </td>
          <td width="4%" style="text-align:center;color:#C8A951;font-size:20px;
                                  vertical-align:middle;padding-top:0;">›</td>
          <!-- Step 4 -->
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#0a1628;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">4</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Elegir Acción</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              <strong>WhatsApp:</strong> 💾 Borrador · 🚀 Iniciar<br/>
              <strong>Telegram:</strong> 📲 Enviar Invitación
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 2: DRAFT VS FIRE ── -->
  <tr>
    <td style="background:#ffffff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        2 · Guardar Borrador vs Iniciar Ahora (WhatsApp)
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="48%" style="background:#f0fdf4;border-radius:10px;border:2px solid #86efac;
                                  padding:18px 20px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:14px;font-weight:800;color:#15803d;">
              💾 Guardar Borrador
            </p>
            <p style="margin:0 0 8px;font-size:12px;color:#374151;line-height:1.6;">
              Crea la conversación <strong>sin enviar nada</strong> al cliente.
              Abre el formulario para que puedas:
            </p>
            <ul style="margin:0;padding-left:16px;font-size:12px;color:#374151;line-height:1.8;">
              <li>Leer el mensaje guardado (caja amarilla)</li>
              <li>Verificar el teléfono y contacto</li>
              <li>Confirmar que es el cliente correcto</li>
            </ul>
            <p style="margin:10px 0 0;font-size:12px;color:#15803d;font-weight:700;">
              ✅ Recomendado para nuevos agentes
            </p>
          </td>
          <td width="4%"></td>
          <td width="48%" style="background:#eff6ff;border-radius:10px;border:2px solid #93c5fd;
                                  padding:18px 20px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:14px;font-weight:800;color:#1d4ed8;">
              🚀 Iniciar Ahora
            </p>
            <p style="margin:0 0 8px;font-size:12px;color:#374151;line-height:1.6;">
              Crea la conversación y <strong>envía al cliente inmediatamente</strong>.
              Glenda responde en segundos con:
            </p>
            <ul style="margin:0;padding-left:16px;font-size:12px;color:#374151;line-height:1.8;">
              <li>Respuesta directa al mensaje (si lo pegaste)</li>
              <li>O saludo genérico (si no había mensaje)</li>
            </ul>
            <p style="margin:10px 0 0;font-size:12px;color:#1d4ed8;font-weight:700;">
              ⚡ Para agentes con experiencia
            </p>
          </td>
        </tr>
      </table>
      <!-- TIP box -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:16px;">
        <tr>
          <td style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;
                     padding:12px 16px;">
            <p style="margin:0;font-size:12px;color:#78350f;line-height:1.6;">
              💡 <strong>Consejo:</strong> Si ya tienes el mensaje del cliente, siempre pégalo en el campo
              <em>"Mensaje del representante"</em>. Glenda consultará el sistema y
              responderá directamente con datos reales — sin hacerle preguntas al cliente.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 3: TELEGRAM INVITATION ── -->
  <tr>
    <td style="background:#f0f4ff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        3 · Invitar a un Representante a Telegram
      </p>
      <p style="margin:0 0 16px;font-size:13px;color:#374151;line-height:1.6;">
        Si un representante te contactó por otro canal (presencial, correo, otro número),
        puedes invitarle a usar <strong>@GlendaUeipabBot</strong> en Telegram con un solo clic.
        Telegram es <em>instantáneo</em>, sin la restricción de 24 horas de WhatsApp, y gratuito.
      </p>
      <!-- Steps -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
        <tr>
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#1a3a6b;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">1</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Canal = Telegram</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              En el formulario, selecciona <strong>Telegram</strong> en el campo Canal
            </p>
          </td>
          <td width="4%" style="text-align:center;color:#C8A951;font-size:20px;vertical-align:middle;">›</td>
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#1a3a6b;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">2</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Selecciona Contacto</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              El contacto Odoo es <strong>obligatorio</strong> — el teléfono se llena automáticamente
            </p>
          </td>
          <td width="4%" style="text-align:center;color:#C8A951;font-size:20px;vertical-align:middle;">›</td>
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#1a3a6b;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">3</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Enviar Invitación</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Haz clic en <strong>📲 Enviar Invitación Telegram</strong> — llega por WhatsApp con el enlace al bot
            </p>
          </td>
          <td width="4%" style="text-align:center;color:#C8A951;font-size:20px;vertical-align:middle;">›</td>
          <td width="22%" style="text-align:center;vertical-align:top;padding:0 4px;">
            <div style="width:36px;height:36px;background:#1a3a6b;border-radius:50%;
                        color:#C8A951;font-size:16px;font-weight:800;
                        line-height:36px;text-align:center;margin:0 auto 10px;">4</div>
            <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#0a1628;">Representante Conectado</p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.5;">
              Toca el enlace, pulsa <em>Iniciar</em> en Telegram y queda vinculado automáticamente
            </p>
          </td>
        </tr>
      </table>
      <!-- Benefits -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:14px;">
        <tr>
          <td width="31%" style="background:#f0f9ff;border-radius:10px;border:1px solid #bae6fd;
                                  padding:14px 12px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">⚡</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0369a1;">Instantáneo</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Glenda responde en segundos — sin esperar el cron de 5 min de WA</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;
                                  padding:14px 12px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">🔓</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#15803d;">Sin Límite 24h</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Glenda puede escribir al representante en cualquier momento</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#fefce8;border-radius:10px;border:1px solid #fde68a;
                                  padding:14px 12px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">💸</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#b45309;">Sin Créditos WA</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Telegram es gratuito — solo necesitan la app instalada</p>
          </td>
        </tr>
      </table>
      <!-- Note -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:14px;">
        <tr>
          <td style="background:#eff6ff;border-left:4px solid #3b82f6;border-radius:0 8px 8px 0;
                     padding:12px 16px;">
            <p style="margin:0;font-size:12px;color:#1e40af;line-height:1.6;">
              💡 <strong>Nota:</strong> Si el representante ya tiene Telegram vinculado, el sistema mostrará
              un aviso automático y no enviará la invitación nuevamente.
              Puedes verificar revisando el campo <em>Telegram Chat ID</em> en su ficha de contacto en Odoo.
            </p>
          </td>
        </tr>
      </table>

      <!-- Parent-initiated flow -->
      <p style="margin:0 0 10px;font-size:13px;font-weight:700;color:#0a1628;">
        📲 Cuando el representante abre el bot por su cuenta
      </p>
      <p style="margin:0 0 12px;font-size:12px;color:#374151;line-height:1.6;">
        Si un representante encuentra <strong>@GlendaUeipabBot</strong> directamente en Telegram
        y pulsa <em>Iniciar</em>, verá un menú de bienvenida con un botón especial para
        compartir su número de teléfono:
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:14px;">
        <tr>
          <td width="48%" style="background:#f8faff;border:1px solid #e2e8f0;border-radius:10px;
                                  padding:14px 16px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#0369a1;">
              📱 Compartir mi número (recomendado)
            </p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.6;">
              El representante toca el botón → Telegram muestra una confirmación nativa del sistema →
              si acepta, Glenda vincula su cuenta automáticamente y lo identifica en Odoo.
              <strong>Una sola vez, sin escribir nada.</strong>
            </p>
          </td>
          <td width="4%"></td>
          <td width="48%" style="background:#f8faff;border:1px solid #e2e8f0;border-radius:10px;
                                  padding:14px 16px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:#64748b;">
              1️⃣–5️⃣ Opciones de texto
            </p>
            <p style="margin:0;font-size:11px;color:#64748b;line-height:1.6;">
              Si prefiere no compartir su número, puede tocar cualquier opción del menú
              y Glenda la atiende normalmente. Puede proporcionar su cédula más adelante
              si necesita ver su saldo.
            </p>
          </td>
        </tr>
      </table>

      <!-- /vincular re-offer -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;
                     padding:12px 16px;">
            <p style="margin:0;font-size:12px;color:#78350f;line-height:1.6;">
              🔁 <strong>¿El representante rechazó compartir su número por error?</strong>
              No hay problema — puede escribir el comando <code>/vincular</code> en cualquier momento
              dentro del chat con Glenda y el botón de compartir reaparecerá inmediatamente.
              También puede proporcionarle su cédula directamente si lo prefiere.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 4: WHAT GLENDA KNOWS ── -->
  <tr>
    <td style="background:#f8faff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        4 · Lo que Glenda Sabe
      </p>
      <p style="margin:0 0 16px;font-size:13px;color:#374151;">
        Glenda consulta el sistema automáticamente y responde con datos reales. No hace falta que el cliente
        proporcione información que el colegio ya tiene.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">💰</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Mensualidad</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Tarifa actual con descuentos por hermanos aplicados</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">📊</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Pronóstico Año</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Meses restantes Jun–Ago · Total regular y pronto pago</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">🗳️</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Propuesta 2026-27</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Opciones A y B · Votación 22–26 mayo</p>
          </td>
        </tr>
        <tr><td colspan="5" style="height:8px;"></td></tr>
        <tr>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">🎓</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Datos del Alumno</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Nombre, grado y sección desde directorio escolar</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">📋</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Saldo en Sistema</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Facturas pendientes reales de Odoo</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">💳</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Medios de Pago</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Transferencia · Zelle · Cashea · Tarjeta · USD</p>
          </td>
        </tr>
        <tr><td colspan="5" style="height:8px;"></td></tr>
        <tr>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">📅</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Costos Anuales</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Seguro · Guía inglés · Olimpiadas · Enciclopedia</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">🏫</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Info Institucional</p>
            <p style="margin:0;font-size:10px;color:#64748b;">Horarios · Actividades · Alianzas · Reglamentos</p>
          </td>
          <td width="2%"></td>
          <td width="31%" style="background:#fff;border-radius:8px;border:1px solid #e2e8f0;
                                  padding:14px;text-align:center;vertical-align:top;">
            <div style="font-size:22px;margin-bottom:6px;">📌</div>
            <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:#0a1628;">Inscripción Anticipada</p>
            <p style="margin:0;font-size:10px;color:#64748b;">$187,51 · Válida hasta 31 julio 2026</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 5: CONVERSATION STATES ── -->
  <tr>
    <td style="background:#ffffff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        5 · Estados de la Conversación
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding:6px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#e2e8f0;color:#475569;
                         font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">
              ● BORRADOR
            </span>
          </td>
          <td style="padding:6px 0 6px 12px;font-size:12px;color:#374151;">
            Conversación creada pero <strong>no enviada</strong>. Revisa y haz clic en <em>Iniciar Conversación</em>.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#dbeafe;color:#1d4ed8;
                         font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">
              ● ACTIVA
            </span>
          </td>
          <td style="padding:6px 0 6px 12px;font-size:12px;color:#374151;">
            Glenda está <strong>procesando</strong> el mensaje del cliente. Respuesta en camino.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#fef3c7;color:#b45309;
                         font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">
              ● ESPERANDO
            </span>
          </td>
          <td style="padding:6px 0 6px 12px;font-size:12px;color:#374151;">
            Glenda respondió y <strong>espera respuesta del cliente</strong>. Normal — usa 🔄 para actualizar.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#dcfce7;color:#15803d;
                         font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">
              ● RESUELTA
            </span>
          </td>
          <td style="padding:6px 0 6px 12px;font-size:12px;color:#374151;">
            Conversación <strong>cerrada exitosamente</strong>. El cliente fue atendido.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;vertical-align:middle;">
            <span style="display:inline-block;background:#fee2e2;color:#b91c1c;
                         font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;">
              ● FALLIDA
            </span>
          </td>
          <td style="padding:6px 0 6px 12px;font-size:12px;color:#374151;">
            Error o tiempo agotado. <strong>Requiere atención manual</strong> — notifica a soporte@ueipab.edu.ve
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 6: REFRESH + MONITORING ── -->
  <tr>
    <td style="background:#f8faff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        6 · Seguimiento en Tiempo Real
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="48%" style="vertical-align:top;">
            <p style="margin:0 0 10px;font-size:13px;font-weight:700;color:#0a1628;">
              🔄 Botón Actualizar
            </p>
            <p style="margin:0 0 12px;font-size:12px;color:#374151;line-height:1.6;">
              Al abrir una conversación en estado <em>Esperando</em> o <em>Activa</em>,
              verás el botón <strong>🔄 Actualizar</strong> en la parte superior.
              Haz clic para recargar los mensajes sin salir de la pantalla.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#0a1628;border-radius:6px;padding:8px 16px;
                           text-align:center;width:auto;">
                  <span style="color:#C8A951;font-size:13px;font-weight:700;">🔄 Actualizar</span>
                </td>
              </tr>
            </table>
          </td>
          <td width="4%"></td>
          <td width="48%" style="vertical-align:top;">
            <p style="margin:0 0 10px;font-size:13px;font-weight:700;color:#0a1628;">
              📋 Lista de Conversaciones
            </p>
            <p style="margin:0 0 10px;font-size:12px;color:#374151;line-height:1.6;">
              Desde <strong>AI Agent → Conversaciones</strong> puedes ver todas las conversaciones activas.
              Agrupa por Canal o Estado para encontrar rápidamente las que necesitan atención.
            </p>
            <p style="margin:0;font-size:12px;color:#374151;line-height:1.6;">
              Conversaciones en rojo (<em>Fallida</em>) requieren acción inmediata.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 7: WHEN TO INTERVENE ── -->
  <tr>
    <td style="background:#ffffff;padding:28px 40px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        7 · Cuándo Intervenir Manualmente
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background:#fef2f2;border-left:4px solid #ef4444;border-radius:0 8px 8px 0;
                     padding:16px 20px;margin-bottom:10px;">
            <p style="margin:0 0 10px;font-size:13px;font-weight:700;color:#991b1b;">
              ⚠️ Señales de que debes intervenir:
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td width="48%" style="vertical-align:top;font-size:12px;color:#374151;line-height:1.8;
                                        padding-right:10px;">
                  ❌ Estado <strong>Fallida</strong> sin resolverse<br/>
                  ❌ Cliente responde con queja grave<br/>
                  ❌ Solicitud de excepción o descuento especial<br/>
                  ❌ Disputa de cobro o reclamo formal
                </td>
                <td width="48%" style="vertical-align:top;font-size:12px;color:#374151;line-height:1.8;">
                  ❌ Cliente amenaza con acciones legales<br/>
                  ❌ Glenda no encontró los datos del cliente<br/>
                  ❌ Conversación lleva más de 72h sin respuesta<br/>
                  ❌ Cliente pide hablar con una persona
                </td>
              </tr>
            </table>
            <p style="margin:12px 0 0;font-size:12px;color:#991b1b;">
              En estos casos: cierra la conversación con <em>Resolver Manualmente</em> y
              escribe a <strong>pagos@ueipab.edu.ve</strong> o <strong>soporte@ueipab.edu.ve</strong>
              con el resumen del caso.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── SECTION 8: QUICK TIPS ── -->
  <tr>
    <td style="background:#f8faff;padding:28px 40px 20px;">
      <p style="margin:0 0 18px;font-size:16px;font-weight:800;color:#0a1628;
                text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #C8A951;
                padding-bottom:8px;">
        8 · Tips Rápidos
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="padding:6px 0;font-size:12px;color:#374151;line-height:1.6;">
            ✅ <strong>Siempre pega el mensaje original</strong> del cliente — Glenda responde mucho mejor con contexto real.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:12px;color:#374151;line-height:1.6;">
            ✅ <strong>Usa Guardar Borrador</strong> si no estás seguro del teléfono o el contacto antes de enviar.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:12px;color:#374151;line-height:1.6;">
            ✅ <strong>No dupliques conversaciones</strong> — si ya existe una activa para ese cliente, Glenda te avisará.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:12px;color:#374151;line-height:1.6;">
            ✅ <strong>El cliente recibirá la respuesta en segundos</strong> — no es necesario hacer seguimiento inmediato.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:12px;color:#374151;line-height:1.6;">
            ✅ <strong>Haz clic en 🔄 Actualizar</strong> para ver si el cliente ya respondió, en lugar de recargar la página.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:12px;color:#374151;line-height:1.6;">
            ✅ <strong>Invita a Telegram</strong> a representantes que preguntan con frecuencia — es más rápido y no consume créditos de WhatsApp. Usa Canal = Telegram en el formulario de inicio.
          </td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:12px;color:#374151;line-height:1.6;">
            ✅ Si un representante dice que rechazó compartir su número por error, indícale que escriba <strong>/vincular</strong> en el chat con Glenda — el botón reaparece de inmediato.
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ── CTA ── -->
  <tr>
    <td style="background:#ffffff;padding:20px 40px 28px;text-align:center;">
      <p style="margin:0 0 16px;font-size:13px;color:#374151;">
        Accede al módulo directamente:
      </p>
      <a href="https://odoo.ueipab.edu.ve/web#menu_id=656&action=923&cids=1"
         style="display:inline-block;background:linear-gradient(135deg,#0a1628,#1a3a6b);
                color:#C8A951;text-decoration:none;font-size:14px;font-weight:700;
                padding:13px 40px;border-radius:50px;letter-spacing:0.5px;">
        🤖 Abrir AI Agent en Odoo
      </a>
    </td>
  </tr>

  <!-- ── FOOTER ── -->
  <tr>
    <td style="background:#0a1628;padding:22px 40px;text-align:center;">
      <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"
           alt="Colegio Andrés Bello" width="40" height="40"
           style="border-radius:50%;border:2px solid #C8A951;
                  display:block;margin:0 auto 10px;object-fit:cover;"/>
      <p style="margin:0 0 4px;font-size:12px;font-weight:700;color:#C8A951;">
        Equipo de Tecnología · Colegio Andrés Bello
      </p>
      <p style="margin:0 0 8px;font-size:11px;color:#8badd4;">
        El Tigre, Venezuela
      </p>
      <p style="margin:0;font-size:11px;color:#4b6080;">
        <a href="mailto:soporte@ueipab.edu.ve" style="color:#4b6080;text-decoration:none;">soporte@ueipab.edu.ve</a>
        &nbsp;·&nbsp;
        <a href="https://t.me/GlendaUeipabBot" style="color:#4b6080;text-decoration:none;">@GlendaUeipabBot</a>
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def send_test(env_name, to_email):
    url, db, uid, key = ENVS[env_name]
    m = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    def call(model, method, args=None, kw=None):
        return m.execute_kw(db, uid, key, model, method, args or [], kw or {})

    new_id = call('mail.mail', 'create', [[{
        'subject'   : SUBJECT,
        'body_html' : BODY,
        'email_to'  : to_email,
        'email_from': FROM,
        'state'     : 'outgoing',
    }]])
    call('ir.cron', 'method_direct_trigger', [[3]])
    print(f"✓ [{env_name}] mail.mail id={new_id} → {to_email}")
    return new_id


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', choices=['testing','production','both'], default='both')
    parser.add_argument('--to', default=TO_TEST)
    args = parser.parse_args()

    envs = ['testing','production'] if args.env == 'both' else [args.env]
    for env in envs:
        send_test(env, args.to)
