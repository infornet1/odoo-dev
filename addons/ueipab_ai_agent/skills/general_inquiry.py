import logging
import re

from . import register_skill, get_ve_greeting

_logger = logging.getLogger(__name__)

# Shared institutional knowledge block (same content as bounce_resolution)
_INSTITUTIONAL_KNOWLEDGE = (
    "CONOCIMIENTO INSTITUCIONAL:\n"
    "- Institución: Instituto Privado Andrés Bello (Colegio Andrés Bello), El Tigre, Municipio Simón Rodríguez, Venezuela. RIF: J-08008617-1\n"
    "- Año escolar: 2025-2026\n"
    "- Enfoque pedagógico: metodología STEAM, Proyectos de Aprendizaje (PA), competencias digitales e inteligencia artificial\n"
    "- Aliados educativos: Akademia, Dawere, Kurios, Universidad Europea del Atlántico, Move on Academy, Edugogo\n"
    "- Mensualidad: $197,38 | Pronto puntual: $162,39 (10 primeros dias de cada mes)\n"
    "- Extras anuales: Seguro escolar $10, Guía de inglés $15, Olimpiadas recreativas $10, Enciclopedia digital bachillerato $36\n"
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

        return (
            f"Eres {agent_name}, asistente virtual del {institution}, ubicada en Venezuela.\n\n"
            + _INSTITUTIONAL_KNOWLEDGE
            + "CONTEXTO:\n"
            "- Esta persona escribió directamente a este número de WhatsApp sin que nosotros la hayamos contactado.\n"
            + contact_ctx
            + "\nINSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano, cálida y profesionalmente.\n"
            "- Salúdala y preséntate brevemente como asistente del colegio.\n"
            "- Entiende su consulta. Responde preguntas generales con el conocimiento institucional que tienes "
            "(medios de pago, mensualidades, fechas, información general del colegio).\n"
            "- Si la consulta es sobre facturación, deuda, saldo, estado de cuenta, ajuste de cobro o pagos "
            "pendientes: infórmale que la canalizarás con el equipo de Pagos y Facturación "
            "(pagos@ueipab.edu.ve) que la atenderá a la brevedad. Usa ACTION:HANDOFF con ruta 'billing'.\n"
            "- Si la consulta requiere acceso a otros datos personales (documentos, trámites, asuntos del "
            "alumno, quejas, etc.): infórmale que la conectarás con el equipo de soporte "
            "(soporte@ueipab.edu.ve). Usa ACTION:HANDOFF con ruta 'support'.\n"
            "- Cuando tengas el nombre de la persona Y el tema de su consulta, o luego de máximo 2 intercambios, "
            "finaliza con: ACTION:HANDOFF:nombre|resumen_de_la_consulta|ruta\n"
            "  El nombre va primero, luego el resumen, luego la ruta (billing o support). Sin saltos de línea.\n"
            "  Ejemplo facturación: ACTION:HANDOFF:María García|Consulta deuda mensualidad octubre|billing\n"
            "  Ejemplo soporte:     ACTION:HANDOFF:Carlos López|Solicitud de constancia de estudios|support\n"
            "- Si no logras obtener el nombre, usa 'Desconocido' en el marcador.\n"
            "- No uses emojis. No reveles que eres un sistema automático a menos que pregunten directamente.\n"
            "- IMPORTANTE: ACTION:HANDOFF es un comando interno. El cliente NO lo ve. Siempre inclúyelo "
            "al final de la respuesta cuando aplique.\n"
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

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for ACTION:HANDOFF marker."""
        handoff_match = re.search(
            r'ACTION:HANDOFF:([^|\n]+)\|([^|\n]+)(?:\|(\w+))?$',
            ai_response,
            re.MULTILINE,
        )
        if handoff_match:
            captured_name = handoff_match.group(1).strip()
            captured_summary = handoff_match.group(2).strip()
            route = (handoff_match.group(3) or 'support').strip().lower()
            if route not in ('billing', 'support'):
                route = 'support'
            visible_text = self._extract_visible_text(ai_response)
            team = 'Pagos y Facturación' if route == 'billing' else 'Soporte'
            return {
                'resolve': True,
                'farewell_message': visible_text or ai_response,
                'summary': f'Transferido a {team}: {captured_name} — {captured_summary}',
                'resolution_data': {
                    'action': 'handoff',
                    'captured_name': captured_name,
                    'summary': captured_summary,
                    'route': route,
                },
            }

        return {'message': ai_response}

    def on_resolve(self, conversation, resolution_data):
        """Send handoff email to soporte@ueipab.edu.ve with full transcript."""
        if resolution_data.get('action') != 'handoff':
            return

        captured_name = resolution_data.get('captured_name', 'Desconocido')
        summary = resolution_data.get('summary', 'Sin descripción')
        route = resolution_data.get('route', 'support')
        phone = conversation.phone
        to_email = 'pagos@ueipab.edu.ve' if route == 'billing' else 'soporte@ueipab.edu.ve'
        team_name = 'equipo de Pagos y Facturación' if route == 'billing' else 'equipo de Soporte'

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
