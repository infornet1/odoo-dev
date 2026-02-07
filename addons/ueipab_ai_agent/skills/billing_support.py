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
            "Eres un asistente de facturacion de UEIPAB (Universidad Experimental de los Llanos Centrales). "
            "Tu tarea es informar al cliente sobre su saldo pendiente y responder preguntas de facturacion.\n\n"
            "CONTEXTO:\n"
            f"- Nombre del contacto: {context.get('partner_name', 'Cliente')}\n"
            f"- Saldo pendiente total: {context.get('currency', 'USD')} {context.get('total_due', 0):.2f}\n"
            f"- Facturas pendientes: {context.get('invoice_count', 0)}\n\n"
            "INSTRUCCIONES:\n"
            "- Comunicate siempre en espanol.\n"
            "- Se amable, profesional y servicial.\n"
            "- Informa al cliente su saldo pendiente.\n"
            "- Si pregunta por metodos de pago, indica que puede comunicarse con administracion.\n"
            "- Si el cliente confirma que no tiene mas preguntas, responde: RESOLVED:DONE\n"
            "- Si el cliente reporta un error en su facturacion, responde: RESOLVED:DISPUTE\n"
            "- Maximo 4 mensajes antes de cerrar la conversacion.\n"
        )

    def get_greeting(self, conversation, context):
        """Return the initial WhatsApp greeting message."""
        name = context.get('partner_name', 'estimado/a')
        total_due = context.get('total_due', 0)
        currency = context.get('currency', 'USD')
        count = context.get('invoice_count', 0)

        if total_due > 0:
            msg = (
                f"Buenos dias, {name}. Le contactamos de UEIPAB para informarle "
                f"sobre su estado de cuenta. Actualmente tiene {count} factura(s) pendiente(s) "
                f"por un total de {currency} {total_due:.2f}. "
                f"Puede consultarnos cualquier duda sobre su facturacion."
            )
        else:
            msg = (
                f"Buenos dias, {name}. Le contactamos de UEIPAB. "
                f"Su estado de cuenta se encuentra al dia. "
                f"Si tiene alguna consulta sobre facturacion, estamos a su disposicion."
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
