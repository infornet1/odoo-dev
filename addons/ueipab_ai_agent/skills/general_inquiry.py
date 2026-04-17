import logging
import re

from . import register_skill, get_ve_greeting

_logger = logging.getLogger(__name__)

# Flyers available to send via WhatsApp.
# key → (filename, short description for Claude's reference)
_FLYERS = {
    'inscripcion':          ('inscripcion.png',          'Inscripciones abiertas año escolar 2026-2027 — $197.38/año, 17.72% descuento hasta el 1 de mayo'),
    'pronto_pago':          ('pronto_pago.png',          'Pronto pago: mensualidad congelada a $162.39 si pagas en los primeros 10 días del mes'),
    'tarjeta_credito':      ('tarjeta_credito.png',      'Aceptamos tarjetas de crédito nacionales e internacionales sin comisiones adicionales'),
    'english':              ('english.png',              'MOA School: Cursos de Inglés After School, grupos pequeños, $38/mes'),
    'robotica':             ('robotica.png',             'Clases de Robótica con Kurios — 2 clases/semana, $52/mes, inscripción gratis'),
    'dibujo':               ('dibujo.png',               'Curso de Dibujo y Pintura — 3 meses, 4h semanales, $38/mes'),
    'bachillerato_virtual': ('bachillerato_virtual.png', 'Bachillerato Virtual 100% online — inscríbete ya'),
}

def _get_flyer_url(base_url, filename):
    """Build the public URL for a flyer file."""
    return f"{base_url.rstrip('/')}/{filename}"

# Shared institutional knowledge block (same content as bounce_resolution)
_INSTITUTIONAL_KNOWLEDGE = (
    "CONOCIMIENTO INSTITUCIONAL:\n"
    "- Institución: Instituto Privado Andrés Bello (Colegio Andrés Bello), El Tigre, Municipio Simón Rodríguez, Venezuela. RIF: J-08008617-1\n"
    "- Año escolar: 2026-2027\n"
    "- Enfoque pedagógico: metodología STEAM, Proyectos de Aprendizaje (PA), competencias digitales e inteligencia artificial\n"
    "- Aliados educativos: Akademia, Dawere, Kurios, Universidad Europea del Atlántico, Move on Academy, Edugogo\n"
    "- Inscripción: $197,38\n"
    "- Mensualidad: $197,38 | Pronto puntual: $162,39 (10 primeros dias de cada mes)\n"
    "- Costos adicionales:\n"
    "    Seguro escolar: $15\n"
    "    Enciclopedia de Inglés: $30\n"
    "    Olimpiadas Recreativas de Lengua y Matemáticas: $10\n"
    "    Enciclopedia digital bachillerato: $36\n"
    "    Competencia Kurios: $10 (solo si el alumno es seleccionado)\n"
    "    Competencia MOA inglés: $25 (solo si el alumno es seleccionado)\n"
    "    Encuentros Regionales/Nacionales (Olimpiadas Recreativas, Robótica, Inglés): traslados y logística a cargo de los padres\n"
    "POLÍTICA PDVSA / PETROPIAR 2026-2027:\n"
    "- Período anterior (2025-2026): existía un beneficio especial — la institución emitía la factura con un crédito anticipado del 35% y esperaba que el empleador reembolsara al empleado.\n"
    "- Período 2026-2027: este beneficio queda DESCONTINUADO por la situación socioeconómica del país y la situación financiera de la institución.\n"
    "- Para nuevos prospectos PDVSA/Petropiar: pago 100% por adelantado a tasa BCV, igual que cualquier otra familia. El reembolso con el empleador es responsabilidad exclusiva del representante.\n"
    "- Para familias ya inscritas (2025-2026) que expresen dificultad económica ante este cambio: responder con mucha empatía, invitarlas a conversar con el Director antes de tomar cualquier decisión, y alertar urgentemente a pagos@ueipab.edu.ve.\n"
    "MEDIOS DE PAGO (a nombre de Instituto Privado Andrés Bello, C.A.):\n"
    "- Transferencia Banco Plaza (Cta Cte): 0138-0032-47-0320013870\n"
    "- Transferencia BanPlus (Cta Cte): 0174-0127-12-1274138559\n"
    "- Transferencia Mercantil (Cta Cte): 0105-0069-93-1069377856\n"
    "- Transferencia Banco de Venezuela (Cta Cte): 0102-0445-34-0007673100\n"
    "- Transferencia Bancamiga (Cta Cte): 0172-0702-44-7024976891\n"
    "- Pago móvil: 04141906296 | Banco 0102 (Venezuela) | RIF J080086171\n"
    "- Zelle: pagos@ueipab.edu.ve\n"
    "- Tarjeta crédito/débito: Portal Mercantil en https://www.portaldepagosmercantil.com/\n"
    "- Binance: ID 383 867 49\n"
    "- Efectivo USD: Banco Mercantil cuenta dólares 5069006770\n"
    "- Tras realizar el pago, notificar a: pagos@ueipab.edu.ve\n"
    "CANALES DE ATENCIÓN HUMANA:\n"
    "- Facturación / deuda / pagos / estado de cuenta / ajustes de cobro: pagos@ueipab.edu.ve\n"
    "- Todo lo demás (soporte general, documentos, asuntos del alumno, quejas, etc.): soporte@ueipab.edu.ve\n\n"
)


@register_skill('general_inquiry')
class GeneralInquirySkill:
    """Skill: Handle unsolicited inbound WhatsApp messages.

    Triggered when an unknown phone messages the Glenda number with no active
    conversation. Glenda greets warmly, captures the person's name and inquiry,
    answers simple questions using institutional knowledge, and hands off to the
    human support team via email to soporte@ueipab.edu.ve for anything personal
    or complex.
    """

    def _get_agent_config(self, conversation):
        icp = conversation.env['ir.config_parameter'].sudo()
        return {
            'agent_name': icp.get_param('ai_agent.agent_display_name', 'Glenda'),
            'institution': icp.get_param('ai_agent.institution_display_name', 'Instituto Privado Andrés Bello'),
        }

    def get_context(self, conversation):
        cfg = self._get_agent_config(conversation)
        partner = conversation.partner_id
        partner_found = bool(
            partner and not partner.name.startswith('Consulta WhatsApp')
        )
        return {
            'partner_name': partner.name if partner_found else '',
            'partner_found_in_odoo': partner_found,
            **cfg,
        }

    def get_system_prompt(self, conversation, context):
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'Instituto Privado Andrés Bello')
        partner_name = context.get('partner_name', '')
        partner_found = context.get('partner_found_in_odoo', False)

        contact_ctx = (
            f"- Este contacto está registrado en el sistema como: {partner_name}. Puedes dirigirte a él/ella por su nombre.\n"
            if partner_found
            else "- Este contacto NO está registrado en el sistema. Si no dice su nombre, pregúntaselo de forma natural.\n"
        )

        flyer_list = "\n".join(
            f"  - {key}: {desc}" for key, (_, desc) in _FLYERS.items()
        )

        return (
            f"Eres {agent_name}, asistente virtual del {institution}, ubicada en Venezuela.\n\n"
            + _INSTITUTIONAL_KNOWLEDGE
            + "CONTEXTO:\n"
            "- Esta persona escribió directamente a este número de WhatsApp sin que nosotros la hayamos contactado.\n"
            + contact_ctx
            + "\nFLYERS DISPONIBLES (imágenes informativas que puedes enviar):\n"
            + flyer_list + "\n"
            + "\nINSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano, cálida y profesionalmente.\n"
            "- Salúdala y preséntate brevemente como asistente del colegio.\n"
            "- Entiende su consulta. Responde preguntas generales con el conocimiento institucional que tienes "
            "(medios de pago, mensualidades, fechas, información general del colegio).\n"
            "- Si la persona pregunta por inscripciones, mensualidad, cursos extracurriculares, métodos de pago "
            "u otros temas cubiertos por un flyer disponible, añade ACTION:SEND_FLYER:clave al final de tu "
            "respuesta (usa exactamente la clave de la lista de flyers). Solo un flyer por respuesta.\n"
            "  Ejemplo: ACTION:SEND_FLYER:inscripcion\n"
            "- Si la consulta es sobre facturación, deuda, saldo, estado de cuenta, ajuste de cobro o pagos "
            "pendientes: infórmale que la canalizarás con el equipo de Pagos y Facturación "
            "(pagos@ueipab.edu.ve) que la atenderá a la brevedad. Usa ACTION:HANDOFF con ruta 'billing'.\n"
            "- Si la consulta requiere acceso a otros datos personales (documentos, trámites, asuntos del "
            "alumno, quejas, etc.): infórmale que la conectarás con el equipo de soporte "
            "(soporte@ueipab.edu.ve). Usa ACTION:HANDOFF con ruta 'support'.\n"
            "MANEJO ESPECIAL PDVSA / PETROPIAR:\n"
            "- Si alguien se identifica como empleado(a) de PDVSA o Petropiar y es un NUEVO prospecto "
            "(no inscrito en 2025-2026): infórmale con claridad pero cordialidad que el beneficio del "
            "crédito anticipado del 35% que existía en períodos anteriores ha sido descontinuado para "
            "2026-2027. El pago ahora es 100% por adelantado a tasa BCV, igual que cualquier otra "
            "familia. El reembolso con su empleador es responsabilidad exclusiva del representante. "
            "Usa ACTION:HANDOFF con ruta 'billing'.\n"
            "- Si es una familia YA INSCRITA (período 2025-2026) que expresa dificultad económica, "
            "preocupación o amenaza de no poder continuar ante este cambio (ej: 'no voy a poder pagar', "
            "'no tengo para pagar', 'tengo dos o más alumnos', 'no puedo sin ese beneficio'): "
            "respóndele con MUCHA empatía y calma. Hazle saber que entiendes su situación y que el "
            "colegio valora su familia. Invítala a conversar directamente con el Director para evaluar "
            "su caso particular antes de tomar cualquier decisión. No presiones ni repitas la política "
            "fríamente. Usa ACTION:HANDOFF con ruta 'pdvsa_retention'.\n"
            "- Cuando tengas el nombre de la persona Y el tema de su consulta, o luego de máximo 2 intercambios, "
            "finaliza con: ACTION:HANDOFF:nombre|resumen_de_la_consulta|ruta\n"
            "  El nombre va primero, luego el resumen, luego la ruta (billing o support). Sin saltos de línea.\n"
            "  Ejemplo facturación: ACTION:HANDOFF:María García|Consulta deuda mensualidad octubre|billing\n"
            "  Ejemplo soporte:     ACTION:HANDOFF:Carlos López|Solicitud de constancia de estudios|support\n"
            "- Si no logras obtener el nombre, usa 'Desconocido' en el marcador.\n"
            "- No uses emojis. No reveles que eres un sistema automático a menos que pregunten directamente.\n"
            "- IMPORTANTE: ACTION:SEND_FLYER y ACTION:HANDOFF son comandos internos. El cliente NO los ve. "
            "Inclúyelos siempre al final de la respuesta cuando apliquen.\n"
        )

    def get_greeting(self, conversation, context):
        """Fallback greeting if conversation is started manually via action_start."""
        saludo = get_ve_greeting()
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'Instituto Privado Andrés Bello')
        return (
            f"{saludo}! Le saluda {agent_name}, asistente virtual del {institution}. "
            "Con gusto le atiendo. ¿En qué le puedo ayudar?"
        )

    def _extract_visible_text(self, ai_response):
        """Strip ACTION markers from the response before sending to customer."""
        text = re.sub(r'ACTION:\w+[^\n]*', '', ai_response)
        return text.strip()

    def _get_base_url(self, conversation):
        return conversation.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.flyer_base_url', 'https://dev.ueipab.edu.ve/flyers'
        )

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for ACTION:SEND_FLYER and ACTION:HANDOFF markers."""
        # Check for flyer send request
        flyer_match = re.search(r'ACTION:SEND_FLYER:(\w+)', ai_response, re.MULTILINE)
        flyer_key = flyer_match.group(1).strip() if flyer_match else None
        if flyer_key and flyer_key not in _FLYERS:
            _logger.warning("general_inquiry: unknown flyer key '%s', ignoring", flyer_key)
            flyer_key = None

        # Check for handoff
        handoff_match = re.search(
            r'ACTION:HANDOFF:([^|\n]+)\|([^|\n]+)(?:\|(\w+))?$',
            ai_response,
            re.MULTILINE,
        )
        if handoff_match:
            captured_name = handoff_match.group(1).strip()
            captured_summary = handoff_match.group(2).strip()
            route = (handoff_match.group(3) or 'support').strip().lower()
            if route not in ('billing', 'support', 'pdvsa_retention'):
                route = 'support'
            visible_text = self._extract_visible_text(ai_response)
            team = 'Pagos y Facturación' if route == 'billing' else 'Soporte'
            result = {
                'resolve': True,
                'farewell_message': visible_text or ai_response,
                'summary': f'Transferido a {team}: {captured_name} — {captured_summary}',
                'resolution_data': {
                    'action': 'handoff',
                    'captured_name': captured_name,
                    'summary': captured_summary,
                    'route': route,
                    'flyer_key': flyer_key,
                },
            }
            return result

        visible_text = self._extract_visible_text(ai_response)
        result = {'message': visible_text or ai_response}
        if flyer_key:
            result['flyer_key'] = flyer_key
        return result

    def send_flyer(self, conversation, flyer_key):
        """Send a flyer image via WhatsApp for the given key."""
        if flyer_key not in _FLYERS:
            return
        filename, description = _FLYERS[flyer_key]
        base_url = self._get_base_url(conversation)
        url = _get_flyer_url(base_url, filename)
        dry_run = conversation.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.dry_run', 'True').lower() == 'true'
        if dry_run:
            _logger.info("DRY_RUN: would send flyer '%s' to %s: %s", flyer_key, conversation.phone, url)
            return
        wa_service = conversation.env['ai.agent.whatsapp.service']
        try:
            wa_service.send_media(conversation.phone, url)
            _logger.info("Flyer '%s' sent to %s", flyer_key, conversation.phone)
        except Exception as e:
            _logger.error("Failed to send flyer '%s' to %s: %s", flyer_key, conversation.phone, e)

    def on_resolve(self, conversation, resolution_data):
        """Send handoff email to soporte@ueipab.edu.ve with full transcript."""
        if resolution_data.get('action') != 'handoff':
            return

        captured_name = resolution_data.get('captured_name', 'Desconocido')
        summary = resolution_data.get('summary', 'Sin descripción')
        route = resolution_data.get('route', 'support')
        phone = conversation.phone
        if route == 'pdvsa_retention':
            to_email = 'pagos@ueipab.edu.ve'
            team_name = 'equipo de Pagos y Facturación'
        elif route == 'billing':
            to_email = 'pagos@ueipab.edu.ve'
            team_name = 'equipo de Pagos y Facturación'
        else:
            to_email = 'soporte@ueipab.edu.ve'
            team_name = 'equipo de Soporte'

        partner = conversation.partner_id
        partner_found = bool(partner and not partner.name.startswith('Consulta WhatsApp'))
        partner_info = f"Sí — {partner.name}" if partner_found else "No encontrado en el sistema"

        # Build transcript
        transcript_rows = []
        for msg in conversation.agent_message_ids.sorted('create_date'):
            role = 'Cliente' if msg.direction == 'inbound' else 'Glenda'
            body = (msg.body or '').strip()
            if body:
                transcript_rows.append(
                    f'<tr style="vertical-align:top;">'
                    f'<td style="padding:3px 10px 3px 0;font-weight:bold;white-space:nowrap;">{role}:</td>'
                    f'<td style="padding:3px 0;">{body}</td></tr>'
                )
        transcript_html = (
            '<table style="border-collapse:collapse;font-size:13px;">'
            + ''.join(transcript_rows)
            + '</table>'
            if transcript_rows else '<i>(sin mensajes)</i>'
        )

        if route == 'pdvsa_retention':
            subject = f"[URGENTE - Glenda] Familia PDVSA — Riesgo de no renovación — {captured_name}"
            body_html = f"""
<p style="color:#c0392b;font-weight:bold;">⚠️ ATENCIÓN URGENTE — Riesgo de no renovación de matrícula</p>
<p>Hola {team_name},</p>
<p>Una familia <strong>ya inscrita en el período 2025-2026</strong>, identificada como empleada de <strong>PDVSA / Petropiar</strong>,
ha expresado a través de WhatsApp dificultades económicas ante la descontinuación del beneficio del 35% de crédito anticipado.</p>
<p>Puede haber riesgo de que esta familia <strong>no continúe en el período 2026-2027</strong>.
Se les invitó a conversar con el Director para evaluar su situación particular.</p>
<table style="border-collapse:collapse;margin:10px 0;">
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Teléfono:</td><td>{phone}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Nombre indicado:</td><td>{captured_name}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Contacto en Odoo:</td><td>{partner_info}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Resumen:</td><td>{summary}</td></tr>
</table>
<p><strong>Acción requerida:</strong> Contactar a esta familia a la brevedad y coordinar con el Director una reunión para evaluar su caso.</p>
<p><b>Transcripción de la conversación:</b></p>
<div style="background:#f5f5f5;padding:12px;border-radius:4px;">
{transcript_html}
</div>
<p>Saludos,<br/><b>Glenda — Asistente Virtual</b><br/>Instituto Privado Andrés Bello</p>
"""
        else:
            subject = f"[Glenda] Consulta entrante — WhatsApp {phone}"
            body_html = f"""
<p>Hola {team_name},</p>
<p>Un cliente se comunicó a través de WhatsApp al número de Glenda y necesita atención personalizada.</p>
<table style="border-collapse:collapse;margin:10px 0;">
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Teléfono:</td><td>{phone}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Nombre indicado:</td><td>{captured_name}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Contacto en Odoo:</td><td>{partner_info}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Resumen:</td><td>{summary}</td></tr>
</table>
<p><b>Transcripción de la conversación:</b></p>
<div style="background:#f5f5f5;padding:12px;border-radius:4px;">
{transcript_html}
</div>
<p style="margin-top:14px;">Por favor, comuníquese con el cliente para atender su solicitud.</p>
<p>Saludos,<br/><b>Glenda — Asistente Virtual</b><br/>Instituto Privado Andrés Bello</p>
"""
        conversation._send_escalation_email({
            'to': to_email,
            'subject': subject,
            'body_html': body_html,
        })
