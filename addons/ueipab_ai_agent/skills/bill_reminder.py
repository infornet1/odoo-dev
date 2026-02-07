import logging

from . import register_skill, get_ve_greeting, get_first_name

_logger = logging.getLogger(__name__)


@register_skill('bill_reminder')
class BillReminderSkill:
    """Skill: send friendly reminders about upcoming invoice due dates."""

    def _get_agent_config(self, conversation):
        """Get agent display name and institution from system parameters."""
        icp = conversation.env['ir.config_parameter'].sudo()
        return {
            'agent_name': icp.get_param('ai_agent.agent_display_name', 'Asistente Virtual'),
            'institution': icp.get_param('ai_agent.institution_display_name', 'UEIPAB'),
        }

    def get_context(self, conversation):
        """Get context from the source account.move record."""
        ctx = {
            'partner_name': conversation.partner_id.name or '',
            'first_name': get_first_name(conversation.partner_id.name),
            'invoice_name': '',
            'amount_total': 0.0,
            'currency': 'USD',
            'date_due': '',
        }
        ctx.update(self._get_agent_config(conversation))
        if conversation.source_model == 'account.move' and conversation.source_id:
            invoice = conversation.env['account.move'].browse(conversation.source_id)
            if invoice.exists():
                ctx['invoice_name'] = invoice.name or ''
                ctx['amount_total'] = invoice.amount_total or 0.0
                ctx['currency'] = invoice.currency_id.name if invoice.currency_id else 'USD'
                ctx['date_due'] = str(invoice.invoice_date_due or '')
                ctx['amount_residual'] = invoice.amount_residual or 0.0
        return ctx

    def get_system_prompt(self, conversation, context):
        """Return Claude system prompt for bill reminders."""
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        first_name = context.get('first_name', 'Cliente')
        return (
            f"Eres {agent_name}, asistente de cobranzas de {institution}, ubicado en Venezuela. "
            "Tu tarea es recordar amablemente a un cliente sobre una factura próxima a vencer o vencida.\n\n"
            "CONTEXTO:\n"
            f"- Nombre del contacto: {first_name}\n"
            f"- Factura: {context.get('invoice_name', '')}\n"
            f"- Monto total: {context.get('currency', 'USD')} {context.get('amount_total', 0):.2f}\n"
            f"- Monto pendiente: {context.get('currency', 'USD')} {context.get('amount_residual', 0):.2f}\n"
            f"- Fecha de vencimiento: {context.get('date_due', 'no especificada')}\n\n"
            "INSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano, de forma cercana y cálida.\n"
            f"- Dirígete al cliente por su nombre ({first_name}).\n"
            "- Sé amable, profesional y respetuoso. No uses emojis.\n"
            "- Recuerda al cliente el monto pendiente y la fecha de vencimiento.\n"
            "- Si el cliente confirma que ya realizó el pago, responde: RESOLVED:PAID\n"
            "- Si el cliente solicita más tiempo, responde: RESOLVED:EXTENSION\n"
            "- Si el cliente tiene dudas, respóndelas amablemente.\n"
            "- No amenaces ni presiones. Es un recordatorio cordial.\n"
            "- NO prometas acciones que no puedes ejecutar (como enviar correos, llamar, "
            "o realizar gestiones internas). Solo puedes conversar por WhatsApp.\n"
            "- Máximo 3 intercambios antes de cerrar la conversación.\n"
            "- IMPORTANTE: Los marcadores RESOLVED: son internos, no los incluyas en el "
            "mensaje visible al cliente. Envía primero un mensaje de despedida o confirmación "
            "y luego el marcador RESOLVED: en la misma respuesta.\n"
        )

    def get_greeting(self, conversation, context):
        """Return the initial WhatsApp greeting message."""
        first_name = context.get('first_name', 'estimado/a')
        amount = context.get('amount_residual', context.get('amount_total', 0))
        currency = context.get('currency', 'USD')
        date_due = context.get('date_due', '')
        invoice = context.get('invoice_name', '')
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        saludo = get_ve_greeting()

        msg = (
            f"{saludo}, {first_name}! Le escribe {agent_name} desde {institution} "
            f"para recordarle que tiene una factura pendiente"
        )
        if invoice:
            msg += f" ({invoice})"
        msg += f" por {currency} {amount:.2f}"
        if date_due:
            msg += f", con vencimiento el {date_due}"
        msg += ". Quedamos atentos ante cualquier consulta."
        return msg

    def get_reminder_message(self, conversation, context, reminder_count):
        """Return a WhatsApp reminder message for bill reminders."""
        first_name = context.get('first_name', 'estimado/a')
        amount = context.get('amount_residual', context.get('amount_total', 0))
        currency = context.get('currency', 'USD')
        invoice = context.get('invoice_name', '')
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        saludo = get_ve_greeting()

        ref = f" ({invoice})" if invoice else ""

        if reminder_count == 0:
            return (
                f"{saludo}, {first_name}. Le escribimos nuevamente desde {institution} "
                f"para recordarle sobre su factura pendiente{ref} por "
                f"{currency} {amount:.2f}. Quedamos atentos a cualquier consulta."
            )
        return (
            f"{saludo}, {first_name}. Le contactamos por ultima vez desde {institution} "
            f"respecto a su factura pendiente{ref} por {currency} {amount:.2f}. "
            f"Si no recibimos respuesta, cerraremos esta solicitud. "
            f"Quedamos a su disposicion."
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
        if 'RESOLVED:PAID' in ai_response:
            return {
                'resolve': True,
                'farewell_message': self._extract_farewell(ai_response),
                'summary': 'Cliente confirma que ya realizo el pago.',
                'resolution_data': {'action': 'paid'},
            }
        if 'RESOLVED:EXTENSION' in ai_response:
            return {
                'resolve': True,
                'farewell_message': self._extract_farewell(ai_response),
                'summary': 'Cliente solicita extension de plazo.',
                'resolution_data': {'action': 'extension'},
            }
        return {'message': ai_response}

    def on_resolve(self, conversation, resolution_data):
        """Log resolution on the invoice chatter."""
        if conversation.source_model != 'account.move' or not conversation.source_id:
            return

        invoice = conversation.env['account.move'].browse(conversation.source_id)
        if not invoice.exists():
            return

        action = resolution_data.get('action', '')
        if action == 'paid':
            invoice.message_post(body=(
                "Recordatorio WhatsApp AI: Cliente confirma que ya realizo el pago. "
                "Verificar recepcion del pago."
            ))
        elif action == 'extension':
            invoice.message_post(body=(
                "Recordatorio WhatsApp AI: Cliente solicita extension de plazo de pago."
            ))
        _logger.info("Bill reminder resolved for invoice %s: %s", invoice.name, action)
