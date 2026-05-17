"""
Send staff announcement email: OdooBot is now powered by Glenda.
Run (test):  docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http < scripts/send_glenda_odoobot_announcement.py
Run (live):  Set DRY_RUN=False, TEST_EMAIL='' — sends to all 52 internal users.
"""

import logging
_logger = logging.getLogger(__name__)

DRY_RUN = True   # Set to False to actually send
TEST_EMAIL = ''  # 'gustavo.perdomo@ueipab.edu.ve' to test one address

SUBJECT = "Glenda ya está en Odoo — tu asistente virtual ahora también responde en el chat interno"


BODY_HTML = (
    '<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;background:#f0f4fa;padding:24px;">'

    # Header with logo
    '<div style="background:#1a2c5b;border-radius:10px 10px 0 0;padding:28px 36px 24px;text-align:center;">'
    '<img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo"'
    ' alt="Colegio Andrés Bello"'
    ' style="height:80px;width:80px;border-radius:50%;object-fit:cover;border:3px solid #2471a3;margin:0 auto 14px;display:block;" />'
    '<h1 style="color:#ffffff;font-size:20px;margin:0 0 6px;">¡Glenda ya está en Odoo!</h1>'
    '<p style="color:#a8c4e0;font-size:13px;margin:0;">Tu asistente virtual ahora responde en el chat interno del sistema</p>'
    '</div>'

    # Body
    '<div style="background:#ffffff;padding:32px 36px;border-left:4px solid #2471a3;border-right:4px solid #2471a3;">'
    '<p style="color:#1a2c5b;font-size:15px;line-height:1.6;">Hola equipo,</p>'
    '<p style="color:#333;font-size:15px;line-height:1.6;">'
    'A partir de hoy, <strong style="color:#1a2c5b;">Glenda</strong> — la misma asistente de inteligencia artificial '
    'que atiende a nuestras/os trabajadoras/es y próximamente a las/os representantes por WhatsApp — está disponible directamente dentro de '
    '<strong>Odoo Discuss</strong>, conectada al <strong>OdooBot</strong>.'
    '</p>'
    '<p style="color:#333;font-size:15px;line-height:1.6;">'
    'Puedes consultarle tarifas, políticas, inscripciones y cualquier información institucional '
    'sin salir del sistema — desde tu computadora, en segundos.'
    '</p>'

    # Steps
    '<div style="background:#f0f4fa;border-radius:8px;padding:20px 24px;margin:24px 0;">'
    '<h2 style="color:#1a2c5b;font-size:15px;margin:0 0 16px;">¿Cómo usarlo? Solo 3 pasos</h2>'
    '<table style="width:100%;border-collapse:collapse;">'
    '<tr><td style="width:36px;vertical-align:top;padding:6px 12px 6px 0;">'
    '<div style="background:#1a2c5b;color:#fff;border-radius:50%;width:28px;height:28px;text-align:center;line-height:28px;font-size:13px;font-weight:bold;">1</div>'
    '</td><td style="vertical-align:top;padding:6px 0;color:#333;font-size:14px;">'
    'Abre <strong>Odoo</strong> y haz clic en el ícono de <strong>Discuss</strong> (burbuja de chat) en el menú superior izquierdo.'
    '</td></tr>'
    '<tr><td style="width:36px;vertical-align:top;padding:6px 12px 6px 0;">'
    '<div style="background:#1a2c5b;color:#fff;border-radius:50%;width:28px;height:28px;text-align:center;line-height:28px;font-size:13px;font-weight:bold;">2</div>'
    '</td><td style="vertical-align:top;padding:6px 0;color:#333;font-size:14px;">'
    'En la barra lateral izquierda, bajo <em>Mensajes directos</em>, busca <strong>OdooBot</strong> y haz clic.'
    '</td></tr>'
    '<tr><td style="width:36px;vertical-align:top;padding:6px 12px 6px 0;">'
    '<div style="background:#1a2c5b;color:#fff;border-radius:50%;width:28px;height:28px;text-align:center;line-height:28px;font-size:13px;font-weight:bold;">3</div>'
    '</td><td style="vertical-align:top;padding:6px 0;color:#333;font-size:14px;">'
    '<strong>¡Escríbele tu pregunta!</strong> Glenda responderá en segundos.'
    '</td></tr>'
    '</table>'
    '</div>'

    # Sidebar mockup
    '<h2 style="color:#1a2c5b;font-size:15px;margin:24px 0 12px;">¿Dónde encontrar OdooBot?</h2>'
    '<div style="background:#22264a;border-radius:8px;padding:16px 20px;">'
    '<div style="color:#7a9cc4;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Mensajes directos</div>'
    '<div style="padding:6px 10px;border-radius:4px;color:#9ab3cc;margin-bottom:4px;">'
    '<span style="display:inline-block;width:8px;height:8px;background:#44cc88;border-radius:50%;margin-right:8px;"></span>Alejandra Lopez</div>'
    '<div style="padding:6px 10px;border-radius:4px;color:#9ab3cc;margin-bottom:6px;">'
    '<span style="display:inline-block;width:8px;height:8px;background:#888;border-radius:50%;margin-right:8px;"></span>Norka La Rosa</div>'
    '<div style="padding:7px 10px;border-radius:6px;background:#2471a3;color:#ffffff;margin-bottom:6px;font-weight:bold;border:2px solid #5ba8d4;">'
    '<span style="margin-right:8px;">🤖</span>OdooBot'
    '<span style="font-size:11px;font-weight:normal;margin-left:8px;background:#1a5580;padding:2px 8px;border-radius:10px;">← Glenda está aquí</span>'
    '</div>'
    '<div style="padding:6px 10px;border-radius:4px;color:#9ab3cc;">'
    '<span style="display:inline-block;width:8px;height:8px;background:#44cc88;border-radius:50%;margin-right:8px;"></span>Gustavo Perdomo</div>'
    '</div>'

    # Chat example
    '<h2 style="color:#1a2c5b;font-size:15px;margin:28px 0 14px;">Ejemplo de conversación</h2>'
    '<div style="background:#f0f4fa;border-radius:8px;padding:20px 24px;">'
    '<p style="color:#1a2c5b;font-size:11px;font-weight:bold;margin:0 0 14px;text-transform:uppercase;letter-spacing:0.5px;">Chat con OdooBot</p>'
    # User 1
    '<div style="text-align:right;margin-bottom:12px;">'
    '<span style="display:inline-block;background:#2471a3;color:#fff;border-radius:16px 16px 4px 16px;padding:9px 14px;font-size:13px;max-width:78%;text-align:left;">'
    '¿El colegio tiene Bachillerato Internacional?'
    '</span></div>'
    # Glenda 1
    '<div style="margin-bottom:14px;display:flex;align-items:flex-start;gap:8px;">'
    '<div style="background:#1a2c5b;border-radius:50%;min-width:28px;width:28px;height:28px;text-align:center;line-height:28px;font-size:14px;">🤖</div>'
    '<span style="display:inline-block;background:#ffffff;color:#333;border:1px solid #d0dce8;border-radius:4px 16px 16px 16px;padding:9px 14px;font-size:13px;max-width:82%;text-align:left;">'
    '¡Hola! En el Colegio Andrés Bello ofrecemos Bachillerato en dos modalidades:<br><br>'
    '<strong>Presencial</strong> — Media General y Bachillerato, bajo la dirección de la Prof. Norka La Rosa.<br><br>'
    '<strong>Virtual 100% en línea</strong> — a través de nuestra alianza con Dawere, ideal para quienes necesitan flexibilidad.<br><br>'
    'Para inscripciones 2026-2027 hay una <strong>promoción hasta el 31 de julio</strong> a $187,51. ¿Te gustaría más información?'
    '</span></div>'
    # User 2
    '<div style="text-align:right;margin-bottom:12px;">'
    '<span style="display:inline-block;background:#2471a3;color:#fff;border-radius:16px 16px 4px 16px;padding:9px 14px;font-size:13px;max-width:78%;text-align:left;">'
    '¿Y cuáles son los medios de pago?'
    '</span></div>'
    # Glenda 2
    '<div style="display:flex;align-items:flex-start;gap:8px;">'
    '<div style="background:#1a2c5b;border-radius:50%;min-width:28px;width:28px;height:28px;text-align:center;line-height:28px;font-size:14px;">🤖</div>'
    '<span style="display:inline-block;background:#ffffff;color:#333;border:1px solid #d0dce8;border-radius:4px 16px 16px 16px;padding:9px 14px;font-size:13px;max-width:82%;text-align:left;">'
    'Aceptamos: transferencias (Banco Venezuela, Mercantil, BanPlus, Plaza, Bancamiga), Zelle, Binance, Cashea, y tarjeta crédito/débito via Portal Mercantil. '
    'Tras pagar, notifica a <strong>pagos@ueipab.edu.ve</strong>.'
    '</span></div>'
    '</div>'  # end chat

    # What she knows table
    '<h2 style="color:#1a2c5b;font-size:15px;margin:28px 0 14px;">¿Qué más puede responder?</h2>'
    '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
    '<tr style="background:#f0f4fa;"><td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#2471a3;font-weight:bold;">💰 Tarifas 2026-2027</td>'
    '<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#444;">Mensualidades, inscripción promo, pronto pago, descuentos hermanos</td></tr>'
    '<tr><td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#2471a3;font-weight:bold;">📋 Costos anuales</td>'
    '<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#444;">Seguro $30,58 · Guía inglés $25 · Olimpiadas $10 · Enciclopedia $36</td></tr>'
    '<tr style="background:#f0f4fa;"><td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#2471a3;font-weight:bold;">👨&#8203;‍👩‍👧 Cotizaciones multi-alumno</td>'
    '<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#444;">Descuentos 5% / 8% / 11% · total primer mes incluido</td></tr>'
    '<tr><td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#2471a3;font-weight:bold;">🏦 Medios de pago</td>'
    '<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#444;">Transferencias, Zelle, Binance, Cashea, Portal Mercantil</td></tr>'
    '<tr style="background:#f0f4fa;"><td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#2471a3;font-weight:bold;">📜 Políticas</td>'
    '<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#444;">PDVSA, mora, requisitos inscripción, tasa BCV</td></tr>'
    '<tr><td style="padding:9px 12px;color:#2471a3;font-weight:bold;">🎓 Programas académicos</td>'
    '<td style="padding:9px 12px;color:#444;">Bachillerato presencial y virtual, alianzas Dawere, Akademia, extracurriculares</td></tr>'
    '</table>'

    # Calibration section
    '<div style="background:#f0f4fa;border-radius:8px;padding:24px;margin-top:28px;">'
    '<p style="color:#1a2c5b;font-size:15px;font-weight:700;margin:0 0 6px;">Gracias al Programa de Calibración</p>'
    '<p style="color:#555;font-size:13px;margin:0 0 18px;line-height:1.5;">'
    'Quienes participaron en el programa de pruebas internas enviaron <strong>26 sugerencias</strong>. '
    'La mayoría ya están implementadas en Glenda. Gracias por su retroalimentación — cada sugerencia cuenta.'
    '</p>'

    # Done table
    '<p style="color:#1a2c5b;font-size:13px;font-weight:700;margin:0 0 10px;">✅ Mejoras ya implementadas</p>'
    '<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:18px;">'
    '<tr style="background:#1a2c5b;color:#fff;">'
    '<td style="padding:7px 10px;font-weight:600;border-radius:6px 0 0 0;">Sugerencia</td>'
    '<td style="padding:7px 10px;font-weight:600;">Quién la hizo</td>'
    '<td style="padding:7px 10px;font-weight:600;border-radius:0 6px 0 0;">Estado</td>'
    '</tr>'
    '<tr style="background:#fff;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Dejar de enviar mensajes repetidos al despedirse</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">8 personas</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#27ae60;font-weight:600;">Listo</td>'
    '</tr>'
    '<tr style="background:#f8fafd;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Mencionar Cashea cuando hay dificultades de pago</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Luisa A., Jessica B.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#27ae60;font-weight:600;">Listo</td>'
    '</tr>'
    '<tr style="background:#fff;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Transcribir mensajes de voz</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Maria F., Gustavo P.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#27ae60;font-weight:600;">Listo</td>'
    '</tr>'
    '<tr style="background:#f8fafd;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Información sobre Bachillerato (menciones, IB)</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Audrey G.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#27ae60;font-weight:600;">Listo</td>'
    '</tr>'
    '<tr style="background:#fff;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Cómo inscribirse / solicitar cupo (enlaces Akdemia)</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Audrey G.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#27ae60;font-weight:600;">Listo</td>'
    '</tr>'
    '<tr style="background:#f8fafd;">'
    '<td style="padding:7px 10px;color:#333;">Política de mora e incumplimiento de pago (proceso completo)</td>'
    '<td style="padding:7px 10px;color:#555;">Luisa A. (×3)</td>'
    '<td style="padding:7px 10px;color:#27ae60;font-weight:600;">Listo</td>'
    '</tr>'
    '</table>'

    # Pending table
    '<p style="color:#1a2c5b;font-size:13px;font-weight:700;margin:0 0 10px;">🔄 Sugerencias en camino</p>'
    '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
    '<tr style="background:#2471a3;color:#fff;">'
    '<td style="padding:7px 10px;font-weight:600;border-radius:6px 0 0 0;">Sugerencia</td>'
    '<td style="padding:7px 10px;font-weight:600;">Quién la hizo</td>'
    '<td style="padding:7px 10px;font-weight:600;border-radius:0 6px 0 0;">Estado</td>'
    '</tr>'
    '<tr style="background:#fff;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Sistema de calificación de atención (👍/👎 al finalizar)</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Nidya L.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#e67e22;font-weight:600;">En desarrollo</td>'
    '</tr>'
    '<tr style="background:#f8fafd;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Tabla comparativa de cursos extracurriculares</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Jessica B.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#e67e22;font-weight:600;">Planificado</td>'
    '</tr>'
    '<tr style="background:#fff;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Resumen automático de circulares en 3 puntos clave</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Jessica B.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#e67e22;font-weight:600;">Planificado</td>'
    '</tr>'
    '<tr style="background:#f8fafd;">'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#333;">Mejora en tiempos de respuesta percibidos (latencia)</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#555;">Maria F.</td>'
    '<td style="padding:7px 10px;border-bottom:1px solid #e0e8f0;color:#e67e22;font-weight:600;">En evaluación</td>'
    '</tr>'
    '<tr style="background:#fff;">'
    '<td style="padding:7px 10px;color:#333;">Prueba diagnóstica para alumnos procedentes del extranjero</td>'
    '<td style="padding:7px 10px;color:#555;">Luisa A.</td>'
    '<td style="padding:7px 10px;color:#e67e22;font-weight:600;">En consideración</td>'
    '</tr>'
    '</table>'
    '</div>'

    # Note
    '<div style="border-left:3px solid #2471a3;padding:12px 16px;background:#f8fafd;border-radius:0 6px 6px 0;margin-top:24px;">'
    '<p style="margin:0;font-size:13px;color:#555;line-height:1.5;">'
    '<strong style="color:#1a2c5b;">Nota:</strong> Esta integración es exclusiva para el equipo interno con acceso a Odoo. '
    'Glenda responde con la misma información actualizada que usa en WhatsApp. '
    '¿Dudas técnicas? <a href="mailto:soporte@ueipab.edu.ve" style="color:#2471a3;">soporte@ueipab.edu.ve</a>'
    '</p></div>'
    '</div>'  # end body card

    # Footer
    '<div style="background:#1a2c5b;border-radius:0 0 10px 10px;padding:18px 36px;text-align:center;">'
    '<p style="color:#a8c4e0;font-size:12px;margin:0 0 4px;">Instituto Privado Andrés Bello — Sistema de Gestión Interno</p>'
    '<p style="color:#6a90b5;font-size:11px;margin:0;">© 2026 Colegio Andrés Bello, El Tigre, Anzoátegui, Venezuela</p>'
    '</div>'
    '</div>'
)

CC_ADDRESS   = 'recursoshumanos@ueipab.edu.ve'
REPLY_TO     = 'recursoshumanos@ueipab.edu.ve'

RECIPIENT_EMAILS = [
    'alejandra.lopez@ueipab.edu.ve',
    'andres.morales@ueipab.edu.ve',
    'arcides.arzola@ueipab.edu.ve',
    'audrey.garcia@ueipab.edu.ve',
    'camila.rossato@ueipab.edu.ve',
    'david.hernandez@ueipab.edu.ve',
    'dixia.bellorin@ueipab.edu.ve',
    'daniel.bongianni@ueipab.edu.ve',
    'elis.mejias@ueipab.edu.ve',
    'emilio.isea@ueipab.edu.ve',
    'flormar.hernandez@ueipab.edu.ve',
    'gabriel.espana@ueipab.edu.ve',
    'gabriela.uray@ueipab.edu.ve',
    'gladys.brito@ueipab.edu.ve',
    'giovanni.vezza@ueipab.edu.ve',
    'heydi.ron@ueipab.edu.ve',
    'ismary.arcila@ueipab.edu.ve',
    'jesus.dicesare@ueipab.edu.ve',
    'josefina.rodriguez@ueipab.edu.ve',
    'jose.hernandez@ueipab.edu.ve',
    'jessica.bolivar@ueipab.edu.ve',
    'laray@ueipab.edu.ve',
    'luis.rodriguez@ueipab.edu.ve',
    'luisa.abreu@ueipab.edu.ve',
    'lorena.reyes@ueipab.edu.ve',
    'magyelis.mata@ueipab.edu.ve',
    'mairelsy.motta@ueipab.edu.ve',
    'maria.nieto@ueipab.edu.ve',
    'mariela.prado@ueipab.edu.ve',
    'mirian.hernandez@ueipab.edu.ve',
    'maria.figuera@ueipab.edu.ve',
    'nelci.brito@ueipab.edu.ve',
    'nidya.lira@ueipab.edu.ve',
    'norka.larosa@ueipab.edu.ve',
    'pablo.navarro@ueipab.edu.ve',
    'ramon.bello@ueipab.edu.ve',
    'robert.quijada@ueipab.edu.ve',
    'rafael.perez@ueipab.edu.ve',
    'sergio.maneiro@ueipab.edu.ve',
    'teresa.marin@ueipab.edu.ve',
    'virginia.verde@ueipab.edu.ve',
    'yaritza.bruces@ueipab.edu.ve',
    'yudelys.brito@ueipab.edu.ve',
    'zareth.farias@ueipab.edu.ve',
]

label = '[DRY RUN] ' if DRY_RUN else ''
send_list = [TEST_EMAIL] if TEST_EMAIL else RECIPIENT_EMAILS
print(f"\n{label}Sending to {len(send_list)} recipient(s)  |  CC: {CC_ADDRESS}  |  Reply-To: {REPLY_TO}\n")
for e in send_list:
    print(f"  {e}")

if not DRY_RUN:
    sent = 0
    for email in send_list:
        mail = env['mail.mail'].create({
            'subject': SUBJECT,
            'body_html': BODY_HTML,
            'email_from': 'Glenda — Colegio Andrés Bello <soporte@ueipab.edu.ve>',
            'email_to': email,
            'email_cc': CC_ADDRESS,
            'reply_to': REPLY_TO,
            'auto_delete': True,
        })
        mail.send()
        sent += 1
        print(f"  ✓ Queued → {email}")
    env.cr.commit()
    print(f"\nDone. {sent} email(s) queued.")
else:
    print(f"\n[DRY RUN] No emails sent. Set DRY_RUN = False to send.")
