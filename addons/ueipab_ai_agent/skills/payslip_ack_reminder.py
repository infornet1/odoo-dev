"""Payslip Acknowledgment Reminder skill for Glenda AI Agent.

Contacts employees via WhatsApp with their payslip acknowledgment URL.
Auto-resolves when the payslip is_acknowledged flag flips to True (checked by cron).
"""
import logging

from . import register_skill, get_ve_greeting, get_first_name

_logger = logging.getLogger(__name__)


@register_skill('payslip_ack_reminder')
class PayslipAckReminderSkill:

    def _get_agent_config(self, conversation):
        ICP = conversation.env['ir.config_parameter'].sudo()
        return {
            'agent_name': ICP.get_param('ai_agent.agent_display_name', 'Glenda'),
            'institution': ICP.get_param('ai_agent.institution_display_name', 'UEIPAB'),
        }

    def _get_payslip(self, conversation):
        if conversation.source_model != 'hr.payslip' or not conversation.source_id:
            return None
        return conversation.env['hr.payslip'].browse(conversation.source_id)

    def get_context(self, conversation):
        config = self._get_agent_config(conversation)
        payslip = self._get_payslip(conversation)

        ctx = {
            'agent_name': config['agent_name'],
            'institution': config['institution'],
            'employee_name': '',
            'first_name': '',
            'payslip_number': '',
            'period': '',
            'net_veb': '',
            'ack_url': '',
            'is_liquid_ve_v2': False,
        }

        if not payslip or not payslip.exists():
            return ctx

        emp = payslip.employee_id
        ctx['employee_name'] = emp.name
        ctx['first_name'] = get_first_name(emp.name)
        ctx['payslip_number'] = payslip.number or payslip.name or ''

        if payslip.date_from and payslip.date_to:
            ctx['period'] = '{} - {}'.format(
                payslip.date_from.strftime('%d/%m/%Y'),
                payslip.date_to.strftime('%d/%m/%Y'),
            )

        rate = getattr(payslip, 'exchange_rate_used', None) or 1.0
        if hasattr(payslip, 'get_net_amount'):
            net = payslip.get_net_amount()
        else:
            net = payslip.net_wage or 0.0
        if net and rate:
            ctx['net_veb'] = '{:,.2f} Bs.'.format(net * rate)

        if hasattr(payslip, '_get_acknowledgment_url'):
            ctx['ack_url'] = payslip._get_acknowledgment_url()

        if payslip.struct_id and payslip.struct_id.code == 'LIQUID_VE_V2':
            ctx['is_liquid_ve_v2'] = True

        return ctx

    def get_greeting(self, conversation, context):
        greeting = get_ve_greeting()
        first_name = context.get('first_name', 'estimado/a')
        institution = context.get('institution', 'UEIPAB')
        payslip_number = context.get('payslip_number', '')
        period = context.get('period', '')
        net_veb = context.get('net_veb', '')
        ack_url = context.get('ack_url', '')
        is_liquid = context.get('is_liquid_ve_v2', False)

        doc_type = 'adelanto de prestaciones sociales' if is_liquid else 'comprobante de pago'

        lines = [
            f"{greeting}, {first_name}. Te saluda Glenda de Recursos Humanos de {institution}.",
            "",
        ]

        if payslip_number:
            period_str = f" correspondiente al período {period}" if period else ""
            amount_str = f" por *{net_veb}*" if net_veb else ""
            lines.append(
                f"Tu {doc_type} *{payslip_number}*{period_str}{amount_str} "
                f"está pendiente de conformidad digital."
            )
        else:
            lines.append(f"Tu {doc_type} está pendiente de conformidad digital.")

        lines.append("")

        if ack_url:
            lines.append("Por favor ingresa al siguiente enlace para confirmar:")
            lines.append(ack_url)
        else:
            lines.append("Por favor comunícate con Recursos Humanos para mayor información.")

        lines.append("")
        lines.append("Si tienes alguna dificultad con el enlace, responde a este mensaje y te ayudamos.")

        return "\n".join(lines)

    def get_system_prompt(self, conversation, context):
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'UEIPAB')
        first_name = context.get('first_name', 'el empleado')
        ack_url = context.get('ack_url', '')
        payslip_number = context.get('payslip_number', '')
        period = context.get('period', '')
        net_veb = context.get('net_veb', '')

        return (
            f"Eres {agent_name}, asistente virtual de Recursos Humanos de {institution}.\n\n"
            f"Tu única tarea es ayudar a {first_name} a completar la conformidad digital "
            f"de su comprobante de pago {payslip_number} ({period}, {net_veb}).\n\n"
            f"Enlace de conformidad: {ack_url}\n\n"
            "REGLAS:\n"
            "1. Si el empleado tiene problemas con el enlace, indica: "
            "'Por favor comunícate con Recursos Humanos a recursoshumanos@ueipab.edu.ve'\n"
            "2. Si el empleado confirma que ya confirmó, responde: "
            "'¡Perfecto! Gracias por confirmar, ya está registrado. Que tengas un excelente día.'\n"
            "3. Si pregunta sobre monto o período, proporciona la información del contexto.\n"
            "4. Comunícate en español venezolano, trato de tú, amable y conciso.\n"
            "5. Máximo 3-4 mensajes. No discutas otros temas."
        )

    def get_reminder_message(self, conversation, context, reminder_count):
        first_name = context.get('first_name', 'estimado/a')
        ack_url = context.get('ack_url', '')
        is_liquid = context.get('is_liquid_ve_v2', False)
        doc_type = 'adelanto de prestaciones sociales' if is_liquid else 'comprobante de pago'

        lines = [
            f"Hola {first_name}, te recordamos que tu {doc_type} sigue pendiente de conformidad digital.",
            "",
        ]
        if ack_url:
            lines.append("Enlace de confirmación:")
            lines.append(ack_url)
        lines.append("")
        lines.append("Si tienes algún inconveniente, responde a este mensaje.")
        return "\n".join(lines)

    def process_ai_response(self, conversation, response_text):
        return []
