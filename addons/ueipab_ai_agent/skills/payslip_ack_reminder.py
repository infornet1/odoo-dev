"""Payslip Acknowledgment Reminder skill for Glenda AI Agent.

Contacts employees via WhatsApp with their payslip acknowledgment URL.
Auto-resolves when the payslip is_acknowledged flag flips to True (checked by cron).
"""
import logging
import re

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
            f"{greeting}, {first_name}. Te saluda Glenda, la agente de asistencia virtual de Recursos Humanos de {institution}.",
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

        lines.append(
            "Por favor ingresa a tu correo electrónico institucional "
            "para que revises tu recibo de adelanto."
        )
        lines.append("")
        lines.append("Si tienes alguna dificultad, responde a este mensaje y te ayudamos.")

        return "\n".join(lines)

    def get_system_prompt(self, conversation, context):
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'UEIPAB')
        first_name = context.get('first_name', 'el empleado')
        payslip_number = context.get('payslip_number', '')
        period = context.get('period', '')
        net_veb = context.get('net_veb', '')

        return (
            f"Eres {agent_name}, la agente de asistencia virtual de Recursos Humanos de {institution}. "
            f"Eres un sistema automatizado, NO un empleado real.\n\n"
            f"Tu única tarea es recordarle a {first_name} que revise su correo electrónico "
            f"institucional para completar la conformidad digital de su comprobante de pago "
            f"{payslip_number} ({period}, {net_veb}).\n\n"
            "REGLAS:\n"
            "1. NUNCA compartas enlaces directos de confirmación por este canal.\n"
            "2. Siempre dirige al empleado a su correo institucional.\n"
            "3. Si el empleado tiene CUALQUIER dificultad, problema, queja o consulta que no puedas "
            "resolver con las reglas anteriores, emite en una línea separada: "
            "ACTION:ESCALATE:descripcion breve del problema\n"
            "   Luego despídete indicando que un agente humano de RRHH le contactará.\n"
            "4. Si el empleado confirma que ya completó la conformidad, responde: "
            "'¡Perfecto! Gracias por confirmar. Que tengas un excelente día.'\n"
            "5. Si pregunta sobre monto o período, proporciona la información del contexto.\n"
            "6. Comunícate en español venezolano, trato de tú, amable y conciso.\n"
            "7. Máximo 3-4 mensajes. No discutas otros temas.\n"
            "8. Si presentas la acción ACTION:ESCALATE, escríbela SOLA en su propia línea, "
            "sin markdown, sin asteriscos."
        )

    def get_reminder_message(self, conversation, context, reminder_count):
        first_name = context.get('first_name', 'estimado/a')
        ack_url = context.get('ack_url', '')
        is_liquid = context.get('is_liquid_ve_v2', False)
        doc_type = 'adelanto de prestaciones sociales' if is_liquid else 'comprobante de pago'

        lines = [
            f"Hola {first_name}, te recordamos que tu {doc_type} sigue pendiente de conformidad digital.",
            "",
            "Por favor revisa tu correo electrónico institucional para completar la confirmación.",
            "",
            "Si tienes algún inconveniente, responde a este mensaje.",
        ]
        return "\n".join(lines)

    def process_ai_response(self, conversation, response_text, context):
        escalate_match = re.search(r'ACTION:ESCALATE:(.+)$', response_text, re.MULTILINE)
        if escalate_match:
            escalate_desc = escalate_match.group(1).strip()
            emp_name = context.get('employee_name', 'Empleado')
            institution = context.get('institution', 'UEIPAB')
            payslip_number = context.get('payslip_number', '')
            period = context.get('period', '')

            odoo_base = conversation.env['ir.config_parameter'].sudo().get_param(
                'web.base.url', 'http://localhost:8069')
            conv_url = (
                f"{odoo_base}/web#id={conversation.id}"
                f"&model=ai.agent.conversation&view_type=form"
            )

            visible_text = re.sub(r'ACTION:ESCALATE:.+$', '', response_text, flags=re.MULTILINE).strip()

            messages_html = ''
            for msg in conversation.agent_message_ids.sorted('id'):
                role = 'Empleado' if msg.role == 'user' else 'Glenda'
                messages_html += f'<p><strong>{role}:</strong> {msg.body or ""}</p>'

            body_html = (
                f'<h3>[{institution}] Glenda — Conformidad de Recibo</h3>'
                f'<p><strong>Empleado:</strong> {emp_name}</p>'
                f'<p><strong>Recibo:</strong> {payslip_number} ({period})</p>'
                f'<p><strong>Motivo de escalacion:</strong> {escalate_desc}</p>'
                f'<p><strong>Conversacion:</strong> <a href="{conv_url}">#{conversation.id}</a></p>'
                f'<hr/>'
                f'<h4>Resumen de la conversacion</h4>'
                f'{messages_html}'
                f'<hr/>'
                f'<p><em>Este correo fue generado automaticamente por Glenda AI. '
                f'Requiere atencion del equipo de Recursos Humanos.</em></p>'
            )

            return {
                'message': visible_text or response_text,
                'escalate': escalate_desc,
                'send_escalation_email': {
                    'to': 'recursoshumanos@ueipab.edu.ve',
                    'subject': (
                        f'[GLENDA-ACK] Requiere atencion: {emp_name} — '
                        f'{escalate_desc[:80]}'
                    ),
                    'body_html': body_html,
                },
                'resolve': True,
                'summary': escalate_desc,
            }

        return {}
