import logging

from . import register_skill

_logger = logging.getLogger(__name__)


@register_skill('bill_reminder')
class BillReminderSkill:
    """Skill: send friendly reminders about upcoming invoice due dates."""

    def get_context(self, conversation):
        """Get context from the source account.move record."""
        ctx = {
            'partner_name': conversation.partner_id.name or '',
            'invoice_name': '',
            'amount_total': 0.0,
            'currency': 'USD',
            'date_due': '',
        }
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
        return (
            "Eres un asistente virtual de cobranzas de UEIPAB (Universidad Experimental de los "
            "Llanos Centrales Rómulo Gallegos), ubicada en Venezuela. "
            "Tu tarea es recordar amablemente a un cliente sobre una factura próxima a vencer o vencida.\n\n"
            "CONTEXTO:\n"
            f"- Nombre del contacto: {context.get('partner_name', 'Cliente')}\n"
            f"- Factura: {context.get('invoice_name', '')}\n"
            f"- Monto total: {context.get('currency', 'USD')} {context.get('amount_total', 0):.2f}\n"
            f"- Monto pendiente: {context.get('currency', 'USD')} {context.get('amount_residual', 0):.2f}\n"
            f"- Fecha de vencimiento: {context.get('date_due', 'no especificada')}\n\n"
            "INSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano. Usa el trato de 'usted' (formal pero cálido).\n"
            "- Sé amable, profesional y respetuoso. No uses emojis.\n"
            "- Recuerda al cliente el monto pendiente y la fecha de vencimiento.\n"
            "- Si el cliente confirma que ya realizó el pago, responde: RESOLVED:PAID\n"
            "- Si el cliente solicita más tiempo, responde: RESOLVED:EXTENSION\n"
            "- Si el cliente tiene dudas, respóndelas amablemente.\n"
            "- No amenaces ni presiones. Es un recordatorio cordial.\n"
            "- Máximo 3 intercambios antes de cerrar la conversación.\n"
            "- IMPORTANTE: Los marcadores RESOLVED: son internos, no los incluyas en el "
            "mensaje visible al cliente.\n"
        )

    def get_greeting(self, conversation, context):
        """Return the initial WhatsApp greeting message."""
        name = context.get('partner_name', 'estimado/a')
        amount = context.get('amount_residual', context.get('amount_total', 0))
        currency = context.get('currency', 'USD')
        date_due = context.get('date_due', '')
        invoice = context.get('invoice_name', '')

        msg = (
            f"Buen día, {name}. Le saludamos de parte de UEIPAB para recordarle "
            f"que tiene una factura pendiente"
        )
        if invoice:
            msg += f" ({invoice})"
        msg += f" por {currency} {amount:.2f}"
        if date_due:
            msg += f", con vencimiento el {date_due}"
        msg += ". Quedamos atentos ante cualquier consulta."
        return msg

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for resolution signals."""
        if 'RESOLVED:PAID' in ai_response:
            return {
                'resolve': True,
                'summary': 'Cliente confirma que ya realizo el pago.',
                'resolution_data': {'action': 'paid'},
            }
        if 'RESOLVED:EXTENSION' in ai_response:
            return {
                'resolve': True,
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
