import logging

from . import register_skill, get_ve_greeting, get_first_name

_logger = logging.getLogger(__name__)


@register_skill('billing_support')
class BillingSupportSkill:
    """Skill: inform customers of balance and answer billing questions."""

    def _get_agent_config(self, conversation):
        """Get agent display name and institution from system parameters."""
        icp = conversation.env['ir.config_parameter'].sudo()
        return {
            'agent_name': icp.get_param('ai_agent.agent_display_name', 'Asistente Virtual'),
            'institution': icp.get_param('ai_agent.institution_display_name', 'UEIPAB'),
        }

    def get_context(self, conversation):
        """Get context from the source res.partner record."""
        ctx = {
            'partner_name': conversation.partner_id.name or '',
            'first_name': get_first_name(conversation.partner_id.name),
            'total_due': 0.0,
            'currency': 'USD',
            'invoice_count': 0,
        }
        ctx.update(self._get_agent_config(conversation))
        partner = conversation.partner_id
        if partner:
            # Get outstanding invoices
            invoices = conversation.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('state', '=', 'posted'),
            ])
            ctx['total_due'] = sum(invoices.mapped('amount_residual'))
            ctx['invoice_count'] = len(invoices)
            if invoices:
                ctx['currency'] = invoices[0].currency_id.name if invoices[0].currency_id else 'USD'
        return ctx

    def get_system_prompt(self, conversation, context):
        """Return Claude system prompt for billing support."""
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        first_name = context.get('first_name', 'Cliente')
        return (
            f"Eres {agent_name}, asistente de facturación de {institution}, ubicado en Venezuela. "
            "Tu tarea es informar al cliente sobre su saldo pendiente y responder preguntas "
            "de facturación.\n\n"
            "CONTEXTO:\n"
            f"- Nombre del contacto: {first_name}\n"
            f"- Saldo pendiente total: {context.get('currency', 'USD')} {context.get('total_due', 0):.2f}\n"
            f"- Facturas pendientes: {context.get('invoice_count', 0)}\n\n"
            "INSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano, de forma cercana y cálida.\n"
            f"- Dirígete al cliente por su nombre ({first_name}).\n"
            "- Sé amable, profesional y servicial. No uses emojis.\n"
            "- Informa al cliente sobre su saldo pendiente.\n"
            "- Si pregunta por métodos de pago, indícale que puede comunicarse con administración "
            "al correo administracion@ueipab.edu.ve.\n"
            "- Si el cliente confirma que no tiene más preguntas, responde: RESOLVED:DONE\n"
            "- Si el cliente reporta un error en su facturación, responde: RESOLVED:DISPUTE\n"
            "- NO prometas acciones que no puedes ejecutar (como enviar correos, llamar, "
            "o realizar gestiones internas). Solo puedes conversar por WhatsApp.\n"
            "- Máximo 4 intercambios antes de cerrar la conversación.\n"
            "- IMPORTANTE: Los marcadores RESOLVED: son internos, no los incluyas en el "
            "mensaje visible al cliente. Envía primero un mensaje de despedida o confirmación "
            "y luego el marcador RESOLVED: en la misma respuesta.\n"
        )

    def get_greeting(self, conversation, context):
        """Return the initial WhatsApp greeting message."""
        first_name = context.get('first_name', 'estimado/a')
        total_due = context.get('total_due', 0)
        currency = context.get('currency', 'USD')
        count = context.get('invoice_count', 0)
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        saludo = get_ve_greeting()

        if total_due > 0:
            msg = (
                f"{saludo}, {first_name}! Le escribe {agent_name} desde {institution} "
                f"para informarle sobre su estado de cuenta. Actualmente tiene "
                f"{count} factura(s) pendiente(s) por un total de {currency} {total_due:.2f}. "
                f"Puede consultarnos cualquier duda sobre su facturación."
            )
        else:
            msg = (
                f"{saludo}, {first_name}! Le escribe {agent_name} desde {institution}. "
                f"Su estado de cuenta se encuentra al día. "
                f"Si tiene alguna consulta sobre facturación, estamos a su disposición."
            )
        return msg

    def get_reminder_message(self, conversation, context, reminder_count):
        """Return a WhatsApp reminder message for billing support."""
        first_name = context.get('first_name', 'estimado/a')
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        saludo = get_ve_greeting()

        if reminder_count == 0:
            return (
                f"{saludo}, {first_name}. Le escribimos nuevamente desde {institution}. "
                f"Quedamos pendientes por si tiene alguna consulta adicional sobre su "
                f"facturacion. Estamos a su disposicion."
            )
        return (
            f"{saludo}, {first_name}. Le contactamos por ultima vez desde {institution} "
            f"respecto a su consulta de facturacion. Si no recibimos respuesta, "
            f"cerraremos esta solicitud. Quedamos a su disposicion."
        )

    def _extract_farewell(self, ai_response):
        """Extract farewell text before RESOLVED: marker."""
        import re
        match = re.search(r'RESOLVED:\S+', ai_response)
        if match:
            farewell = ai_response[:match.start()].strip()
            return farewell if farewell else None
        return None

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for resolution signals."""
        if 'RESOLVED:DONE' in ai_response:
            return {
                'resolve': True,
                'farewell_message': self._extract_farewell(ai_response),
                'summary': 'Consulta de facturacion atendida satisfactoriamente.',
                'resolution_data': {'action': 'done'},
            }
        if 'RESOLVED:DISPUTE' in ai_response:
            return {
                'resolve': True,
                'farewell_message': self._extract_farewell(ai_response),
                'summary': 'Cliente reporta discrepancia en facturacion. Requiere revision manual.',
                'resolution_data': {'action': 'dispute'},
            }
        return {'message': ai_response}

    def on_resolve(self, conversation, resolution_data):
        """Log resolution on the partner chatter."""
        partner = conversation.partner_id
        if not partner:
            return

        action = resolution_data.get('action', '')
        if action == 'done':
            partner.message_post(body=(
                "Consulta de facturacion via WhatsApp AI atendida satisfactoriamente."
            ))
        elif action == 'dispute':
            partner.message_post(body=(
                "Cliente reporta discrepancia en facturacion via WhatsApp AI. "
                "Requiere revision manual del equipo de administracion."
            ))
        _logger.info("Billing support resolved for partner %s: %s", partner.name, action)
