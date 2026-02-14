import json
import logging
import re

from . import register_skill, get_ve_greeting, get_first_name

_logger = logging.getLogger(__name__)


@register_skill('bounce_resolution')
class BounceResolutionSkill:
    """Skill: resolve bounced emails by contacting customers via WhatsApp."""

    def _get_agent_config(self, conversation):
        """Get agent display name and institution from system parameters."""
        icp = conversation.env['ir.config_parameter'].sudo()
        return {
            'agent_name': icp.get_param('ai_agent.agent_display_name', 'Asistente Virtual'),
            'institution': icp.get_param('ai_agent.institution_display_name', 'UEIPAB'),
        }

    def get_context(self, conversation):
        """Get context from the source mail.bounce.log record."""
        ctx = {
            'bounced_email': '',
            'bounce_reason': '',
            'partner_name': conversation.partner_id.name or '',
            'first_name': get_first_name(conversation.partner_id.name),
            'remaining_emails': [],
        }
        ctx.update(self._get_agent_config(conversation))
        if conversation.source_model == 'mail.bounce.log' and conversation.source_id:
            bounce_log = conversation.env['mail.bounce.log'].browse(conversation.source_id)
            if bounce_log.exists():
                ctx['bounced_email'] = bounce_log.bounced_email or ''
                ctx['bounce_reason'] = dict(
                    bounce_log._fields['bounce_reason'].selection
                ).get(bounce_log.bounce_reason, bounce_log.bounce_reason or '')
                ctx['bounce_log_id'] = bounce_log.id
                # Load family context from Akdemia
                family_json = bounce_log.akdemia_family_emails
                ctx['family_context'] = json.loads(family_json) if family_json else []
                # Check if partner has other emails besides the bounced one
                all_emails = conversation.partner_id.email or ''
                parts = [e.strip() for e in all_emails.replace(',', ';').split(';') if e.strip()]
                bounced_lower = (bounce_log.bounced_email or '').lower()
                ctx['remaining_emails'] = [e for e in parts if e.lower() != bounced_lower]
        return ctx

    def _build_family_section(self, context):
        """Build family context section for system prompt from Akdemia data."""
        family = context.get('family_context', [])
        if not family:
            return '', ''

        # Collect unique parent entries (name + email) across all student rows
        seen = set()
        lines = []
        for record in family:
            for parent in record.get('parents', []):
                key = (parent.get('name', ''), parent.get('email', ''))
                if key in seen or not parent.get('name'):
                    continue
                seen.add(key)
                email_part = parent.get('email') or 'sin correo'
                lines.append(
                    f"  - {parent['name']} ({parent.get('slot', '?')}): {email_part}")

        if not lines:
            return '', ''

        section = (
            "CONTEXTO FAMILIAR (Akdemia - plataforma escolar):\n"
            "Los siguientes correos estan registrados en Akdemia para la familia de este contacto:\n"
            + '\n'.join(lines) + '\n\n'
        )
        instruction = (
            "- IMPORTANTE: Si el cliente proporciona un correo que ya aparece en el CONTEXTO FAMILIAR "
            "bajo otro nombre (otro representante/familiar), informale amablemente que ese correo ya "
            "esta registrado a nombre de otra persona en el sistema escolar y pidele un correo personal "
            "diferente. NO aceptes ese correo como nuevo.\n"
        )
        return section, instruction

    def get_system_prompt(self, conversation, context):
        """Return Claude system prompt for bounce resolution."""
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        first_name = context.get('first_name', 'Cliente')
        remaining = context.get('remaining_emails', [])

        # Build multi-email context section
        if remaining:
            remaining_list = ', '.join(remaining)
            email_context = (
                f"- Correo con problemas: {context.get('bounced_email', 'desconocido')}\n"
                f"- Otros correos vigentes del contacto: {remaining_list}\n"
                f"- Razón del rebote: {context.get('bounce_reason', 'desconocida')}\n"
            )
            multi_email_instructions = (
                "- El contacto tiene otros correos vigentes además del que rebotó. "
                "El correo con problemas será retirado de nuestros registros. "
                "Tu objetivo es confirmar que el cliente está conforme con sus otros correos "
                "y ofrecerle agregar uno adicional si lo desea.\n"
                "- Si el cliente está conforme con sus correos actuales y no desea agregar otro, "
                "responde: RESOLVED:REMOVE_ONLY\n"
                "- Si el cliente quiere agregar un correo nuevo además de los que ya tiene, "
                "confírmalo repitiéndolo y responde: RESOLVED:nuevo@email.com\n"
            )
        else:
            email_context = (
                f"- Correo con problemas: {context.get('bounced_email', 'desconocido')}\n"
                f"- Razón del rebote: {context.get('bounce_reason', 'desconocida')}\n"
            )
            multi_email_instructions = (
                "- El contacto NO tiene otros correos registrados. "
                "Es importante obtener un correo alternativo.\n"
                "- Si el cliente proporciona un email nuevo, confírmalo repitiéndolo y responde "
                "EXACTAMENTE con el formato: RESOLVED:nuevo@email.com\n"
            )

        # Build family context section
        family_section, family_instruction = self._build_family_section(context)

        return (
            f"Eres {agent_name}, asistente de {institution}, ubicado en Venezuela. "
            "Tu tarea es contactar amablemente a un representante o cliente cuyo correo electrónico "
            "está presentando problemas de entrega.\n\n"
            "CONTEXTO:\n"
            f"- Nombre del contacto: {first_name}\n"
            f"{email_context}"
            f"{family_section}"
            "INSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano, de forma cercana y cálida.\n"
            f"- Dirígete al cliente por su nombre ({first_name}).\n"
            "- Sé amable, profesional y conciso. No uses emojis.\n"
            f"{multi_email_instructions}"
            f"{family_instruction}"
            "- Si el cliente dice que su correo actual (el que rebotó) ya funciona (liberó espacio, lo arregló, etc.) "
            "o pide que le envíes un correo para verificar, DEBES responder con tu mensaje al cliente "
            "seguido del marcador ACTION:VERIFY_EMAIL al final (sin email, se verifica el correo rebotado). "
            "Si confirma recepción, responde: RESOLVED:RESTORE\n"
            "- Si el cliente proporciona un correo NUEVO y quieres verificar que funcione "
            "antes de aplicarlo, responde con: ACTION:VERIFY_EMAIL:nuevo@email.com "
            "(reemplaza nuevo@email.com con el correo real del cliente). "
            "Si confirma recepción del correo de verificación, responde: RESOLVED:nuevo@email.com\n"
            "  Ejemplo: 'Perfecto, le envío un correo de verificación a su nueva dirección "
            "para confirmar que funcione. Revise su bandeja y avíseme cuando lo reciba. "
            "ACTION:VERIFY_EMAIL:dayanacperdomo@yahoo.com'\n"
            "  El sistema enviará el correo automáticamente al email indicado. SIEMPRE incluye el marcador.\n"
            "- Si el cliente no desea proporcionar otro correo, responde: RESOLVED:DECLINED\n"
            "- Si el cliente solicita algo fuera del tema del correo electrónico "
            "(constancia de estudios, factura, cambio de datos, información de pagos, etc.), "
            "infórmale amablemente que has registrado su solicitud y que nuestro equipo de soporte "
            "le contactará al respecto. Luego retoma el tema del correo. "
            "Incluye al final de tu respuesta: ACTION:ESCALATE:breve descripcion del requerimiento\n"
            "- Si alguien que NO es el contacto responde (un familiar, pareja, etc.) y te da "
            "un numero de telefono diferente para comunicarte con el contacto real, "
            "incluye al final: ACTION:ALTERNATIVE_PHONE:04XXXXXXXXX (solo digitos, sin guiones ni espacios). "
            "Puedes incluirlo junto con ACTION:ESCALATE si aplica.\n"
            "- No reveles detalles técnicos del rebote a menos que el cliente pregunte.\n"
            "- Máximo 4-5 intercambios antes de cerrar la conversación.\n"
            "- IMPORTANTE: Los marcadores RESOLVED: y ACTION: son comandos internos del sistema. "
            "El cliente NO los ve. SIEMPRE debes incluirlos al final de tu respuesta cuando apliquen. "
            "Nunca omitas un marcador cuando la situación lo requiera.\n"
            "- No puedes ver imágenes ni archivos adjuntos. Si el cliente envía una imagen, "
            "pídele amablemente que te escriba la información en texto.\n"
            "- El cliente puede enviar varios mensajes seguidos. Lee TODOS los mensajes del cliente "
            "completos antes de responder. No asumas el significado de un mensaje aislado.\n"
            "- Si ya enviaste un correo de verificación a una dirección y el cliente menciona a otra persona "
            "o proporciona un correo que parece de alguien más, NO cambies automáticamente. "
            "Pregunta primero para aclarar a quién pertenece ese correo.\n"
        )

    def get_greeting(self, conversation, context):
        """Return the initial WhatsApp greeting message."""
        first_name = context.get('first_name', 'estimado/a')
        email = context.get('bounced_email', 'su correo')
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        remaining = context.get('remaining_emails', [])
        saludo = get_ve_greeting()

        if remaining:
            remaining_list = ', '.join(remaining)
            return (
                f"{saludo}, {first_name}! Le escribe {agent_name} desde {institution}. "
                f"Nos comunicamos con usted porque hemos detectado que su correo electrónico "
                f"({email}) está presentando inconvenientes para recibir nuestras comunicaciones. "
                f"Vamos a retirar ese correo de nuestros registros. "
                f"Sus otros correos ({remaining_list}) se mantienen sin cambios. "
                f"¿Desea agregar algún otro correo adicional o está conforme con los que tiene?"
            )
        return (
            f"{saludo}, {first_name}! Le escribe {agent_name} desde {institution}. "
            f"Nos comunicamos con usted porque hemos detectado que su correo electrónico "
            f"({email}) está presentando inconvenientes para recibir nuestras comunicaciones. "
            f"¿Nos podría facilitar un correo alternativo para mantenernos en contacto?"
        )

    def get_reminder_message(self, conversation, context, reminder_count):
        """Return a WhatsApp reminder message for bounce resolution."""
        first_name = context.get('first_name', 'estimado/a')
        email = context.get('bounced_email', 'su correo')
        agent_name = context.get('agent_name', 'Asistente Virtual')
        institution = context.get('institution', 'UEIPAB')
        saludo = get_ve_greeting()

        if reminder_count == 0:
            return (
                f"{saludo}, {first_name}. Le escribimos nuevamente desde {institution}. "
                f"Quedamos pendientes de su respuesta sobre el inconveniente con su correo "
                f"electronico ({email}). Si nos puede facilitar un correo alternativo o "
                f"confirmarnos que su correo actual ya esta funcionando, se lo agradecemos."
            )
        return (
            f"{saludo}, {first_name}. Le contactamos por ultima vez desde {institution} "
            f"respecto al inconveniente con su correo electronico ({email}). "
            f"Si no recibimos respuesta, cerraremos esta solicitud. "
            f"Quedamos a su disposicion."
        )

    def _extract_visible_text(self, ai_response):
        """Extract visible text before any internal marker (RESOLVED: or ACTION:)."""
        # ACTION:ESCALATE: has free-form description, match it first
        esc_match = re.search(r'ACTION:ESCALATE:', ai_response)
        if esc_match:
            text = ai_response[:esc_match.start()].strip()
            return text if text else None
        # Original pattern for RESOLVED:xxx and ACTION:VERIFY_EMAIL
        match = re.search(r'(?:RESOLVED|ACTION):\S+', ai_response)
        if match:
            text = ai_response[:match.start()].strip()
            return text if text else None
        return None

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for resolution signals and actions."""
        # Check for ACTION:ALTERNATIVE_PHONE (may appear alone or with ESCALATE)
        phone_match = re.search(r'ACTION:ALTERNATIVE_PHONE:(\S+)', ai_response)

        # Check for ACTION:ESCALATE: (intermediate, conversation continues)
        escalate_match = re.search(r'ACTION:ESCALATE:(.+)$', ai_response, re.MULTILINE)
        if escalate_match:
            escalation_desc = escalate_match.group(1).strip()
            visible_text = self._extract_visible_text(ai_response)
            result = {
                'message': visible_text or ai_response,
                'escalate': escalation_desc,
            }
            if phone_match:
                result['alternative_phone'] = phone_match.group(1).strip()
            return result

        # Standalone ACTION:ALTERNATIVE_PHONE (without ESCALATE)
        if phone_match:
            visible_text = self._extract_visible_text(ai_response)
            return {
                'message': visible_text or ai_response,
                'alternative_phone': phone_match.group(1).strip(),
            }

        # Check for ACTION:VERIFY_EMAIL or ACTION:VERIFY_EMAIL:target@email.com
        verify_match = re.search(r'ACTION:VERIFY_EMAIL(?::(\S+))?', ai_response)
        if verify_match:
            # If email specified after colon, verify that email; otherwise verify bounced email
            target_email = verify_match.group(1) if verify_match.group(1) else context.get('bounced_email', '')
            visible_text = self._extract_visible_text(ai_response)
            return {
                'message': visible_text or ai_response,
                'send_verification_email': target_email,
            }

        # Check for resolution patterns
        resolve_match = re.search(r'RESOLVED:(\S+)', ai_response)
        if resolve_match:
            resolution_value = resolve_match.group(1)
            farewell = self._extract_visible_text(ai_response)

            if resolution_value == 'RESTORE':
                return {
                    'resolve': True,
                    'farewell_message': farewell,
                    'summary': 'Cliente confirma recepcion de correo de verificacion. Email restaurado.',
                    'resolution_data': {'action': 'restore'},
                }
            elif resolution_value == 'REMOVE_ONLY':
                return {
                    'resolve': True,
                    'farewell_message': farewell,
                    'summary': 'Correo rebotado retirado. Cliente conforme con correos restantes.',
                    'resolution_data': {'action': 'remove_only'},
                }
            elif resolution_value == 'DECLINED':
                return {
                    'resolve': True,
                    'farewell_message': farewell,
                    'summary': 'Cliente no desea proporcionar email alternativo.',
                    'resolution_data': {'action': 'declined'},
                }
            else:
                # Should be a new email
                new_email = resolution_value.strip()
                return {
                    'resolve': True,
                    'farewell_message': farewell,
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

        elif action == 'remove_only':
            # Remove bounced email, keep remaining. No new email to add.
            from odoo import fields as odoo_fields
            if bounce_log.partner_id:
                bounce_log._remove_email_from_field(
                    bounce_log.partner_id, 'email', bounce_log.bounced_email)
                bounce_log.partner_id.message_post(
                    body=(
                        '<strong>Bounce Log - Email retirado</strong><br/>'
                        f'Email retirado: <code>{bounce_log.bounced_email}</code><br/>'
                        'Cliente conforme con correos restantes.<br/>'
                        'Resuelto por: AI Agent (Glenda)'
                    ),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            # Remove from mailing.contact too
            bounced_lower = (bounce_log.bounced_email or '').lower()
            mc_records = conversation.env['mailing.contact'].sudo().search(
                [('email', 'ilike', bounce_log.bounced_email)])
            for mc in mc_records:
                mc_emails = [e.strip().lower() for e in (mc.email or '').split(';') if e.strip()]
                if bounced_lower in mc_emails:
                    bounce_log._remove_email_from_field(mc, 'email', bounce_log.bounced_email)
            # Target state: akdemia_pending if email is in Akdemia, else resolved
            target_state = 'akdemia_pending' if bounce_log.in_akdemia else 'resolved'
            bounce_log.write({
                'state': target_state,
                'resolved_date': odoo_fields.Datetime.now(),
                'resolved_by': conversation.env.uid,
            })
            _logger.info("Bounce log %d: bounced email removed, state=%s",
                         bounce_log.id, target_state)

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
