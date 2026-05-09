import logging
import re

from . import register_skill, get_ve_greeting

_logger = logging.getLogger(__name__)

# Flyers available to send via WhatsApp.
# key → (filename, short description for Claude's reference)
_FLYERS = {
    'inscripcion':          ('inscripcion.png',          'Inscripciones abiertas año escolar 2026-2027 — $197.38/año, 17.72% descuento hasta el 1 de mayo'),
    'pronto_pago':          ('pronto_pago.png',          'Pronto pago: mensualidad congelada a $162.39 si pagas en los primeros 10 días del mes'),
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
    "- Inscripción (tarifa vigente hasta agosto 2026): $197,38\n"
    "- Mensualidad (tarifa vigente hasta agosto 2026): $197,38 | Pronto pago: $162,39 (10 primeros días de cada mes)\n"
    "TARIFAS A PARTIR DEL 1 DE SEPTIEMBRE DE 2026 (inicio año escolar 2026-2027) [PROYECTADAS]:\n"
    "- Inscripción: $264,48\n"
    "- Mensualidad: $264,48 | Pronto pago (primeros 10 días del mes): $241,16 (descuento 8,816%)\n"
    "- Estas tarifas son proyectadas. Si el representante quiere confirmar o tiene dudas sobre su caso particular, orientar a pagos@ueipab.edu.ve\n"
    "COSTOS ANUALES ÚNICOS (pago único por año escolar, sin descuento, por alumno):\n"
    "    Seguro escolar: $15\n"
    "    Enciclopedia de Inglés: $30\n"
    "    Olimpiadas Recreativas de Lengua y Matemáticas: $10\n"
    "    Subtotal estándar por alumno: $55\n"
    "    Enciclopedia digital bachillerato: $36 (solo alumnos en nivel bachillerato)\n"
    "COSTOS OPCIONALES / CONDICIONALES (NO incluir en cotización estándar):\n"
    "    Competencia Kurios: $10 (solo si el alumno es seleccionado por el colegio)\n"
    "    Competencia MOA inglés: $25 (solo si el alumno es seleccionado por el colegio)\n"
    "    Encuentros Regionales/Nacionales: traslados y logística a cargo de los padres\n"
    "DESCUENTOS POR HERMANOS (aplica sobre mensualidad):\n"
    "- 1er alumno: tarifa completa (sin descuento)\n"
    "- 2do alumno: 5% de descuento sobre mensualidad\n"
    "- 3er alumno: 6% de descuento sobre mensualidad\n"
    "- 4to alumno en adelante: 7% de descuento sobre mensualidad\n"
    "- Los descuentos de hermano y pronto pago se acumulan (el pronto pago se aplica sobre la mensualidad ya descontada)\n"
    "- Inscripción: precio completo por alumno, sin descuento por hermano\n"
    "TABLA DE MENSUALIDAD POR ALUMNO (tarifas Sep 2026, proyectadas):\n"
    "  1er alumno: mensualidad $264,48 | pronto pago $241,16\n"
    "  2do alumno: mensualidad $251,26 | pronto pago $229,11\n"
    "  3er alumno: mensualidad $248,61 | pronto pago $226,69\n"
    "  4to alumno en adelante: mensualidad $245,97 | pronto pago $224,28\n"
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
    "PROYECCIONES MATRÍCULA 2026-2027 (para familias industria y general):\n"
    "- Se estima un ajuste de la matrícula base de entre 20% y 34%, calculado sobre inflación, salarios del sector privado y riesgo país. Tarifas definitivas se presentarán ante el Comité de Contraloría.\n"
    "- Costos NO incluidos en la matrícula: seguro escolar, olimpiadas académicas, guías de texto/inglés, concursos nacionales (robótica, química, etc.) y eventos externos — se pagan según participación del alumno.\n"
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
    "- Tras realizar el pago, notificar a: pagos@ueipab.edu.ve\n"
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

    def get_context(self, conversation):
        cfg = self._get_agent_config(conversation)
        partner = conversation.partner_id
        partner_found = bool(
            partner and not partner.name.startswith('Consulta WhatsApp')
        )
        return {
            'partner_name': partner.name if partner_found else '',
            'partner_found_in_odoo': partner_found,
            **cfg,
        }

    def get_system_prompt(self, conversation, context):
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'Instituto Privado Andrés Bello')
        partner_name = context.get('partner_name', '')
        partner_found = context.get('partner_found_in_odoo', False)

        contact_ctx = (
            f"- Este contacto está registrado en el sistema como: {partner_name}. Puedes dirigirte a él/ella por su nombre.\n"
            if partner_found
            else "- Este contacto NO está registrado en el sistema. Si no dice su nombre, pregúntaselo de forma natural.\n"
        )

        flyer_list = "\n".join(
            f"  - {key}: {desc}" for key, (_, desc) in _FLYERS.items()
        )

        return (
            f"Eres {agent_name}, asistente virtual del {institution}, ubicada en Venezuela.\n\n"
            + _INSTITUTIONAL_KNOWLEDGE
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
            "- Si la persona pregunta por inscripciones, mensualidad, cursos extracurriculares, métodos de pago "
            "u otros temas cubiertos por un flyer disponible, añade ACTION:SEND_FLYER:clave al final de tu "
            "respuesta (usa exactamente la clave de la lista de flyers). Solo un flyer por respuesta.\n"
            "  Ejemplo: ACTION:SEND_FLYER:inscripcion\n"
            "- Si la consulta es sobre facturación, deuda, saldo, estado de cuenta, ajuste de cobro o pagos "
            "pendientes: infórmale que la canalizarás con el equipo de Pagos y Facturación "
            "(pagos@ueipab.edu.ve) que la atenderá a la brevedad. Usa ACTION:HANDOFF con ruta 'billing'.\n"
            "- Si la consulta requiere acceso a otros datos personales (documentos, trámites, asuntos del "
            "alumno, quejas, etc.): infórmale que la conectarás con el equipo de soporte "
            "(soporte@ueipab.edu.ve). Usa ACTION:HANDOFF con ruta 'support'.\n"
            "COTIZACIÓN MULTI-ALUMNO:\n"
            "- Si el representante menciona más de 1 hijo O pregunta por costo total o descuentos, "
            "prepara una cotización detallada.\n"
            "- Si no indicó cuántos alumnos tiene, pregúntalo antes de cotizar. "
            "Si alguno está en bachillerato, también pregunta para incluir la Enciclopedia digital ($36 extra).\n"
            "- La cotización debe incluir CUATRO secciones en texto plano (sin markdown):\n"
            "  1. MENSUALIDAD por alumno con descuento hermano aplicado + total regular + total con pronto pago\n"
            "  2. INSCRIPCIÓN: $264,48 por alumno (sin descuento), total\n"
            "  3. COSTOS ANUALES: $55 por alumno estándar (seguro $15 + enc. inglés $30 + olimpiadas $10), "
            "     más $36 por cada alumno en bachillerato. Total.\n"
            "  4. TOTAL PRIMER MES: suma de inscripción + costos anuales + mensualidad del primer mes\n"
            "     (mostrar opción regular y opción con pronto pago)\n"
            "- Formato sugerido:\n"
            "  MENSUALIDAD (desde sep 2026):\n"
            "  1er alumno: $264,48/mes\n"
            "  2do alumno: $251,26/mes (5% desc. hermano)\n"
            "  Total mensual: $515,74 | Con pronto pago: $470,27\n"
            "  INSCRIPCION (pago unico): $264,48 x 2 = $528,96\n"
            "  COSTOS ANUALES (pago unico, sin desc.): $55 x 2 = $110,00\n"
            "  TOTAL PRIMER MES: $1.154,70 | Con pronto pago: $1.109,23\n"
            "- Los costos opcionales (Competencia Kurios, MOA, traslados) NO se incluyen en la cotización estándar.\n"
            "- Luego de presentar la cotización, haz el handoff a 'billing' con resumen estructurado. "
            "Ejemplo: ACTION:HANDOFF:Ana Perez|Cotizacion 2 alumnos: mens $515,74 (PP $470,27) insc $528,96 extras anuales $110,00 primer mes $1.154,70|billing\n"
            "TARIFAS VIGENTES vs PRÓXIMAS:\n"
            "- Si preguntan por costos ACTUALES (antes de septiembre 2026): inscripción $197,38, mensualidad $197,38 (pronto pago $162,39).\n"
            "- Si preguntan por costos del PRÓXIMO AÑO ESCOLAR o a partir de septiembre 2026: inscripción proyectada $264,48, mensualidad proyectada $264,48 (pronto pago $241,16 con 8,816% de descuento los primeros 10 días). Aclara que son tarifas proyectadas y recomienda confirmar con pagos@ueipab.edu.ve.\n"
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
            "- No uses emojis. No reveles que eres un sistema automático a menos que pregunten directamente.\n"
            "- NUNCA menciones el nombre del propietario, dueño o accionista de la institución. "
            "Si preguntan por el 'dueño' o 'propietario', responde únicamente con las autoridades académicas "
            "(Director: Prof. Arcides Arzola, Sub-directora: Prof. Norka La Rosa, Sub-director: Prof. David Hernández) "
            "y el contacto soporte@ueipab.edu.ve. Puedes mencionar a la fundadora histórica Carmen Violeta Mata de Perdomo si es relevante.\n"
            "- IMPORTANTE: ACTION:SEND_FLYER y ACTION:HANDOFF son comandos internos. El cliente NO los ve. "
            "Inclúyelos siempre al final de la respuesta cuando apliquen.\n"
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

    def process_ai_response(self, conversation, ai_response, context):
        """Parse AI response for ACTION:SEND_FLYER and ACTION:HANDOFF markers."""
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
        result = {'message': visible_text or ai_response}
        if flyer_key:
            result['flyer_key'] = flyer_key
        return result

    def send_flyer(self, conversation, flyer_key):
        """Send a flyer image via WhatsApp for the given key."""
        if flyer_key not in _FLYERS:
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
