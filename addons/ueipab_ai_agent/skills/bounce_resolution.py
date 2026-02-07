import logging
import re

from . import register_skill

_logger = logging.getLogger(__name__)


@register_skill('bounce_resolution')
class BounceResolutionSkill:
    """Skill: resolve bounced emails by contacting customers via WhatsApp."""

    def get_context(self, conversation):
        """Get context from the source mail.bounce.log record."""
        ctx = {
            'bounced_email': '',
            'bounce_reason': '',
            'partner_name': conversation.partner_id.name or '',
        }
        if conversation.source_model == 'mail.bounce.log' and conversation.source_id:
            bounce_log = conversation.env['mail.bounce.log'].browse(conversation.source_id)
            if bounce_log.exists():
                ctx['bounced_email'] = bounce_log.bounced_email or ''
                ctx['bounce_reason'] = dict(
                    bounce_log._fields['bounce_reason'].selection
                ).get(bounce_log.bounce_reason, bounce_log.bounce_reason or '')
                ctx['bounce_log_id'] = bounce_log.id
        return ctx

    def get_system_prompt(self, conversation, context):
        """Return Claude system prompt for bounce resolution."""
        return (
            "Eres un asistente virtual de UEIPAB (Universidad Experimental de los Llanos Centrales "
            "Rómulo Gallegos), ubicada en Venezuela. "
            "Tu tarea es contactar amablemente a un representante o cliente cuyo correo electrónico "
            "está presentando problemas de entrega.\n\n"
            "CONTEXTO:\n"
            f"- Nombre del contacto: {context.get('partner_name', 'Cliente')}\n"
            f"- Correo con problemas: {context.get('bounced_email', 'desconocido')}\n"
            f"- Razón del rebote: {context.get('bounce_reason', 'desconocida')}\n\n"
            "INSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano. Usa el trato de 'usted' (formal pero cálido).\n"
            "- Sé amable, profesional y conciso. No uses emojis.\n"
            "- Explica brevemente que su correo está presentando problemas para recibir "
            "comunicaciones de UEIPAB.\n"
            "- Pregunta si nos puede facilitar un correo electrónico alternativo.\n"
            "- Si el cliente proporciona un email nuevo, confírmalo repitiéndolo y responde "
            "EXACTAMENTE con el formato: RESOLVED:nuevo@email.com\n"
            "- Si el cliente dice que su correo actual funciona bien, responde: RESOLVED:RESTORE\n"
            "- Si el cliente no desea proporcionar otro correo, responde: RESOLVED:DECLINED\n"
            "- No reveles detalles técnicos del rebote a menos que el cliente pregunte.\n"
            "- Máximo 2-3 intercambios antes de cerrar la conversación.\n"
            "- IMPORTANTE: Los marcadores RESOLVED: son internos, no los incluyas en el "
            "mensaje visible al cliente. Envía primero un mensaje de despedida o confirmación "
            "y luego el marcador RESOLVED: en la misma respuesta.\n"
        )

    def get_greeting(self, conversation, context):
        """Return the initial WhatsApp greeting message."""
        name = context.get('partner_name', 'estimado/a')
        email = context.get('bounced_email', 'su correo')
        return (
            f"Buen día, {name}. Le saludamos de parte de UEIPAB. "
            f"Nos comunicamos con usted porque hemos detectado que su correo electrónico "
            f"({email}) está presentando inconvenientes para recibir nuestras comunicaciones. "
            f"¿Nos podría facilitar un correo alternativo para mantenernos en contacto?"
        )

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for resolution signals."""
        # Check for resolution patterns
        resolve_match = re.search(r'RESOLVED:(\S+)', ai_response)
        if resolve_match:
            resolution_value = resolve_match.group(1)

            if resolution_value == 'RESTORE':
                return {
                    'resolve': True,
                    'summary': 'Cliente indica que su email actual funciona correctamente.',
                    'resolution_data': {'action': 'restore'},
                }
            elif resolution_value == 'DECLINED':
                return {
                    'resolve': True,
                    'summary': 'Cliente no desea proporcionar email alternativo.',
                    'resolution_data': {'action': 'declined'},
                }
            else:
                # Should be a new email
                new_email = resolution_value.strip()
                return {
                    'resolve': True,
                    'summary': f'Cliente proporciono nuevo email: {new_email}',
                    'resolution_data': {'action': 'new_email', 'email': new_email},
                }

        # No resolution yet — forward the AI response as-is
        return {'message': ai_response}

    def on_resolve(self, conversation, resolution_data):
        """Apply resolution to the source mail.bounce.log record."""
        if conversation.source_model != 'mail.bounce.log' or not conversation.source_id:
            return

        bounce_log = conversation.env['mail.bounce.log'].browse(conversation.source_id)
        if not bounce_log.exists():
            _logger.warning("Bounce log %d not found for conversation %d",
                            conversation.source_id, conversation.id)
            return

        action = resolution_data.get('action')

        if action == 'new_email':
            new_email = resolution_data.get('email', '')
            if new_email:
                bounce_log.write({'new_email': new_email})
                bounce_log.action_apply_new_email()
                _logger.info("Bounce log %d: applied new email %s via AI agent",
                             bounce_log.id, new_email)

        elif action == 'restore':
            bounce_log.action_restore_original()
            _logger.info("Bounce log %d: restored original email via AI agent", bounce_log.id)

        elif action == 'declined':
            bounce_log.write({'state': 'contacted'})
            bounce_log.message_post(body=(
                "Cliente contactado via WhatsApp AI. "
                "No desea proporcionar email alternativo."
            ))
            _logger.info("Bounce log %d: customer declined via AI agent", bounce_log.id)

        # Link conversation to bounce log
        bounce_log.write({
            'ai_conversation_id': conversation.id,
            'whatsapp_contacted': True,
            'whatsapp_contact_date': conversation.create_date,
        })
