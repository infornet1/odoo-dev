import logging

from . import register_skill

_logger = logging.getLogger(__name__)


@register_skill('billing_support')
class BillingSupportSkill:
    """Skill: inform customers of balance and answer billing questions."""

    def get_context(self, conversation):
        """Get context from the source res.partner record."""
        ctx = {
            'partner_name': conversation.partner_id.name or '',
            'total_due': 0.0,
            'currency': 'USD',
            'invoice_count': 0,
        }
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
        return (
            "Eres un asistente virtual de facturación de UEIPAB (Universidad Experimental de los "
            "Llanos Centrales Rómulo Gallegos), ubicada en Venezuela. "
            "Tu tarea es informar al cliente sobre su saldo pendiente y responder preguntas "
            "de facturación.\n\n"
            "CONTEXTO:\n"
            f"- Nombre del contacto: {context.get('partner_name', 'Cliente')}\n"
            f"- Saldo pendiente total: {context.get('currency', 'USD')} {context.get('total_due', 0):.2f}\n"
            f"- Facturas pendientes: {context.get('invoice_count', 0)}\n\n"
            "INSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano. Usa el trato de 'usted' (formal pero cálido).\n"
            "- Sé amable, profesional y servicial. No uses emojis.\n"
            "- Informa al cliente sobre su saldo pendiente.\n"
            "- Si pregunta por métodos de pago, indícale que puede comunicarse con administración "
            "al correo administracion@ueipab.edu.ve.\n"
            "- Si el cliente confirma que no tiene más preguntas, responde: RESOLVED:DONE\n"
            "- Si el cliente reporta un error en su facturación, responde: RESOLVED:DISPUTE\n"
            "- Máximo 4 intercambios antes de cerrar la conversación.\n"
            "- IMPORTANTE: Los marcadores RESOLVED: son internos, no los incluyas en el "
            "mensaje visible al cliente.\n"
        )

    def get_greeting(self, conversation, context):
        """Return the initial WhatsApp greeting message."""
        name = context.get('partner_name', 'estimado/a')
        total_due = context.get('total_due', 0)
        currency = context.get('currency', 'USD')
        count = context.get('invoice_count', 0)

        if total_due > 0:
            msg = (
                f"Buen día, {name}. Le saludamos de parte de UEIPAB para informarle "
                f"sobre su estado de cuenta. Actualmente tiene {count} factura(s) pendiente(s) "
                f"por un total de {currency} {total_due:.2f}. "
                f"Puede consultarnos cualquier duda sobre su facturación."
            )
        else:
            msg = (
                f"Buen día, {name}. Le saludamos de parte de UEIPAB. "
                f"Su estado de cuenta se encuentra al día. "
                f"Si tiene alguna consulta sobre facturación, estamos a su disposición."
            )
        return msg

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for resolution signals."""
        if 'RESOLVED:DONE' in ai_response:
            return {
                'resolve': True,
                'summary': 'Consulta de facturacion atendida satisfactoriamente.',
                'resolution_data': {'action': 'done'},
            }
        if 'RESOLVED:DISPUTE' in ai_response:
            return {
                'resolve': True,
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
