"""HR Data Collection skill for Glenda AI Agent.

Multi-phase conversation to verify and collect employee data:
  Phase 1: Phone number (confirm/update, +58 format)
  Phase 2: Cedula de Identidad (number, expiry, photo)
  Phase 3: RIF (number, expiry, photo)
  Phase 4: Address (from RIF or manual, structured fields)
  Phase 5: Emergency contact (name + phone)

PROTECTED FIELDS: name and work_email are NEVER modified.
"""
import base64
import logging
import re

import requests

from . import (
    register_skill,
    get_ve_greeting,
    get_first_name,
    normalize_ve_phone,
    validate_rif_format,
    parse_cedula_expiry,
    parse_ve_address,
)

_logger = logging.getLogger(__name__)

# Phases in order
PHASES = [
    'phone', 'cedula', 'rif', 'address', 'emergency',
]


@register_skill('hr_data_collection')
class HrDataCollectionSkill:

    def _get_agent_config(self, conversation):
        """Read agent display settings from config."""
        env = conversation.env
        get_param = env['ir.config_parameter'].sudo().get_param
        return {
            'agent_name': get_param('ai_agent.agent_display_name', 'Glenda'),
            'institution': get_param('ai_agent.institution_display_name', 'UEIPAB'),
        }

    def get_context(self, conversation):
        """Fetch employee data and collection request state."""
        env = conversation.env
        config = self._get_agent_config(conversation)

        ctx = {
            'agent_name': config['agent_name'],
            'institution': config['institution'],
            'employee_name': '',
            'first_name': '',
            'employee_id': 0,
            'request_id': 0,
            # Existing employee data
            'current_phone': '',
            'current_cedula': '',
            'current_cedula_expiry': '',
            'current_rif': '',
            'current_rif_expiry': '',
            'current_address': '',
            'current_city': '',
            'current_state': '',
            'current_emergency_name': '',
            'current_emergency_phone': '',
            'current_work_email': '',
            # Phase completion status
            'phone_done': False,
            'cedula_done': False,
            'rif_done': False,
            'address_done': False,
            'emergency_done': False,
            # Document photos
            'cedula_photo_done': False,
            'rif_photo_done': False,
        }

        if conversation.source_model != 'hr.data.collection.request':
            return ctx
        request = env['hr.data.collection.request'].browse(conversation.source_id)
        if not request.exists():
            return ctx

        emp = request.employee_id
        ctx.update({
            'employee_name': emp.name or '',
            'first_name': get_first_name(emp.name),
            'employee_id': emp.id,
            'request_id': request.id,
            # Existing employee data
            'current_phone': emp.mobile_phone or '',
            'current_cedula': emp.identification_id or '',
            'current_cedula_expiry': str(emp.id_expiry_date) if emp.id_expiry_date else '',
            'current_rif': getattr(emp, 'ueipab_rif', '') or '',
            'current_rif_expiry': str(emp.ueipab_rif_expiry_date) if getattr(emp, 'ueipab_rif_expiry_date', None) else '',
            'current_address': emp.private_street or '',
            'current_city': emp.private_city or '',
            'current_state': emp.private_state_id.name if emp.private_state_id else '',
            'current_emergency_name': emp.emergency_contact or '',
            'current_emergency_phone': emp.emergency_phone or '',
            'current_work_email': emp.work_email or '',
            # Phase completion status (from request)
            'phone_done': request.phone_confirmed,
            'cedula_done': request.cedula_confirmed,
            'rif_done': request.rif_number_confirmed,
            'address_done': request.address_confirmed,
            'emergency_done': request.emergency_confirmed,
            'cedula_photo_done': request.cedula_photo_received,
            'rif_photo_done': request.rif_photo_received,
        })
        return ctx

    def _get_pending_phases(self, context):
        """Return list of phase names still pending."""
        pending = []
        if not context['phone_done']:
            pending.append('phone')
        if not context['cedula_done']:
            pending.append('cedula')
        if not context['rif_done']:
            pending.append('rif')
        if not context['address_done']:
            pending.append('address')
        if not context['emergency_done']:
            pending.append('emergency')
        return pending

    def _get_next_phase(self, context):
        """Return the next phase to work on."""
        pending = self._get_pending_phases(context)
        return pending[0] if pending else None

    def get_system_prompt(self, conversation, context):
        """Build comprehensive system prompt with multi-phase instructions."""
        agent_name = context['agent_name']
        institution = context['institution']
        emp_name = context['employee_name']
        first_name = context['first_name']
        pending = self._get_pending_phases(context)
        all_done = len(pending) == 0

        # Build phase status section
        phase_status_lines = []
        for phase_key, label in [
            ('phone', 'Telefono'),
            ('cedula', 'Cedula'),
            ('rif', 'RIF'),
            ('address', 'Direccion'),
            ('emergency', 'Contacto Emergencia'),
        ]:
            done = context.get(f'{phase_key}_done', False)
            status = 'COMPLETADA' if done else 'PENDIENTE'
            phase_status_lines.append(f"  - {label}: {status}")
        phase_status = '\n'.join(phase_status_lines)

        # Build existing data section for smart confirmation
        existing_data_lines = []
        if context['current_phone']:
            existing_data_lines.append(f"  - Telefono registrado: {context['current_phone']}")
        if context['current_cedula']:
            existing_data_lines.append(f"  - Cedula registrada: {context['current_cedula']}")
        if context['current_cedula_expiry']:
            existing_data_lines.append(f"  - Vencimiento cedula: {context['current_cedula_expiry']}")
        if context['current_rif']:
            existing_data_lines.append(f"  - RIF registrado: {context['current_rif']}")
        if context['current_rif_expiry']:
            existing_data_lines.append(f"  - Vencimiento RIF: {context['current_rif_expiry']}")
        if context['current_address']:
            addr_parts = [context['current_address']]
            if context['current_city']:
                addr_parts.append(context['current_city'])
            if context['current_state']:
                addr_parts.append(context['current_state'])
            existing_data_lines.append(f"  - Direccion registrada: {', '.join(addr_parts)}")
        if context['current_emergency_name']:
            existing_data_lines.append(
                f"  - Contacto emergencia: {context['current_emergency_name']} "
                f"({context['current_emergency_phone']})"
            )

        existing_data = '\n'.join(existing_data_lines) if existing_data_lines else '  (ninguno)'

        return f"""Eres {agent_name}, asistente virtual del departamento de Recursos Humanos de {institution}.
Tu tarea es verificar y recolectar datos personales del empleado {emp_name}.
Comunicacion en espanol venezolano, trato de TU, amable y profesional. Mensajes cortos.

ESTADO DE FASES:
{phase_status}

DATOS EXISTENTES DEL EMPLEADO:
{existing_data}

REGLAS CRITICAS:
1. NUNCA modifiques el nombre del empleado ({emp_name}) ni su correo institucional ({context['current_work_email']}). Si detectas una discrepancia con algun documento, informa al empleado y emite ACTION:ESCALATE.
2. Avanza las fases en orden: telefono → cedula → RIF → direccion → emergencia.
3. Si un dato ya existe, pide CONFIRMACION rapida ("Tu cedula es V15128008, es correcto?") en vez de pedirlo desde cero.
4. Si faltan fotos de cedula o RIF, pide que las envien por WhatsApp o por correo a recursoshumanos@ueipab.edu.ve.
5. SIEMPRE emite los marcadores ACTION cuando el empleado confirma un dato. Puedes emitir multiples marcadores en la misma respuesta, cada uno en su propia linea. Los marcadores son OBLIGATORIOS para que el sistema registre los datos.
6. Cuando el empleado confirma un dato existente (dice "si", "correcto", etc.), DEBES emitir el marcador PHASE_COMPLETE con el valor confirmado. Confirmar sin marcador NO guarda el dato.

INSTRUCCIONES POR FASE:

FASE 1 - TELEFONO:
- Confirma que el numero de WhatsApp actual es correcto.
- Si confirman, emite: ACTION:PHASE_COMPLETE:phone:+58 XXX XXXXXXX
- Si dan un numero nuevo, normaliza al formato +58 XXX XXXXXXX antes de emitir el marcador.
- Formato: +58 seguido de 3 digitos de area y 7 digitos (ejemplo: +58 414 2337463).

FASE 2 - CEDULA DE IDENTIDAD:
- Pide el numero de cedula (formato VXXXXXXXX, ejemplo V15128008).
- Pide la fecha de vencimiento (formato MM/AAAA, ejemplo 06/2035).
- Pide una foto o captura de la cedula.
- Emite: ACTION:PHASE_COMPLETE:cedula:V15128008
- Emite: ACTION:PHASE_COMPLETE:cedula_expiry:06/2035
- Cuando recibas la foto, emite: ACTION:SAVE_DOCUMENT:cedula

FASE 3 - RIF (Registro de Informacion Fiscal):
- Pide el numero de RIF completo (formato VXXXXXXXXX, ejemplo V151280087 — sin guiones).
- Pide una foto o captura del RIF.
- Si la foto es visible, usa tu capacidad de vision para extraer: numero RIF, fecha vencimiento, domicilio fiscal.
- Si el nombre en el RIF NO coincide con {emp_name}, NO modifiques el nombre. Emite ACTION:ESCALATE con descripcion.
- Emite: ACTION:PHASE_COMPLETE:rif_number:V151280087 (sin guiones)
- Emite: ACTION:PHASE_COMPLETE:rif_expiry:AAAA-MM-DD (formato ISO)
- Cuando recibas la foto, emite: ACTION:SAVE_DOCUMENT:rif

FASE 4 - DIRECCION:
- Si extrajiste direccion del RIF, presentala para confirmacion.
- Si no hay RIF o no se leyo, pide la direccion de residencia.
- Emite: ACTION:PHASE_COMPLETE:address:texto completo de la direccion
- Por defecto: El Tigre, Anzoategui, Venezuela (la mayoria de empleados vive ahi).

FASE 5 - CONTACTO DE EMERGENCIA:
- Pide nombre completo y numero de telefono de un contacto de emergencia.
- Emite: ACTION:PHASE_COMPLETE:emergency:Nombre Completo;+58 XXX XXXXXXX
- El separador entre nombre y telefono es punto y coma (;).

FINALIZACION:
- Cuando TODAS las 5 fases esten completadas, despidete amablemente y emite: RESOLVED:COMPLETED

ESCALACION:
- Para cualquier situacion que requiera intervencion humana, emite: ACTION:ESCALATE:descripcion breve del problema
- Esto incluye: discrepancia de nombres, empleado que reporta email incorrecto, negativa a proporcionar datos, empleado que ya no trabaja en la institucion.
- Despues de escalar, continua con las fases pendientes si es posible.

RECORDATORIO IMPORTANTE:
- Los documentos (cedula, RIF) pueden enviarse como foto, captura de pantalla o PDF.
- Si la imagen no es legible, pide otra mas clara.
- Si el documento esta vencido, aceptalo pero informa al empleado que debe renovarlo."""

    def get_greeting(self, conversation, context):
        """Build initial greeting based on existing employee data."""
        saludo = get_ve_greeting()
        first_name = context['first_name']
        agent_name = context['agent_name']
        institution = context['institution']
        pending = self._get_pending_phases(context)

        if not pending:
            return (
                f"{saludo}, {first_name}. Soy {agent_name} de Recursos Humanos de {institution}. "
                f"Solo quiero confirmar que todos tus datos estan actualizados. "
                f"Sera muy rapido."
            )

        greeting = (
            f"{saludo}, {first_name}. Soy {agent_name} de Recursos Humanos de {institution}. "
            f"Estamos actualizando los datos de nuestro personal y necesito "
            f"verificar algunos datos contigo. Solo tomara unos minutos."
        )

        # Start with first pending phase
        next_phase = pending[0]
        if next_phase == 'phone':
            if context['current_phone']:
                greeting += (
                    f"\n\nPrimero, tengo registrado tu numero como {context['current_phone']}. "
                    f"Es correcto este numero?"
                )
            else:
                greeting += (
                    f"\n\nPrimero, necesito confirmar tu numero de WhatsApp personal. "
                    f"Me lo podrias indicar?"
                )

        return greeting

    def get_reminder_message(self, conversation, context, reminder_count):
        """Build reminder message."""
        first_name = context['first_name']
        agent_name = context['agent_name']
        pending = self._get_pending_phases(context)
        pending_count = len(pending)

        if reminder_count == 0:
            return (
                f"Hola {first_name}, soy {agent_name} de Recursos Humanos. "
                f"Te escribi hace un tiempo para actualizar tus datos. "
                f"Aun nos faltan {pending_count} dato(s) por verificar. "
                f"Cuando tengas un momento, me puedes responder por aqui?"
            )
        return (
            f"Hola {first_name}, te recuerdo que seguimos pendientes "
            f"con la actualizacion de tus datos para Recursos Humanos. "
            f"Este es el ultimo recordatorio. Si no recibimos respuesta, "
            f"nos comunicaremos contigo por otro medio."
        )

    def _extract_visible_text(self, ai_response):
        """Extract text visible to the employee (strip marker lines, keep rest)."""
        lines = ai_response.split('\n')
        visible_lines = [
            line for line in lines
            if not re.match(r'^\s*(?:ACTION|RESOLVED):', line)
        ]
        text = '\n'.join(visible_lines).strip()
        return text if text else None

    def _save_document_to_employee(self, conversation, doc_type, request):
        """Download the latest attachment and save to employee identification_attachment_ids.

        Finds the most recent inbound image/document attachment in the
        conversation, downloads it if needed, creates an ir.attachment
        with naming like "Cedula - V15128008.jpg" or "RIF - V-15128008-9.pdf",
        and links it to the employee's identification_attachment_ids Many2many.

        Args:
            conversation: ai.agent.conversation record
            doc_type: 'cedula' or 'rif'
            request: hr.data.collection.request record

        Returns True if saved successfully, False otherwise.
        """
        env = conversation.env
        emp = request.employee_id

        # Find latest inbound attachment (image or document)
        attachment_msg = env['ai.agent.message'].search([
            ('conversation_id', '=', conversation.id),
            ('direction', '=', 'inbound'),
            ('attachment_url', '!=', False),
            ('attachment_type', 'in', ('image', 'document')),
        ], order='timestamp desc', limit=1)

        if not attachment_msg:
            _logger.warning(
                "HR Collection #%d: SAVE_DOCUMENT:%s — no attachment found in conversation",
                request.id, doc_type)
            return False

        # Get binary data (base64-encoded)
        binary_data = None
        mimetype = 'image/jpeg'

        if attachment_msg.attachment_id and attachment_msg.attachment_id.datas:
            binary_data = attachment_msg.attachment_id.datas
            mimetype = attachment_msg.attachment_id.mimetype or 'image/jpeg'
        elif attachment_msg.attachment_url:
            try:
                resp = requests.get(attachment_msg.attachment_url, timeout=30)
                resp.raise_for_status()
                binary_data = base64.b64encode(resp.content)
                mimetype = resp.headers.get('Content-Type', 'image/jpeg')
            except Exception as e:
                _logger.error(
                    "HR Collection #%d: failed to download %s attachment: %s",
                    request.id, doc_type, e)
                return False

        if not binary_data:
            return False

        # Build filename: "Cedula - V15128008.jpg" or "RIF - V-15128008-9.pdf"
        ext_map = {
            'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp',
            'image/gif': '.gif', 'application/pdf': '.pdf',
        }
        ext = ext_map.get(mimetype, '.jpg')

        if doc_type == 'cedula':
            doc_label = request.cedula_number or emp.identification_id or 'Unknown'
            filename = f"Cedula - {doc_label}{ext}"
        else:
            doc_label = request.rif_number_value or getattr(emp, 'ueipab_rif', '') or 'Unknown'
            filename = f"RIF - {doc_label}{ext}"

        # Create ir.attachment linked to employee
        attachment = env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'datas': binary_data,
            'mimetype': mimetype,
            'res_model': 'hr.employee',
            'res_id': emp.id,
        })

        # Add to employee's identification_attachment_ids (Many2many)
        emp.sudo().write({
            'identification_attachment_ids': [(4, attachment.id)],
        })

        _logger.info(
            "HR Collection #%d: saved %s as '%s' (attachment id=%d) for employee %s",
            request.id, doc_type, filename, attachment.id, emp.name)
        return True

    def process_ai_response(self, conversation, ai_response, context):
        """Parse Claude's response for control markers and update request.

        Can handle multiple markers in the same response (one per line).
        Returns the appropriate action dict for the conversation engine.
        """
        env = conversation.env
        request = None
        if context.get('request_id'):
            request = env['hr.data.collection.request'].browse(context['request_id'])
            if not request.exists():
                request = None

        visible_text = self._extract_visible_text(ai_response)
        from odoo import fields as odoo_fields
        now = odoo_fields.Datetime.now()

        # --- Check for ESCALATE ---
        escalate_match = re.search(r'ACTION:ESCALATE:(.+)$', ai_response, re.MULTILINE)
        if escalate_match:
            escalate_desc = escalate_match.group(1).strip()
            emp_name = context.get('employee_name', 'Empleado')
            institution = context.get('institution', 'UEIPAB')
            request_id = context.get('request_id', 0)

            # Build escalation email for HR Manager
            odoo_base = conversation.env['ir.config_parameter'].sudo().get_param(
                'web.base.url', 'http://localhost:8069')
            request_url = (
                f"{odoo_base}/web#id={request_id}"
                f"&model=hr.data.collection.request&view_type=form"
            ) if request_id else ''
            conv_url = (
                f"{odoo_base}/web#id={conversation.id}"
                f"&model=ai.agent.conversation&view_type=form"
            )

            body_html = (
                f'<h3>[{institution}] Glenda HR — Escalacion</h3>'
                f'<p><strong>Empleado:</strong> {emp_name}</p>'
                f'<p><strong>Motivo:</strong> {escalate_desc}</p>'
                f'<p><strong>Conversacion:</strong> <a href="{conv_url}">#{conversation.id}</a></p>'
            )
            if request_url:
                body_html += (
                    f'<p><strong>Solicitud:</strong> '
                    f'<a href="{request_url}">#{request_id}</a></p>'
                )
            body_html += (
                '<hr/>'
                '<p><em>Este correo fue generado automaticamente por Glenda AI. '
                'Requiere atencion del equipo de Recursos Humanos.</em></p>'
            )

            return {
                'message': visible_text or ai_response,
                'escalate': escalate_desc,
                'send_escalation_email': {
                    'to': 'recursoshumanos@ueipab.edu.ve',
                    'subject': f'[GLENDA-HR] Requiere atencion: {emp_name} — {escalate_desc[:80]}',
                    'body_html': body_html,
                },
            }

        # --- Check for RESOLVED ---
        resolved_match = re.search(r'RESOLVED:(\S+)', ai_response)
        if resolved_match:
            return {
                'resolve': True,
                'farewell_message': visible_text,
                'summary': f"Recoleccion de datos completada para {context.get('employee_name', 'empleado')}",
                'resolution_data': {'action': 'completed'},
            }

        # --- Process PHASE_COMPLETE markers ---
        phase_markers = re.findall(
            r'ACTION:PHASE_COMPLETE:(\w+):(.+?)(?:\n|$)', ai_response
        )
        for phase_key, value in phase_markers:
            value = value.strip()
            if not request:
                continue

            if phase_key == 'phone':
                normalized = normalize_ve_phone(value)
                if normalized:
                    request.write({
                        'phone_confirmed': True,
                        'phone_confirmed_date': now,
                        'phone_value': normalized,
                    })
                    _logger.info("HR Collection #%d: phone confirmed: %s", request.id, normalized)

            elif phase_key == 'cedula':
                cedula = value.strip().upper().replace(' ', '')
                request.write({
                    'cedula_confirmed': True,
                    'cedula_confirmed_date': now,
                    'cedula_number': cedula,
                })
                _logger.info("HR Collection #%d: cedula confirmed: %s", request.id, cedula)

            elif phase_key == 'cedula_expiry':
                expiry_date = parse_cedula_expiry(value)
                if expiry_date:
                    request.write({
                        'cedula_expiry_date': expiry_date,
                    })
                    _logger.info("HR Collection #%d: cedula expiry: %s", request.id, expiry_date)

            elif phase_key == 'rif_number':
                normalized_rif = validate_rif_format(value)
                if normalized_rif:
                    request.write({
                        'rif_number_confirmed': True,
                        'rif_confirmed_date': now,
                        'rif_number_value': normalized_rif,
                    })
                    _logger.info("HR Collection #%d: RIF confirmed: %s", request.id, normalized_rif)

            elif phase_key == 'rif_expiry':
                # Expect ISO format YYYY-MM-DD from Claude
                try:
                    from datetime import date as date_cls
                    parts = value.split('-')
                    rif_exp = date_cls(int(parts[0]), int(parts[1]), int(parts[2]))
                    request.write({
                        'rif_expiry_date': rif_exp,
                    })
                    _logger.info("HR Collection #%d: RIF expiry: %s", request.id, rif_exp)
                except (ValueError, IndexError):
                    _logger.warning("HR Collection #%d: invalid RIF expiry: %s", request.id, value)

            elif phase_key == 'address':
                request.write({
                    'address_confirmed': True,
                    'address_confirmed_date': now,
                    'address_value': value,
                })
                _logger.info("HR Collection #%d: address confirmed", request.id)

            elif phase_key == 'emergency':
                # Format: "Name;+58 XXX XXXXXXX"
                parts = value.split(';', 1)
                emer_name = parts[0].strip() if parts else value
                emer_phone = normalize_ve_phone(parts[1].strip()) if len(parts) > 1 else ''
                request.write({
                    'emergency_confirmed': True,
                    'emergency_confirmed_date': now,
                    'emergency_name': emer_name,
                    'emergency_phone': emer_phone or '',
                })
                _logger.info("HR Collection #%d: emergency confirmed: %s", request.id, emer_name)

        # --- Process SAVE_DOCUMENT markers ---
        doc_markers = re.findall(r'ACTION:SAVE_DOCUMENT:(\w+)', ai_response)
        for doc_type in doc_markers:
            if not request:
                continue
            if doc_type == 'cedula':
                saved = self._save_document_to_employee(conversation, 'cedula', request)
                request.write({
                    'cedula_photo_received': True,
                    'cedula_photo_date': now,
                })
                _logger.info(
                    "HR Collection #%d: cedula photo %s",
                    request.id, "saved to employee" if saved else "flagged (save pending)")
            elif doc_type == 'rif':
                saved = self._save_document_to_employee(conversation, 'rif', request)
                request.write({
                    'rif_photo_received': True,
                    'rif_photo_date': now,
                })
                _logger.info(
                    "HR Collection #%d: RIF photo %s",
                    request.id, "saved to employee" if saved else "flagged (save pending)")

        # --- Update request state ---
        if request:
            request.invalidate_recordset(['phases_completed', 'progress'])
            if request.phases_completed == 5 and request.state != 'completed':
                request.state = 'completed'
            elif request.phases_completed > 0 and request.state == 'draft':
                request.state = 'in_progress'

        # Forward visible text to employee
        return {'message': visible_text or ai_response}

    def on_resolve(self, conversation, resolution_data):
        """Write all collected data from the request to hr.employee.

        PROTECTED: name and work_email are NEVER modified.
        """
        env = conversation.env
        if conversation.source_model != 'hr.data.collection.request':
            return
        request = env['hr.data.collection.request'].browse(conversation.source_id)
        if not request.exists():
            return

        emp = request.employee_id
        if not emp.exists():
            return

        writes = {}

        # Phase 1: Phone
        if request.phone_confirmed and request.phone_value:
            writes['mobile_phone'] = request.phone_value

        # Phase 2: Cedula
        if request.cedula_confirmed and request.cedula_number:
            writes['identification_id'] = request.cedula_number
        if request.cedula_expiry_date:
            writes['id_expiry_date'] = request.cedula_expiry_date

        # Phase 3: RIF
        if request.rif_number_confirmed and request.rif_number_value:
            if hasattr(emp, 'ueipab_rif'):
                writes['ueipab_rif'] = request.rif_number_value
            if hasattr(emp, 'ueipab_rif_expiry_date') and request.rif_expiry_date:
                writes['ueipab_rif_expiry_date'] = request.rif_expiry_date

        # Phase 4: Address — parse structured components from free text
        if request.address_confirmed and request.address_value:
            parsed = parse_ve_address(request.address_value)
            writes['private_street'] = parsed['street'] or request.address_value
            if parsed['city']:
                writes['private_city'] = parsed['city']
            elif not emp.private_city:
                writes['private_city'] = 'El Tigre'
            if parsed['state_code']:
                state = env['res.country.state'].search(
                    [('code', '=', parsed['state_code'])], limit=1)
                if state:
                    writes['private_state_id'] = state.id
            elif not emp.private_state_id:
                # Default: Anzoátegui (V02 in Odoo)
                anzoategui = env['res.country.state'].search(
                    [('code', '=', 'V02')], limit=1)
                if anzoategui:
                    writes['private_state_id'] = anzoategui.id
            if parsed['zip']:
                writes['private_zip'] = parsed['zip']
            elif not emp.private_zip:
                writes['private_zip'] = '6050'
            ve = env['res.country'].search([('code', '=', 'VE')], limit=1)
            if ve:
                writes['private_country_id'] = ve.id

        # Phase 5: Emergency
        if request.emergency_confirmed:
            if request.emergency_name:
                writes['emergency_contact'] = request.emergency_name
            if request.emergency_phone:
                writes['emergency_phone'] = request.emergency_phone

        if writes:
            emp.sudo().write(writes)
            _logger.info(
                "HR Collection #%d: wrote %d fields to employee %s (id=%d): %s",
                request.id, len(writes), emp.name, emp.id, list(writes.keys()),
            )

        # Update request state
        request.write({
            'state': 'completed',
            'ai_conversation_id': conversation.id,
        })

        # Post chatter note on employee
        config = self._get_agent_config(conversation)
        agent_name = config['agent_name']
        field_summary = ', '.join(writes.keys()) if writes else '(sin cambios)'
        emp.sudo().message_post(
            body=f"<b>[{agent_name} - Recoleccion de Datos]</b><br/>"
                 f"Datos actualizados: {field_summary}<br/>"
                 f"Solicitud: #{request.id}",
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
