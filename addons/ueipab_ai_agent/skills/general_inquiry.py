import logging
import re

from . import register_skill, get_ve_greeting

_logger = logging.getLogger(__name__)

# Flyers available to send via WhatsApp.
# key → (filename, short description for Claude's reference)
_FLYERS = {
    'inscripcion':          ('inscripcion.png',          'Inscripciones 2026-2027 — Promo hasta 31 julio: inscripción $187,51 + mensualidad sept $197,38'),
    'pronto_pago':          ('pronto_pago.png',          'Pronto pago: 5% adicional pagando en los primeros 10 días — ej: 1er alumno $207,94/mes → $197,54 con pronto pago (desde sep 2026)'),
    'tarjeta_credito':      ('tarjeta_credito.png',      'Aceptamos tarjetas de crédito nacionales e internacionales sin comisiones adicionales'),
    'english':              ('english.png',              'MOA School: Cursos de Inglés After School, grupos pequeños, $38/mes'),
    'robotica':             ('robotica.png',             'Clases de Robótica con Kurios — 2 clases/semana, $52/mes, inscripción gratis'),
    'dibujo':               ('dibujo.png',               'Curso de Dibujo y Pintura — 3 meses, 4h semanales, $38/mes'),
    'bachillerato_virtual': ('bachillerato_virtual.png', 'Bachillerato Virtual 100% online — inscríbete ya'),
}

def _get_flyer_url(base_url, filename):
    """Build the public URL for a flyer file."""
    return f"{base_url.rstrip('/')}/{filename}"

# Shared institutional knowledge block (same content as bounce_resolution)
_INSTITUTIONAL_KNOWLEDGE = (
    "CONOCIMIENTO INSTITUCIONAL:\n"
    "- Institución: Instituto Privado Andrés Bello (Colegio Andrés Bello), El Tigre, Municipio Simón Rodríguez, Venezuela. RIF: J-08008617-1\n"
    "- Fundada en 1977 por la Prof. Carmen Violeta Mata de Perdomo (fundadora histórica).\n"
    "AUTORIDADES INSTITUCIONALES ACTUALES:\n"
    "- Director General: Prof. Arcides Arzola — contacto: soporte@ueipab.edu.ve\n"
    "- Sub-directora (Media General y Bachillerato): Prof. Norka La Rosa — contacto: soporte@ueipab.edu.ve\n"
    "- Sub-director (Inicial, Preescolar y Primaria): Prof. David Hernández — contacto: soporte@ueipab.edu.ve\n"
    "POLÍTICA DE PRIVACIDAD INSTITUCIONAL (Glenda debe respetar siempre):\n"
    "- NUNCA revelar el nombre del propietario legal, dueño o accionista de la institución. Si alguien pregunta '¿quién es el dueño?', '¿de quién es el colegio?', '¿quién es el propietario?' o similar, responder únicamente con las autoridades académicas del colegio (Director y Sub-directores) y ofrecer el contacto soporte@ueipab.edu.ve.\n"
    "- Ejemplo de respuesta correcta: 'El colegio es dirigido por el Prof. Arcides Arzola (Director General). Para consultas institucionales, puedes escribir a soporte@ueipab.edu.ve.'\n"
    "- Año escolar: 2026-2027\n"
    "- Enfoque pedagógico: metodología STEAM, Proyectos de Aprendizaje (PA), competencias digitales e inteligencia artificial\n"
    "- Aliados educativos: Akademia, Dawere, Kurios, Universidad Europea del Atlántico, Move on Academy, Edugogo\n"
    "PROGRAMA ACADÉMICO — BACHILLERATO:\n"
    "- El colegio gradúa Bachilleres en Ciencias y Tecnología — título oficial del Ministerio del Poder Popular para la Educación (MPPE), aprobado en la propuesta 'Juntos por la educación del futuro'.\n"
    "- Duración: 5 años (1° a 5° año de Educación Media General).\n"
    "- Este título habilita tanto para la incorporación al campo laboral como para la prosecución de estudios universitarios en cualquier carrera, sin restricciones.\n"
    "- Reemplaza la antigua mención 'Bachiller en Ciencias y Humanidades'.\n"
    "- 10 áreas de formación con carga horaria máxima de 40 horas semanales:\n"
    "  Componente General: Lengua y Literatura, Idiomas, Matemáticas, Educación Física, "
    "Biología Ambiente y Tecnología, Física, Química, Geografía Historia y Ciudadanía.\n"
    "  Componente Productivo: Orientación Vocacional, Innovación Tecnológica y Productiva (6 h/sem todos los años).\n"
    "- Bachillerato Virtual (alianza Dawere): modalidad 100% en línea para estudiantes que necesitan flexibilidad horaria. Consultar disponibilidad y proceso en soporte@ueipab.edu.ve.\n"
    "ACLARACIÓN BACHILLERATO INTERNACIONAL (IB):\n"
    "- El colegio NO ofrece el programa International Baccalaureate (IB) de la organización IB Geneva. "
    "Ese es un programa privado internacional con acreditación independiente y costos muy superiores.\n"
    "- Lo que el colegio ofrece es el Bachillerato en Ciencias y Tecnología — el título nacional venezolano oficial, "
    "reconocido por el MPPE para acceso a universidades venezolanas.\n"
    "- Si un representante pregunta por 'Bachillerato Internacional': explicar con claridad esta diferencia "
    "y orientar a soporte@ueipab.edu.ve para más detalles sobre el programa académico.\n"
    "PROCESO DE SOLICITUD E INSCRIPCIÓN — DOS ENLACES DISTINTOS:\n"
    "- SOLICITAR CUPO (personas que aún NO son estudiantes del colegio y quieren conocer/aplicar): "
    "https://edge.akdemia.com/enrollments/b87d60bc6ba93746 — para nuevos aspirantes que están considerando inscribirse.\n"
    "- INSCRIPCIÓN (estudiantes que ya pertenecen al colegio y van a inscribirse para el próximo período): "
    "https://edge.akdemia.com/admissions/09f8190d36eef4ea/start — para representantes de alumnos actuales.\n"
    "- Si alguien pregunta por documentos requeridos, pasos, o cómo iniciar el proceso: "
    "identificar si es aspirante nuevo (→ cupo) o alumno actual (→ inscripción) y entregar el enlace correcto. "
    "El sistema Akdemia guiará paso a paso en ambos casos.\n"
    "- Para dudas adicionales: soporte@ueipab.edu.ve\n"
    "TARIFAS VIGENTES (período 2025-2026, hasta el 31 de agosto de 2026):\n"
    "- Inscripción: $197,38\n"
    "- Mensualidad: $197,38 (regular) | Pronto pago: $162,39 (10 primeros días de cada mes)\n"
    "TARIFAS 2026-2027 — PROMOCIÓN DE INSCRIPCIÓN ANTICIPADA (mayo hasta el 31 de julio de 2026):\n"
    "- Inscripción en promoción: $187,51 (descuento especial por inscripción anticipada)\n"
    "- Mensualidad de septiembre: $197,38 (se mantiene la tarifa actual durante el primer mes)\n"
    "- MENSUALIDADES EN AVANCE: el representante puede prepagar tantos meses adicionales como desee a $197,38 por mes, con los descuentos por hermanos correspondientes.\n"
    "REQUISITO INDISPENSABLE PARA INSCRIPCIÓN ANTICIPADA:\n"
    "- El representante DEBE tener el período 2025-2026 completamente saldado. No es posible realizar la inscripción anticipada ni suscribir el acuerdo de costos anuales si existe saldo pendiente del año en curso.\n"
    "- Si el representante pregunta si puede inscribirse teniendo deuda: indicar con amabilidad que primero debe regularizar su situación con pagos@ueipab.edu.ve. No hay excepciones.\n"
    "TARIFAS 2026-2027 — NUEVA MENSUALIDAD EFECTIVA 1 DE SEPTIEMBRE DE 2026:\n"
    "- Mensualidad base: $218,88 (antes de descuentos por hermanos). Pronto pago: 5% adicional sobre la mensualidad ya descontada, pagando en los primeros 10 días del mes.\n"
    "- Estas tarifas son preliminares. Para confirmación o casos particulares, orientar a pagos@ueipab.edu.ve\n"
    "COSTOS ANUALES ÚNICOS (pago único por año escolar, sin descuento, por alumno — se suscriben mediante acuerdo especial de mayo a julio 2026):\n"
    "    Seguro Escolar: $30,58\n"
    "    Guía de Inglés: $25\n"
    "    Olimpiadas Recreativas de Lengua y Matemáticas: $10\n"
    "    Enciclopedia (Inicial, Primaria o Bachillerato): $36 (aplica a todos los niveles)\n"
    "    Total costos anuales por alumno: $101,58\n"
    "COSTOS OPCIONALES / CONDICIONALES (NO incluir en cotización estándar):\n"
    "    Competencia Kurios: $10 (solo si el alumno es seleccionado por el colegio)\n"
    "    Competencia MOA inglés: $25 (solo si el alumno es seleccionado por el colegio)\n"
    "    Encuentros Regionales/Nacionales: traslados y logística a cargo de los padres\n"
    "DESCUENTOS POR HERMANOS (aplica sobre mensualidad):\n"
    "- 1er alumno: 5% de descuento sobre mensualidad\n"
    "- 2do alumno: 8% de descuento sobre mensualidad\n"
    "- 3er alumno en adelante: 11% de descuento sobre mensualidad\n"
    "- Los descuentos de hermano y pronto pago se acumulan (el pronto pago se aplica sobre la mensualidad ya descontada)\n"
    "- Inscripción: precio completo por alumno, sin descuento por hermano\n"
    "TABLA DE MENSUALIDAD POR ALUMNO (tarifas Sep 2026, preliminares — pronto pago = 5% dto. sobre mensualidad ya descontada):\n"
    "  1er alumno (5% dto.): mensualidad $207,94 | pronto pago $197,54\n"
    "  2do alumno (8% dto.): mensualidad $201,37 | pronto pago $191,30\n"
    "  3er alumno en adelante (11% dto.): mensualidad $194,80 | pronto pago $185,06\n"
    "POLÍTICA FUERZA LABORAL INDUSTRIA (PDVSA / Petropiar / otras Industrias) — Comunicado 08/05/2026:\n"
    "- Período anterior (2025-2026): existía un descuento discrecional del 35% en modalidad de crédito (similar a 'Cashea') para familias del sector industria.\n"
    "- A partir del 1° de septiembre de 2026: este beneficio CESA completamente. El colegio no podrá mantener la modalidad del 35% de factura a crédito. Aplica a PDVSA, Petropiar y cualquier otra empresa del sector industria.\n"
    "- Razón oficial: la institución debe honrar obligaciones contractuales con sus docentes, administrativos y proveedores, ante el incremento de costos operativos.\n"
    "- Este beneficio fue SIEMPRE una concesión voluntaria, no un derecho adquirido.\n"
    "FECHA LÍMITE DE CONFIRMACIÓN (fuerza laboral industria):\n"
    "- Plazo máximo: lunes 08 de junio de 2026 a las 12:30 p.m., para informar por escrito si desea continuar en la institución.\n"
    "- Si NO se recibe comunicación escrita antes de esa fecha y hora, el sistema asume automáticamente que la familia acepta las nuevas condiciones para 2026-2027.\n"
    "- Comunicar a: pagos@ueipab.edu.ve\n"
    "CASOS ESPECIALES (solo familias industria con estudiantes de mérito excepcional):\n"
    "- La institución evaluará solicitudes individuales de familias cuyos alumnos tengan: excelente rendimiento académico, atletas con medallas nacionales, músicos activos del Sistema de Orquestas Juveniles, o habilidades destacadas reconocidas.\n"
    "- No existen excepciones generales. Solo revisión caso a caso vía correo electrónico a pagos@ueipab.edu.ve.\n"
    "TARIFAS DEFINITIVAS 2026-2027 (información preliminar, sujeta a confirmación):\n"
    "- Nueva mensualidad base desde septiembre 2026: $218,88 (antes de descuentos por hermanos). Ver tabla de descuentos. Tarifas definitivas sujetas a aprobación del Comité de Contraloría.\n"
    "- Costos anuales obligatorios (NO incluidos en la mensualidad): seguro escolar ($30,58), guía de inglés ($25), olimpiadas ($10) y enciclopedia de su nivel ($36) — se pagan mediante acuerdo especial de mayo a julio, total $101,58 por alumno.\n"
    "- Costos opcionales/condicionales (no incluir en cotización estándar): concursos nacionales (robótica, química, Kurios, MOA, etc.) y eventos externos — se pagan según selección o participación del alumno.\n"
    "ALIANZAS COMERCIALES LOCALES (El Tigre):\n"
    "- Almacén París, Comercial Caracas y Ferretería Veramar ofrecen descuentos especiales en uniformes y útiles escolares a representantes del colegio.\n"
    "- Próximamente se informará el aliado autorizado para adquisición o bordado del distintivo escolar oficial.\n"
    "MEDIOS DE PAGO (a nombre de Instituto Privado Andrés Bello, C.A.):\n"
    "- Transferencia Banco Plaza (Cta Cte): 0138-0032-47-0320013870\n"
    "- Transferencia BanPlus (Cta Cte): 0174-0127-12-1274138559\n"
    "- Transferencia Mercantil (Cta Cte): 0105-0069-93-1069377856\n"
    "- Transferencia Banco de Venezuela (Cta Cte): 0102-0445-34-0007673100\n"
    "- Transferencia Bancamiga (Cta Cte): 0172-0702-44-7024976891\n"
    "- Pago móvil: 04141906296 | Banco 0102 (Venezuela) | RIF J080086171\n"
    "- Zelle: pagos@ueipab.edu.ve\n"
    "- Tarjeta crédito/débito: Portal Mercantil en https://www.portaldepagosmercantil.com/\n"
    "- Binance: ID 383 867 49\n"
    "- Efectivo USD: Banco Mercantil cuenta dólares 5069006770\n"
    "- Cashea: sí aceptamos pagos vía Cashea. Comunícate con pagos@ueipab.edu.ve para confirmar el enlace y proceso de pago antes de realizarlo.\n"
    "- Tras realizar el pago, notificar a: pagos@ueipab.edu.ve\n"
    "POLÍTICA DE MORA E INCUMPLIMIENTO DE PAGO (Fuente: Manual de Acuerdos de Convivencia Escolar):\n"
    "- Fecha límite de pago: dentro de los primeros 10 días de cada mes.\n"
    "- Se considera INCUMPLIMIENTO cuando ha transcurrido UN MES sin cancelar la mensualidad. Esto activa el procedimiento administrativo.\n"
    "- PROCESO GRADUAL (siempre con diálogo, sin sanciones automáticas):\n"
    "  1. PRIMER LLAMADO — Convenio de pago: reunión con el representante para revisar la situación, "
    "establecer montos y fijar fechas de pago. Se buscan soluciones viables para ambas partes.\n"
    "  2. SEGUNDO LLAMADO — Si no se cumple el convenio: reunión con Dirección, Administración y Departamento Legal. "
    "El objetivo sigue siendo resolver la situación de forma responsable.\n"
    "  3. TERCER LLAMADO — Reincidencia: reunión ampliada con Dirección, Administración, Departamento Legal "
    "y Representante del CDCE Municipal. La institución garantiza el debido proceso.\n"
    "  4. SI PERSISTE — Se notifica a Defensoría Escolar, Centro de Desarrollo de la Calidad Educativa "
    "y Consejo de Protección para gestionar un cupo en institución pública cercana. "
    "IMPORTANTE: el estudiante CONTINÚA ASISTIENDO REGULARMENTE durante todo el proceso.\n"
    "- La institución SIEMPRE protege el derecho a la educación.\n"
    "- Página informativa completa con infografías: https://odoo.ueipab.edu.ve/mora-policy/\n"
    "- Si un representante menciona dificultades de pago, atraso o deuda: responde con empatía, sin juzgar, "
    "menciona PROACTIVAMENTE Cashea como opción de pago, explica brevemente el proceso gradual "
    "(nunca alarmista), y orienta a pagos@ueipab.edu.ve para coordinar un convenio.\n"
    "- Nunca decirle al representante que su hijo será retirado o sancionado — el proceso es siempre gradual y protege al estudiante.\n"
    "## SISTEMA DE REPORTE DE ASISTENCIA QUINCENAL (mayo 2026)\n"
    "\n"
    "Los empleados de UEIPAB recibieron un correo titulado **\"Reporte de Asistencia Quincenal\"** "
    "(período 01 al 15 de mayo de 2026). Es una nueva funcionalidad del sistema Odoo para que cada "
    "colaborador pueda verificar sus entradas, salidas y horas trabajadas antes del cierre de nómina.\n"
    "\n"
    "**Método PRINCIPAL de registro (obligatorio para todos los empleados):**\n"
    "\n"
    "- *Kiosko de Asistencia* — Es el método oficial y obligatorio. Está ubicado en la Oficina de "
    "Administración. Todos los empleados deben registrar su entrada y salida diariamente en el Kiosko. "
    "Este es el único método que garantiza un registro presencial preciso y completo.\n"
    "\n"
    "**Métodos de CONTINGENCIA (solo si el Kiosko no está disponible — ordenados por confiabilidad):**\n"
    "\n"
    "- *Dashboard de Odoo — botón Check In / Check Out (todos los empleados con cuenta interna):* Si el "
    "empleado tiene acceso al sistema Odoo, puede marcar su asistencia directamente desde el Dashboard "
    "de RRHH usando el botón verde 'Check In' al llegar y 'Check Out' al salir. El sistema captura IP, "
    "geolocalización y hora automáticamente. Solo es necesario si no pudo usar el Kiosko ese día.\n"
    "- *Personal docente (profesores):* Si por alguna razón no pudo usar el Kiosko, la asistencia se "
    "registra automáticamente en Odoo cuando el docente ingresa la asistencia estudiantil en el sistema "
    "de Control de Asistencias (la aplicación web que usan para pasar lista a los alumnos). "
    "Horario registrado por contingencia: 7:00 AM a 1:30 PM.\n"
    "- *Personal administrativo y de mantenimiento:* Si por alguna razón no pudo usar el Kiosko, la "
    "asistencia se registra automáticamente mediante la detección de conexión al WiFi del plantel "
    "(red UEIPAB), siempre que la conexión sea de al menos 2 horas y antes de las 2:00 PM.\n"
    "\n"
    "**Preguntas frecuentes:**\n"
    "\n"
    "- *¿Qué es ese correo?* → Es un resumen quincenal de asistencia. Nuevo sistema de Odoo activo desde mayo 2026.\n"
    "- *¿Tengo que hacer clic en \"Confirmar Recepción\"?* → Sí, es importante confirmar para que RRHH sepa que lo revisaste.\n"
    "- *¿Recibiré más correos de meses anteriores?* → Sí, pronto llegarán reportes históricos desde septiembre 2025. Solo son informativos, no requieren acción.\n"
    "- *¿Puedo marcar mi asistencia desde Odoo si no usé el Kiosko?* → Sí. Si tienes cuenta interna en Odoo, ve al Dashboard de RRHH y usa el botón verde 'Check In' al llegar y 'Check Out' al salir. Solo como contingencia — el Kiosko sigue siendo el método obligatorio.\n"
    "- *No usé el Kiosko pero estuve presente* → El sistema puede haber registrado tu asistencia por contingencia (Dashboard Odoo, Control de Asistencias o WiFi). Revisa el reporte. Si aún aparece ausente, solicita la corrección desde el enlace en el correo.\n"
    "- *Soy docente y el reporte me marca ausente pero pasé lista ese día* → Si registraste la asistencia estudiantil en Control de Asistencias, debería aparecer por contingencia. Si hay un error, usa el enlace \"Solicitar Corrección de Asistencia\" en el correo del reporte.\n"
    "- *Soy docente y no usé el Kiosko ni registré en Control de Asistencias ese día* → Sin registro en ninguno de los dos sistemas no hay evidencia automática. Si estuviste presente por otro motivo, usa el enlace de corrección e indica el motivo (ej: reunión, sustitución, etc.).\n"
    "- *Tengo un error en mi registro (ausencia que no fue real, falta registro de entrada/salida)* → Solicita la corrección directamente desde el enlace **\"Solicitar Corrección de Asistencia\"** en el correo del reporte. Sin necesidad de llamar a RRHH.\n"
    "- *El sistema me marca ausente pero estuve presente* → Usa el enlace \"Solicitar Corrección de Asistencia\" en el correo. Selecciona la fecha, indica hora de llegada y salida, el motivo y envía. RRHH lo revisará y aprobará rápidamente.\n"
    "- *No tengo el correo o perdí el enlace de corrección* → Escribe a recursoshumanos@ueipab.edu.ve indicando nombre, fecha y motivo.\n"
    "- *¿Hay un portal de autogestión?* → Sí. Cada reporte que llega al correo tiene un botón directo para solicitar correcciones.\n"
    "- *¿Cuánto tiempo tarda en procesarse la corrección?* → RRHH la revisa y aprueba normalmente el mismo día. Recibirás un correo de confirmación.\n"
    "- *¿Qué pasa si no uso el Kiosko y tampoco hay contingencia?* → Aparecerás como ausente en el reporte. Debes solicitar corrección desde el enlace en el correo antes del cierre de nómina.\n"
    "- *¿A partir de cuándo afectan las ausencias a mi nómina?* → A partir del 1 de junio de 2026, las ausencias injustificadas pueden generar descuentos en nómina. Antes de esa fecha, el sistema es informativo.\n"
    "\n"
    "**Cómo responde Glenda:** Si un empleado pregunta por qué tiene ausencias, primero pregunta si usó el Kiosko ese día. Si lo usó y igual aparece ausente, orienta a recursoshumanos@ueipab.edu.ve. Si no usó el Kiosko, pregunta si tiene acceso a Odoo y usó el botón Check In del Dashboard; si tampoco, el sistema de contingencia automática (Control de Asistencias o WiFi) pudo haberlo registrado — sugiere revisar el reporte. Si no hay registro en ningún método, orienta al enlace de corrección en el email del reporte. No compartas datos de asistencia de otros empleados.\n"
    "CANALES DE ATENCIÓN HUMANA:\n"
    "- Facturación / deuda / pagos / estado de cuenta / ajustes de cobro: pagos@ueipab.edu.ve\n"
    "- Todo lo demás (soporte general, documentos, asuntos del alumno, quejas, etc.): soporte@ueipab.edu.ve\n\n"
)


@register_skill('general_inquiry')
class GeneralInquirySkill:
    """Skill: Handle unsolicited inbound WhatsApp messages.

    Triggered when an unknown phone messages the Glenda number with no active
    conversation. Glenda greets warmly, captures the person's name and inquiry,
    answers simple questions using institutional knowledge, and hands off to the
    human support team via email to soporte@ueipab.edu.ve for anything personal
    or complex.
    """

    def _get_agent_config(self, conversation):
        icp = conversation.env['ir.config_parameter'].sudo()
        return {
            'agent_name': icp.get_param('ai_agent.agent_display_name', 'Glenda'),
            'institution': icp.get_param('ai_agent.institution_display_name', 'Instituto Privado Andrés Bello'),
        }

    # ── Balance query helpers ─────────────────────────────────────────────────

    def _query_partner_balance(self, conversation, partner):
        """Return outstanding invoice breakdown for a partner (and their children)."""
        if not partner:
            return None
        Move = conversation.env['account.move'].sudo()
        partner_ids = [partner.id] + list(partner.child_ids.ids)
        invoices = Move.search([
            ('partner_id', 'in', partner_ids),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('amount_residual_signed', '>', 0),
        ], order='invoice_date asc')

        lines = []
        total = 0.0
        for inv in invoices:
            residual = float(inv.amount_residual_signed)
            if residual <= 0:
                continue
            total += residual
            # Collect non-section line names
            descriptions = [
                l.name for l in inv.invoice_line_ids
                if l.name and not l.display_type
            ]
            lines.append({
                'ref':         inv.name or '',
                'date':        inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '',
                'total_orig':  float(inv.amount_total),
                'residual':    residual,
                'description': ', '.join(descriptions[:3]) or 'Sin descripción',
                'partial':     inv.payment_state == 'partial',
            })

        return {
            'partner_name': partner.name,
            'partner_vat':  partner.vat or '',
            'total':        round(total, 2),
            'count':        len(lines),
            'lines':        lines,
        }

    def _find_partner_by_cedula(self, conversation, cedula):
        """Search res.partner by VAT (cédula). Normalises input."""
        raw = re.sub(r'[^0-9VvEeJjGgPp]', '', cedula).upper()
        if raw and not raw[0].isalpha():
            raw = 'V' + raw
        Partner = conversation.env['res.partner'].sudo()
        # Try exact, then prefix match
        partner = Partner.search([('vat', '=', raw)], limit=1)
        if not partner:
            partner = Partner.search([('vat', 'ilike', raw[-7:])], limit=1)
        return partner or None

    def _format_balance_message(self, balance, bcv_rate=None):
        """Format balance dict into a WhatsApp-friendly message."""
        if not balance or balance['count'] == 0:
            return "No tienes facturas pendientes de pago en nuestro sistema."

        name  = balance['partner_name']
        total = balance['total']
        lines = balance['lines']

        veb_line = ''
        if bcv_rate and bcv_rate > 0:
            veb_total = total * bcv_rate
            veb_line = f" (aprox. Bs. {veb_total:,.2f} a tasa BCV {bcv_rate:,.4f})"

        header = (
            f"Hola {name.split()[0].capitalize()}, aqui el detalle de tu cuenta:\n\n"
            f"*SALDO PENDIENTE: ${total:,.2f}*{veb_line}\n"
            f"Total de facturas: {len(lines)}\n"
            "─────────────────────\n"
        )

        detail_lines = []
        for inv in lines:
            partial_tag = " *(pago parcial)*" if inv['partial'] else ""
            detail_lines.append(
                f"• {inv['ref']} | {inv['date']}\n"
                f"  Monto pendiente: *${inv['residual']:,.2f}*{partial_tag}\n"
                f"  Concepto: {inv['description']}"
            )

        footer = (
            "\n─────────────────────\n"
            "Para pagar o coordinar un acuerdo, escribe a:\n"
            "pagos@ueipab.edu.ve"
        )

        return header + '\n'.join(detail_lines) + footer

    def _get_bcv_rate_from_context(self, conversation):
        """Extract current BCV rate from ir.config_parameter."""
        import json as _j
        raw = conversation.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.bcv_rate_context', '')
        if not raw:
            return 0.0
        try:
            return float(_j.loads(raw).get('current', {}).get('rate', 0))
        except Exception:
            return 0.0

    # ── BCV context helpers ───────────────────────────────────────────────────

    def _get_bcv_context(self, conversation):
        """Read BCV rate context from ir.config_parameter (populated by sync_bcv_to_odoo.py)."""
        import json as _json
        icp = conversation.env['ir.config_parameter'].sudo()
        raw = icp.get_param('ai_agent.bcv_rate_context', '')
        if not raw:
            return None
        try:
            return _json.loads(raw)
        except Exception:
            return None

    def _get_calibration_tester(self, conversation):
        """Return (employee, ack) if this conversation belongs to a calibration participant.

        Supports both WA (matched by phone digits) and Telegram (matched by partner → employee).
        """
        env = conversation.env

        # ── WA path: match enrolled wa_number by phone digits ────────────────
        if conversation.phone:
            digits = re.sub(r'\D', '', conversation.phone)
            acks = env['hr.notice.acknowledgment'].sudo().search([
                ('notice_key', '=', 'glenda_calibracion_v1'),
                ('state', '=', 'acknowledged'),
            ])
            for ack in acks:
                if re.sub(r'\D', '', ack.wa_number or '') == digits:
                    return ack.employee_id, ack

        # ── Telegram path: match via partner_id → hr.employee ───────────────
        if conversation.channel == 'telegram' and conversation.partner_id:
            partner = conversation.partner_id
            emp = env['hr.employee'].sudo().search([
                ('user_id.partner_id', '=', partner.id),
            ], limit=1)
            if emp:
                ack = env['hr.notice.acknowledgment'].sudo().search([
                    ('notice_key', '=', 'glenda_calibracion_v1'),
                    ('state', '=', 'acknowledged'),
                    ('employee_id', '=', emp.id),
                ], limit=1)
                if ack:
                    return emp, ack

        return None, None

    def get_context(self, conversation):
        cfg = self._get_agent_config(conversation)
        partner = conversation.partner_id
        partner_found = bool(
            partner and not partner.name.startswith('Consulta WhatsApp')
        )
        balance = (
            self._query_partner_balance(conversation, partner)
            if partner_found else None
        )
        calibration_employee, _ = self._get_calibration_tester(conversation)
        return {
            'partner_name':              partner.name if partner_found else '',
            'partner_vat':               (partner.vat or '') if partner_found else '',
            'partner_found_in_odoo':     partner_found,
            'balance':                   balance,
            'bcv':                       self._get_bcv_context(conversation),
            'is_calibration_tester':     bool(calibration_employee),
            'calibration_employee_name': calibration_employee.name if calibration_employee else '',
            'calibration_employee_id':   calibration_employee.id if calibration_employee else False,
            **cfg,
        }

    @staticmethod
    def _build_bcv_block(bcv):
        """Format BCV rate data into a system-prompt block."""
        if not bcv:
            return (
                "TASA BCV:\n"
                "- Información de tasa BCV no disponible en este momento. "
                "Si alguien pregunta por la tasa, indícales que consulten bcv.gob.ve "
                "o escriban a pagos@ueipab.edu.ve.\n"
            )

        current = bcv.get('current', {})
        rate    = current.get('rate', 0)
        eff_date = current.get('date', '')
        updated  = current.get('updated_at', '')

        # Format date as DD/MM/YYYY for Venezuelan audience
        def fmt_date(d):
            if not d:
                return d
            try:
                from datetime import datetime
                return datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m/%Y')
            except Exception:
                return d

        history = bcv.get('history', [])
        history_lines = '\n'.join(
            f"  {fmt_date(h['date'])}: Bs. {h['rate']:,.4f}"
            for h in history[:10]  # last 10 days inline
        )

        return (
            "TASA BCV (Banco Central de Venezuela — USD/VEB):\n"
            f"- Tasa actual: *Bs. {rate:,.4f}* por 1 USD "
            f"(efectiva {fmt_date(eff_date)}, actualizada {updated})\n"
            f"- Para convertir: multiplica el monto en USD × {rate:,.4f}\n"
            f"  Ejemplo: $218,88 × {rate:,.4f} = Bs. {218.88 * rate:,.2f}\n"
            f"- Historial reciente (últimos {len(history)} días disponibles):\n"
            + history_lines + "\n"
            "- Si alguien pide una fecha fuera del historial, indica que solo tienes "
            f"los últimos {len(history)} días y sugiere bcv.gob.ve.\n"
            "- Cuando cotices mensualidades o aranceles en bolívares, usa siempre "
            "esta tasa y aclara la fecha de referencia.\n"
        )

    def get_system_prompt(self, conversation, context):
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'Instituto Privado Andrés Bello')
        partner_name = context.get('partner_name', '')
        partner_vat  = context.get('partner_vat', '')
        partner_found = context.get('partner_found_in_odoo', False)
        balance = context.get('balance')
        bcv = context.get('bcv')

        if partner_found:
            contact_ctx = (
                f"- Contacto registrado: {partner_name}"
                + (f" | Cédula: {partner_vat}" if partner_vat else '')
                + ". Dirígete a él/ella por su nombre.\n"
            )
        else:
            contact_ctx = "- Contacto NO registrado en el sistema. Si no dice su nombre, pregúntaselo de forma natural.\n"

        # Balance context block
        if balance and balance['count'] > 0:
            bal_total = balance['total']
            bal_count = balance['count']
            balance_ctx = (
                f"\nSALDO EN SISTEMA (dato interno — úsalo solo si el contacto pregunta):\n"
                f"- {partner_name} tiene {bal_count} factura(s) pendiente(s) por un total de "
                f"*${bal_total:,.2f}*.\n"
                f"- Si el contacto pregunta su saldo o deuda, responde directamente con este dato "
                f"e incluye ACTION:QUERY_BALANCE:FOUND al final para enviarle el desglose completo.\n"
            )
        elif balance and balance['count'] == 0:
            balance_ctx = (
                f"\nSALDO EN SISTEMA: {partner_name} no tiene facturas pendientes registradas.\n"
                f"- Si el contacto pregunta si debe algo, puedes informarle que su cuenta está al día.\n"
            )
        else:
            balance_ctx = (
                "\nSALDO: Contacto no identificado. Si pregunta por su saldo o deuda:\n"
                "- Pídele su número de cédula (ej: V-12345678).\n"
                "- Cuando lo proporcione, incluye ACTION:QUERY_BALANCE:V-12345678 al final de tu "
                "respuesta (reemplaza con la cédula real).\n"
            )

        flyer_list = "\n".join(
            f"  - {key}: {desc}" for key, (_, desc) in _FLYERS.items()
        )

        calibration_block = ''
        if context.get('is_calibration_tester'):
            emp_name = context.get('calibration_employee_name', 'Empleado/a')
            first = emp_name.split()[0].capitalize()
            calibration_block = (
                f"\n⚙️ MODO PRUEBA INTERNA — EMPLEADO TESTER:\n"
                f"- Estás hablando con {first} ({emp_name}), empleado/a de {institution} "
                f"que participa en el Programa de Calibración de Glenda.\n"
                f"- Puedes ser completamente transparente: confirmar que eres una IA, "
                f"reconocer limitaciones, explicar cómo funciona el sistema.\n"
                f"- Si {first} menciona 'tengo una sugerencia', 'mejorar', 'debería poder', "
                f"'no entendiste', 'fallo en', o similares, captura la sugerencia al final "
                f"de tu respuesta con el marcador interno:\n"
                f"  ACTION:LOG_FEEDBACK:categoria|texto_de_la_sugerencia\n"
                f"  Categorías válidas: flujo, respuesta, idioma, asistencia, conocimiento, tecnico, otro\n"
                f"  Ejemplo: ACTION:LOG_FEEDBACK:flujo|Debería poder retomar una conversación anterior sin empezar de cero\n"
                f"- Agradece siempre la sugerencia calurosamente.\n"
                f"- Si {first} quiere probar un escenario específico (ej: 'actúa como si fuera un representante'), "
                f"entra en ese rol naturalmente y demuestra tus capacidades.\n"
                f"- ACTION:LOG_FEEDBACK es un marcador interno. {first} NO lo verá.\n\n"
            )

        return (
            f"Eres {agent_name}, asistente virtual del {institution}, ubicada en Venezuela.\n\n"
            + calibration_block
            + _INSTITUTIONAL_KNOWLEDGE
            + self._build_bcv_block(bcv) + "\n"
            + balance_ctx + "\n"
            + "CONTEXTO:\n"
            "- Esta persona escribió directamente a este número de WhatsApp sin que nosotros la hayamos contactado.\n"
            + contact_ctx
            + "\nFLYERS DISPONIBLES (imágenes informativas que puedes enviar):\n"
            + flyer_list + "\n"
            + "\nINSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano, cálida y profesionalmente.\n"
            "- Salúdala y preséntate brevemente como asistente del colegio.\n"
            "- Entiende su consulta. Responde preguntas generales con el conocimiento institucional que tienes "
            "(medios de pago, mensualidades, fechas, información general del colegio).\n"
            "PRIORIDAD AL RESPONDER SOBRE TARIFAS E INSCRIPCION:\n"
            "- SIEMPRE ofrece primero la PROMOCION DE INSCRIPCION ANTICIPADA (mayo - 31 julio 2026): "
            "inscripcion $187,51 + mensualidad septiembre $197,38 (tarifa actual, NO la nueva de $218,88). "
            "Requisito: 2025-2026 completamente saldado.\n"
            "- DESPUES menciona la nueva mensualidad base $218,88 desde septiembre con descuentos hermanos.\n"
            "- Menciona siempre Cashea como opcion de pago (confirmar enlace con pagos@ueipab.edu.ve).\n"
            "- Si la persona pregunta por inscripciones, mensualidad, cursos extracurriculares, métodos de pago "
            "u otros temas cubiertos por un flyer disponible, añade ACTION:SEND_FLYER:clave al final de tu "
            "respuesta (usa exactamente la clave de la lista de flyers). Solo un flyer por respuesta.\n"
            "  Ejemplo: ACTION:SEND_FLYER:inscripcion\n"
            "- Si la consulta es sobre su SALDO, DEUDA o FACTURAS PENDIENTES:\n"
            "  * Si el contacto ya está identificado y el SALDO EN SISTEMA indica facturas pendientes: "
            "infórmale el total y añade ACTION:QUERY_BALANCE:FOUND para que reciba el desglose.\n"
            "  * Si el contacto ya está identificado y no tiene saldo: dile que está al día.\n"
            "  * Si el contacto NO está identificado: pídele su cédula. Cuando la proporcione, "
            "incluye ACTION:QUERY_BALANCE:V-XXXXXXXX (con su cédula real). No inventes datos.\n"
            "  * Después de mostrar el saldo, si quiere pagar o negociar, usa ACTION:HANDOFF:nombre|resumen|billing.\n"
            "  * IMPORTANTE: Nunca muestres el saldo de una persona a otra. Solo informa al contacto identificado.\n"
            "- Si la consulta es sobre facturación, deuda, saldo, estado de cuenta, ajuste de cobro o pagos "
            "pendientes y NO puedes resolverla con el saldo disponible: infórmale que la canalizarás "
            "con el equipo de Pagos y Facturación (pagos@ueipab.edu.ve). Usa ACTION:HANDOFF con ruta 'billing'.\n"
            "- Si la consulta requiere acceso a otros datos personales (documentos, trámites, asuntos del "
            "alumno, quejas, etc.): infórmale que la conectarás con el equipo de soporte "
            "(soporte@ueipab.edu.ve). Usa ACTION:HANDOFF con ruta 'support'.\n"
            "COTIZACIÓN MULTI-ALUMNO:\n"
            "- Si el representante menciona más de 1 hijo O pregunta por costo total o descuentos, "
            "prepara una cotización detallada.\n"
            "- Si no indicó cuántos alumnos tiene, pregúntalo antes de cotizar.\n"
            "- La cotización debe incluir CUATRO secciones en texto plano (sin markdown):\n"
            "  1. MENSUALIDAD por alumno con descuento hermano aplicado + total regular + total con pronto pago\n"
            "  2. INSCRIPCIÓN: $187,51 por alumno en promoción (sin descuento por hermano), total\n"
            "  3. COSTOS ANUALES: $101,58 por alumno (seguro $30,58 + guía inglés $25 + olimpiadas $10 + enciclopedia $36, aplica a todos los niveles). Total.\n"
            "  4. TOTAL PRIMER MES: suma de inscripción + costos anuales + mensualidad del primer mes\n"
            "     (mostrar opción regular y opción con pronto pago)\n"
            "- Formato sugerido:\n"
            "  MENSUALIDAD (desde sep 2026):\n"
            "  1er alumno (5% dto.): $207,94/mes\n"
            "  2do alumno (8% dto.): $201,37/mes\n"
            "  Total mensual: $409,31 | Con pronto pago: $388,84\n"
            "  INSCRIPCION (pago unico, promo): $187,51 x 2 = $375,02\n"
            "  COSTOS ANUALES (pago unico, sin desc.): $101,58 x 2 = $203,16\n"
            "  TOTAL PRIMER MES: $987,49 | Con pronto pago: $967,02\n"
            "- Los costos opcionales (Competencia Kurios, MOA, traslados) NO se incluyen en la cotización estándar.\n"
            "- REQUISITO PREVIO: antes de presentar la cotización, si el representante tiene saldo pendiente del año en curso, indícale que primero debe regularizar con pagos@ueipab.edu.ve — no puede inscribirse hasta tener 2025-2026 completamente saldado.\n"
            "- Luego de presentar la cotización, haz el handoff a 'billing' con resumen estructurado. "
            "Ejemplo: ACTION:HANDOFF:Ana Perez|Cotizacion 2 alumnos: mens $409,31 (PP $388,84) insc $375,02 extras anuales $203,16 primer mes $987,49|billing\n"
            "TARIFAS VIGENTES vs PRÓXIMAS:\n"
            "- Si preguntan por costos ACTUALES (antes de septiembre 2026): inscripción $197,38, mensualidad $197,38 (pronto pago $162,39).\n"
            "- Si preguntan por costos del PRÓXIMO AÑO ESCOLAR o a partir de septiembre 2026: inscripción en promoción $187,51 (hasta el 31 jul), mensualidad desde sep $207,94 para el 1er alumno (5% dto. hermano) con pronto pago $197,54. Orientar a pagos@ueipab.edu.ve para confirmar tarifas definitivas.\n"
            "- Si preguntan si el precio subirá: sí, habrá un ajuste a partir del 1 de septiembre de 2026. Informar con claridad y sin alarmar.\n"
            "MANEJO ESPECIAL FUERZA LABORAL INDUSTRIA (PDVSA / Petropiar / otras Industrias):\n"
            "- Si alguien se identifica como trabajador(a) del sector industria (PDVSA, Petropiar u otra) "
            "y es un NUEVO prospecto (no inscrito en 2025-2026): infórmale con claridad y cordialidad que "
            "el descuento del 35% en modalidad de crédito que existía en períodos anteriores ha cesado "
            "a partir del 1° de septiembre de 2026. El pago es 100% por adelantado a tasa BCV, igual que "
            "cualquier otra familia. Recomienda escribir a pagos@ueipab.edu.ve. "
            "Usa ACTION:HANDOFF con ruta 'billing'.\n"
            "- Si es una familia YA INSCRITA (período 2025-2026) que expresa dificultad económica, "
            "preocupación o amenaza de no poder continuar: respóndele con MUCHA empatía y calma. "
            "Hazle saber que el colegio comprende su situación y valora a su familia. Recuérdale que "
            "tiene hasta el lunes 08 de junio de 2026 a las 12:30 p.m. para comunicar su decisión por "
            "escrito a pagos@ueipab.edu.ve. Menciona que si su alumno tiene méritos académicos o "
            "deportivos excepcionales, puede solicitar revisión de un 'Caso Especial' individual via email. "
            "Invítala a comunicarse con pagos@ueipab.edu.ve antes de tomar cualquier decisión. "
            "No presiones ni repitas la política fríamente. "
            "Usa ACTION:HANDOFF con ruta 'pdvsa_retention'.\n"
            "- Si preguntan por la FECHA LÍMITE: es el 08 de junio de 2026 a las 12:30 p.m. "
            "Sin respuesta antes de esa fecha, el sistema asume aceptación de las nuevas condiciones.\n"
            "- Si preguntan si su alumno califica como CASO ESPECIAL: los criterios son excelente "
            "rendimiento académico, atleta con medallas nacionales, músico activo del Sistema de "
            "Orquestas Juveniles, o habilidades destacadas reconocidas. Orientar a pagos@ueipab.edu.ve "
            "para solicitud individual. No hay excepciones generales.\n"
            "- Si preguntan por el aumento de tarifas 2026-2027: se proyecta un ajuste de entre 20% y "
            "34% sobre la tarifa base. Las cifras definitivas aún no están confirmadas. "
            "Orientar a pagos@ueipab.edu.ve para más detalles.\n"
            "- Cuando tengas el nombre de la persona Y el tema de su consulta, o luego de máximo 2 intercambios, "
            "finaliza con: ACTION:HANDOFF:nombre|resumen_de_la_consulta|ruta\n"
            "  El nombre va primero, luego el resumen, luego la ruta (billing o support). Sin saltos de línea.\n"
            "  Ejemplo facturación: ACTION:HANDOFF:María García|Consulta deuda mensualidad octubre|billing\n"
            "  Ejemplo soporte:     ACTION:HANDOFF:Carlos López|Solicitud de constancia de estudios|support\n"
            "- Si no logras obtener el nombre, usa 'Desconocido' en el marcador.\n"
            "MENSAJES DE AUDIO:\n"
            "- Puedes procesar mensajes de voz: cuando el cliente envía un audio, se transcribe automáticamente antes de llegar a ti.\n"
            "- Si el mensaje comienza con '[Audio transcrito]:', ese es el contenido del audio transcrito. Trátalo exactamente igual que texto normal; la transcripción puede tener pequeños errores ortográficos — interpreta el significado con contexto. Si el cliente pregunta si escuchaste su audio, confirma que sí procesaste su mensaje de voz.\n"
            "- Si el mensaje es '[audio sin transcripción]', informa amablemente que no pudiste procesar ese audio en particular y pide que escriba su consulta.\n"
            "IDENTIFICACIÓN DEL INTERLOCUTOR:\n"
            "- El número de WhatsApp puede estar registrado a nombre del representante (titular de la cuenta), "
            "pero quien escribe puede ser otra persona (esposo/a, familiar, etc.).\n"
            "- Si alguien se identifica como una persona diferente al titular "
            "(ej: 'soy Miguel, el esposo de Mariana'), actualiza quién habla: dirígete a MIGUEL, no a Mariana.\n"
            "- Cuando el interlocutor narra una situación personal en primera persona "
            "(enfermedad, ausencia, inconveniente), asume que habla de sí mismo — NO del titular — "
            "salvo que lo aclare explícitamente.\n"
            "- Ejemplo correcto: si Miguel dice 'he estado enfermo', desearle recuperación a MIGUEL, "
            "no a Mariana.\n"
            "REGLAS DE COMUNICACIÓN (basadas en retroalimentación de usuarios):\n"
            "- Un solo mensaje por turno: consolida toda tu respuesta en un único mensaje. Nunca envíes dos mensajes seguidos sobre el mismo tema.\n"
            "- DESPEDIDA — REGLA ESTRICTA: cuando el cliente envíe cualquiera de estas frases o similares: "
            "'gracias', 'hasta luego', 'hasta pronto', 'feliz día', 'buenas noches', 'nos vemos', 'adiós', "
            "'chao', 'no es todo', 'eso es todo', 'listo', 'ya es todo', 'muchas gracias', 'mil gracias', "
            "'que tengas', 'que tenga', 'igualmente' — responde con UNA SOLA LÍNEA de cierre y NADA MÁS. "
            "PROHIBIDO: añadir preguntas de seguimiento, ofrecer más ayuda, repetir el saludo, ni enviar "
            "mensajes adicionales. La conversación termina ahí.\n"
            "  ❌ MAL: '¡Hasta pronto! ¿Puedo ayudarte en algo más hoy? ¡Que tengas un excelente día! ¡Cuídate mucho!'\n"
            "  ✅ BIEN: '¡Hasta pronto!'\n"
            "  ❌ MAL: 'Fue un placer. Si necesitas algo más, aquí estaré. ¡Hasta luego! ¡Que tengas un gran día!'\n"
            "  ✅ BIEN: '¡Con mucho gusto! ¡Hasta luego!'\n"
            "- No insistas después del cierre: si el cliente no ha dicho explícitamente adiós pero el tema claramente terminó (responde 'ok', 'listo', 'entendido', 'perfecto'), responde brevemente y espera — no generes más preguntas.\n"
            "- No uses emojis. No reveles que eres un sistema automático a menos que pregunten directamente.\n"
            "- NUNCA menciones el nombre del propietario, dueño o accionista de la institución. "
            "Si preguntan por el 'dueño' o 'propietario', responde únicamente con las autoridades académicas "
            "(Director: Prof. Arcides Arzola, Sub-directora: Prof. Norka La Rosa, Sub-director: Prof. David Hernández) "
            "y el contacto soporte@ueipab.edu.ve. Puedes mencionar a la fundadora histórica Carmen Violeta Mata de Perdomo si es relevante.\n"
            "- IMPORTANTE: ACTION:SEND_FLYER, ACTION:HANDOFF, ACTION:NOTIFY_ABSENCE y ACTION:SCHOOL_ACCOUNT_HELP son comandos internos. "
            "El cliente NO los ve. Inclúyelos siempre al final de la respuesta cuando apliquen.\n"
            "AYUDA CON CUENTA ESCOLAR (correo @ueipab.edu.ve y acceso Akdemia):\n"
            "- Si un representante menciona que olvidó el correo institucional de su hijo/a (@ueipab.edu.ve) "
            "o no puede acceder a la plataforma Akdemia (olvido de contraseña, cambio de dispositivo, etc.), DEBES:\n"
            "  1. Si solo necesita recuperar contraseña y ya tiene el correo: entregar directamente el enlace "
            "https://edge.akdemia.com/login#resetPasswordModal y ofrecer soporte en soporte@ueipab.edu.ve. "
            "NO se requiere ACTION para este caso.\n"
            "  2. Si no recuerda el correo institucional:\n"
            "     a. Pedir su número de cédula venezolana (para verificar identidad — OBLIGATORIO)\n"
            "     b. Pedir el nombre completo del alumno/a y su grado o año\n"
            "     c. Una vez obtenidos ambos datos, incluir al final de tu respuesta:\n"
            "        ACTION:SCHOOL_ACCOUNT_HELP:cedula|nombre_alumno|grado\n"
            "     d. En el mismo mensaje: indicar que el sistema verificará los datos y responderá con "
            "el correo institucional; también mencionar el enlace de recuperación de contraseña Akdemia: "
            "https://edge.akdemia.com/login#resetPasswordModal\n"
            "     e. Informar que el equipo de soporte recibirá una notificación para seguimiento\n"
            "  SEGURIDAD: NUNCA emitas ACTION:SCHOOL_ACCOUNT_HELP sin haber pedido y recibido la cédula. "
            "Si el representante no proporciona cédula, no puedes continuar con la verificación.\n"
            "  Ejemplo: si la madre de Juan Pérez de 3er año olvidó el correo y da cédula V-12345678:\n"
            "  '...verificaremos los datos. Enlace de recuperación: https://edge.akdemia.com/login#resetPasswordModal "
            "\\n\\nACTION:SCHOOL_ACCOUNT_HELP:V-12345678|Juan Pérez|3er año'\n"
            "NOTIFICACIÓN DE AUSENCIAS ESCOLARES:\n"
            "- Si el representante notifica que su hijo/a no asistirá o no asistió a clases "
            "(enfermedad, reposo médico, cita médica u otro motivo), DEBES:\n"
            "  1. Confirmar que tienes: nombre del alumno, año/grado (y sección si la sabe), motivo\n"
            "  2. Si falta información esencial, pregunta de forma natural antes de registrar\n"
            "  3. Una vez confirmados los datos, incluir al final:\n"
            "     ACTION:NOTIFY_ABSENCE:nombre_alumno|grado_raw|motivo\n"
            "  4. Informar al representante que la ausencia quedó registrada y será coordinada con el equipo docente\n"
            "- Ejemplo de respuesta: 'Recibido ✅ Hemos registrado la ausencia de Pedro Martínez de 2do año "
            "por fiebre. Coordinaremos con el personal docente para el manejo de sus actividades. "
            "¡Que se mejore pronto! 🙏\\n\\nACTION:NOTIFY_ABSENCE:Pedro Martínez|2do año|fiebre'\n"
        )

    def get_reminder_message(self, conversation, context, reminder_count):
        """Return a gentle follow-up message for stale general_inquiry conversations."""
        from . import get_ve_greeting
        saludo = get_ve_greeting()
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'Instituto Privado Andrés Bello')
        if reminder_count == 0:
            return (
                f"{saludo}! Soy {agent_name} del {institution}. "
                "¿Pude ayudarte con tu consulta? Si tienes alguna pregunta adicional, "
                "con gusto te atiendo."
            )
        return (
            f"{saludo}. Te escribo por última vez desde {institution}. "
            "Si necesitas información sobre el colegio en otro momento, "
            "no dudes en escribirnos. ¡Hasta pronto!"
        )

    def get_greeting(self, conversation, context):
        """Fallback greeting if conversation is started manually via action_start."""
        saludo = get_ve_greeting()
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'Instituto Privado Andrés Bello')
        return (
            f"{saludo}! Le saluda {agent_name}, asistente virtual del {institution}. "
            "Con gusto le atiendo. ¿En qué le puedo ayudar?"
        )

    def _extract_visible_text(self, ai_response):
        """Strip ACTION markers from the response before sending to customer."""
        text = re.sub(r'ACTION:\w+[^\n]*', '', ai_response)
        return text.strip()

    def _get_base_url(self, conversation):
        return conversation.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.flyer_base_url', 'https://dev.ueipab.edu.ve/flyers'
        )

    def _handle_balance_action(self, conversation, ai_response, context):
        """Resolve ACTION:QUERY_BALANCE and return formatted balance message or None."""
        bal_match = re.search(
            r'ACTION:QUERY_BALANCE:(FOUND|[VvEeJjGgPp]?-?\d+)',
            ai_response, re.MULTILINE
        )
        if not bal_match:
            return None

        token = bal_match.group(1).strip().upper()
        partner = None

        if token == 'FOUND':
            # Use already-identified partner from conversation
            p = conversation.partner_id
            if p and not p.name.startswith('Consulta WhatsApp'):
                partner = p
        else:
            partner = self._find_partner_by_cedula(conversation, token)

        if not partner:
            return (
                "No encontre una cuenta registrada con esa cédula en nuestro sistema. "
                "Verifica el número e intenta nuevamente, o escribe a pagos@ueipab.edu.ve."
            )

        balance = self._query_partner_balance(conversation, partner)
        bcv_rate = self._get_bcv_rate_from_context(conversation)
        return self._format_balance_message(balance, bcv_rate)

    def _handle_log_feedback(self, conversation, ai_response, context):
        """Create ai.agent.feedback record if ACTION:LOG_FEEDBACK marker is present."""
        match = re.search(
            r'ACTION:LOG_FEEDBACK:(\w+)\|(.+?)(?=\nACTION:|\Z)',
            ai_response, re.MULTILINE | re.DOTALL
        )
        if not match:
            return
        category = match.group(1).strip().lower()
        suggestion = match.group(2).strip()
        try:
            conversation.env['ai.agent.feedback'].sudo().log_from_conversation(
                conversation, category, suggestion
            )
        except Exception as e:
            _logger.error("Failed to log calibration feedback: %s", e)

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for ACTION:SEND_FLYER, ACTION:QUERY_BALANCE, ACTION:LOG_FEEDBACK,
        ACTION:HANDOFF and ACTION:NOTIFY_ABSENCE markers."""
        # Log calibration feedback if present (before stripping markers)
        if context.get('is_calibration_tester'):
            self._handle_log_feedback(conversation, ai_response, context)

        # Check for balance query — resolve and append to visible text before other actions
        balance_msg = self._handle_balance_action(conversation, ai_response, context)

        # Check for absence notification
        absence_match = re.search(
            r'ACTION:NOTIFY_ABSENCE:([^|\n]+)\|([^|\n]+)\|(.+?)(?:\n|ACTION:|$)',
            ai_response, re.MULTILINE
        )
        absence_data = None
        if absence_match:
            absence_data = {
                'student_name': absence_match.group(1).strip(),
                'grade_raw':    absence_match.group(2).strip(),
                'reason':       absence_match.group(3).strip(),
            }
            _logger.info("Absence notification from Glenda: %s", absence_data)

        # Check for school account help request (forgot student email / Akdemia access)
        school_match = re.search(
            r'ACTION:SCHOOL_ACCOUNT_HELP:([^|\n]+)\|([^|\n]+)\|([^\n]+)',
            ai_response, re.MULTILINE
        )
        school_account_data = None
        if school_match:
            school_account_data = {
                'cedula':       school_match.group(1).strip(),
                'student_name': school_match.group(2).strip(),
                'grade_raw':    school_match.group(3).strip(),
            }
            _logger.info("School account help from Glenda: %s", school_account_data)

        # Check for flyer send request
        flyer_match = re.search(r'ACTION:SEND_FLYER:(\w+)', ai_response, re.MULTILINE)
        flyer_key = flyer_match.group(1).strip() if flyer_match else None
        if flyer_key and flyer_key not in _FLYERS:
            _logger.warning("general_inquiry: unknown flyer key '%s', ignoring", flyer_key)
            flyer_key = None

        # Check for handoff
        handoff_match = re.search(
            r'ACTION:HANDOFF:([^|\n]+)\|([^|\n]+)(?:\|(\w+))?$',
            ai_response,
            re.MULTILINE,
        )
        if handoff_match:
            captured_name = handoff_match.group(1).strip()
            captured_summary = handoff_match.group(2).strip()
            route = (handoff_match.group(3) or 'support').strip().lower()
            if route not in ('billing', 'support', 'pdvsa_retention'):
                route = 'support'
            visible_text = self._extract_visible_text(ai_response)
            team = 'Pagos y Facturación' if route == 'billing' else 'Soporte'
            result = {
                'resolve': True,
                'farewell_message': visible_text or ai_response,
                'summary': f'Transferido a {team}: {captured_name} — {captured_summary}',
                'resolution_data': {
                    'action': 'handoff',
                    'captured_name': captured_name,
                    'summary': captured_summary,
                    'route': route,
                    'flyer_key': flyer_key,
                },
            }
            return result

        visible_text = self._extract_visible_text(ai_response)
        # If balance query resolved, append the breakdown as a second message
        if balance_msg:
            final_text = visible_text or ai_response
            result = {'message': final_text, 'balance_message': balance_msg}
        else:
            result = {'message': visible_text or ai_response}
        if flyer_key:
            result['flyer_key'] = flyer_key
        if absence_data:
            result['notify_absence'] = absence_data
        if school_account_data:
            result['school_account_help'] = school_account_data
        return result

    def send_flyer(self, conversation, flyer_key):
        """Send a flyer image via WhatsApp for the given key. Skipped on Telegram."""
        if flyer_key not in _FLYERS:
            return
        if conversation.channel != 'whatsapp':
            _logger.info("Flyer '%s' skipped — channel=%s (WA only)", flyer_key, conversation.channel)
            return
        filename, description = _FLYERS[flyer_key]
        base_url = self._get_base_url(conversation)
        url = _get_flyer_url(base_url, filename)
        dry_run = conversation.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.dry_run', 'True').lower() == 'true'
        if dry_run:
            _logger.info("DRY_RUN: would send flyer '%s' to %s: %s", flyer_key, conversation.phone, url)
            return
        wa_service = conversation.env['ai.agent.whatsapp.service']
        try:
            wa_service.send_media(conversation.phone, url)
            _logger.info("Flyer '%s' sent to %s", flyer_key, conversation.phone)
        except Exception as e:
            _logger.error("Failed to send flyer '%s' to %s: %s", flyer_key, conversation.phone, e)

    def on_resolve(self, conversation, resolution_data):
        """Send handoff email to soporte@ueipab.edu.ve with full transcript."""
        if resolution_data.get('action') != 'handoff':
            return

        captured_name = resolution_data.get('captured_name', 'Desconocido')
        summary = resolution_data.get('summary', 'Sin descripción')
        route = resolution_data.get('route', 'support')
        phone = conversation.phone
        if route == 'pdvsa_retention':
            to_email = 'pagos@ueipab.edu.ve'
            team_name = 'equipo de Pagos y Facturación'
        elif route == 'billing':
            to_email = 'pagos@ueipab.edu.ve'
            team_name = 'equipo de Pagos y Facturación'
        else:
            to_email = 'soporte@ueipab.edu.ve'
            team_name = 'equipo de Soporte'

        partner = conversation.partner_id
        partner_found = bool(partner and not partner.name.startswith('Consulta WhatsApp'))
        partner_info = f"Sí — {partner.name}" if partner_found else "No encontrado en el sistema"

        # Build transcript
        transcript_rows = []
        for msg in conversation.agent_message_ids.sorted('create_date'):
            role = 'Cliente' if msg.direction == 'inbound' else 'Glenda'
            body = (msg.body or '').strip()
            if body:
                transcript_rows.append(
                    f'<tr style="vertical-align:top;">'
                    f'<td style="padding:3px 10px 3px 0;font-weight:bold;white-space:nowrap;">{role}:</td>'
                    f'<td style="padding:3px 0;">{body}</td></tr>'
                )
        transcript_html = (
            '<table style="border-collapse:collapse;font-size:13px;">'
            + ''.join(transcript_rows)
            + '</table>'
            if transcript_rows else '<i>(sin mensajes)</i>'
        )

        if route == 'pdvsa_retention':
            subject = f"[URGENTE - Glenda] Familia PDVSA — Riesgo de no renovación — {captured_name}"
            body_html = f"""
<p style="color:#c0392b;font-weight:bold;">⚠️ ATENCIÓN URGENTE — Riesgo de no renovación de matrícula</p>
<p>Hola {team_name},</p>
<p>Una familia <strong>ya inscrita en el período 2025-2026</strong>, identificada como empleada de <strong>PDVSA / Petropiar</strong>,
ha expresado a través de WhatsApp dificultades económicas ante la descontinuación del beneficio del 35% de crédito anticipado.</p>
<p>Puede haber riesgo de que esta familia <strong>no continúe en el período 2026-2027</strong>.
Se les invitó a conversar con el Director para evaluar su situación particular.</p>
<table style="border-collapse:collapse;margin:10px 0;">
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Teléfono:</td><td>{phone}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Nombre indicado:</td><td>{captured_name}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Contacto en Odoo:</td><td>{partner_info}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Resumen:</td><td>{summary}</td></tr>
</table>
<p><strong>Acción requerida:</strong> Contactar a esta familia a la brevedad y coordinar con el Director una reunión para evaluar su caso.</p>
<p><b>Transcripción de la conversación:</b></p>
<div style="background:#f5f5f5;padding:12px;border-radius:4px;">
{transcript_html}
</div>
<p>Saludos,<br/><b>Glenda — Asistente Virtual</b><br/>Instituto Privado Andrés Bello</p>
"""
        else:
            is_quotation = 'cotizacion' in summary.lower() or 'cotización' in summary.lower()
            if is_quotation:
                subject = f"[Glenda] Cotización solicitada — WhatsApp {phone} — {captured_name}"
                intro_html = (
                    "<p>Un prospecto solicitó una <strong>cotización por número de alumnos</strong> "
                    "a través de WhatsApp. Glenda generó la cotización en la conversación. "
                    "El detalle se encuentra en el resumen y en la transcripción.</p>"
                )
            else:
                subject = f"[Glenda] Consulta entrante — WhatsApp {phone}"
                intro_html = (
                    "<p>Un cliente se comunicó a través de WhatsApp al número de Glenda "
                    "y necesita atención personalizada.</p>"
                )
            body_html = f"""
<p>Hola {team_name},</p>
{intro_html}
<table style="border-collapse:collapse;margin:10px 0;">
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Teléfono:</td><td>{phone}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Nombre indicado:</td><td>{captured_name}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Contacto en Odoo:</td><td>{partner_info}</td></tr>
  <tr><td style="padding:4px 14px 4px 0;font-weight:bold;">Resumen:</td><td>{summary}</td></tr>
</table>
<p><b>Transcripción de la conversación:</b></p>
<div style="background:#f5f5f5;padding:12px;border-radius:4px;">
{transcript_html}
</div>
<p style="margin-top:14px;">Por favor, comuníquese con el cliente para atender su solicitud.</p>
<p>Saludos,<br/><b>Glenda — Asistente Virtual</b><br/>Instituto Privado Andrés Bello</p>
"""
        conversation._send_escalation_email({
            'to': to_email,
            'subject': subject,
            'body_html': body_html,
        })
