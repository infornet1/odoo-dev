import json
import logging
import re

from . import register_skill, get_ve_greeting

_logger = logging.getLogger(__name__)

# Flyers available to send via WhatsApp.
# key → (filename, short description for Claude's reference)
_FLYERS = {
    'inscripcion':          ('inscripcion.png',          'Inscripciones 2026-2027 — Promo anticipada hasta 31 jul: $187,51 · Mensualidad confirmada desde sep: $218,88 · Pronto pago $207,93'),
    'pronto_pago':          ('pronto_pago.png',          'Pronto pago: 5% adicional pagando en los primeros 10 días — ej: mensualidad $218,88 → $207,93 con pronto pago (desde sep 2026)'),
    'tarjeta_credito':      ('tarjeta_credito.png',      'Aceptamos tarjetas de crédito nacionales e internacionales sin comisiones adicionales'),
    'english':              ('english.png',              'MOA School: Cursos de Inglés After School, grupos pequeños, $38/mes'),
    'robotica':             ('robotica.png',             'Clases de Robótica con Kurios — 2 clases/semana, $52/mes, inscripción gratis'),
    'dibujo':               ('dibujo.png',               'Curso de Dibujo y Pintura — 3 meses, 4h semanales, $38/mes'),
    'bachillerato_virtual': ('bachillerato_virtual.png', 'Bachillerato Virtual 100% online — inscríbete ya'),
}

def _get_flyer_url(base_url, filename):
    """Build the public URL for a flyer file."""
    return f"{base_url.rstrip('/')}/{filename}"

# Budget 2026-2027 — Opción A confirmed (voting closed 2026-05-26)
_BUDGET_KNOWLEDGE = (
    "PRESUPUESTO 2026-2027 — RESULTADO OFICIAL (votación cerrada 26/05/2026):\n"
    "Opción A ganó. Si participó en las votaciones, revise su correo electrónico o la comunidad de WhatsApp para más detalles, o escriba a votacion@ueipab.edu.ve\n"
    "\n"
    "PRECIOS CONFIRMADOS vigentes desde el 1 de septiembre de 2026:\n"
    "- Inscripción: $218,88\n"
    "- Mensualidad base: $218,88\n"
    "- Pronto pago (días 1 al 10 de cada mes): $207,93 (ahorro $10,95)\n"
    "- Costo anual por estudiante: $2.845,45\n"
    "\n"
    "DESCUENTOS POR HERMANOS (aplican sobre mensualidad base):\n"
    "- 1er hijo/a: 5% de descuento sobre mensualidad\n"
    "- 2do hijo/a: 8% de descuento\n"
    "- 3er hijo/a en adelante: 11% de descuento\n"
    "- El pronto pago (5% adicional) se aplica sobre la mensualidad ya descontada\n"
    "\n"
    "COSTOS ÚNICOS ANUALES POR ALUMNO (pagaderos durante inscripción):\n"
    "- Seguro escolar: $30,58\n"
    "- Guía de inglés: $35,00 (hasta el 31 jul 2026) | $40,00 (desde el 1 ago 2026)\n"
    "- Olimpiadas recreativas de Lengua y Matemáticas: $10,00\n"
    "- Enciclopedia digital Edugogo: $36,00 (aplica a TODOS los niveles: Inicial, Primaria y Bachillerato)\n"
    "- Modelo de Naciones Unidas Bachillerato: $5,00\n"
    "- Modelo de Naciones Unidas Primaria: $5,00\n"
    "- Otros talleres educativos: $5,00\n"
    "\n"
    "LOGROS ACADÉMICOS 2025-2026 (puntos de orgullo institucional):\n"
    "- 95% de vinculación de madres/padres con la escuela\n"
    "- 98% reconocen el cambio positivo del proceso de enseñanza-aprendizaje\n"
    "- Olimpiadas regionales Canguro y Recreativas: clasificación exitosa en Lengua y Matemáticas\n"
    "- 1er y 3er lugar nacional en Competencia MOA Expedition (Margarita)\n"
    "- Participación destacada en Torneo Nacional de Robótica (Caracas)\n"
    "- Crecimiento del 20% en obtención de literales 'A' en Primaria\n"
    "- Promedio general: 15,80 puntos en Media General\n"
    "- Campeón intermunicipal en Tenis de Mesa, subcampeona en Ajedrez\n"
    "- Primeros en Venezuela en implementar enciclopedia digital Edugogo\n"
    "INCENTIVO ESPECIAL — DESCUENTO GLENDA + AKDEMIA (6,7%):\n"
    "Si el representante se auto-inscribe usando Glenda y Akdemia, recibe 6,7% de descuento\n"
    "sobre la inscripción anticipada: $187,51 → *$174,95* (ahorro de $12,56).\n"
    "Menciona este beneficio activamente cuando el representante pregunte por inscripción o costos.\n"
)

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
    "- Competencias de Robótica Regional (Kurios): si un representante pregunta sobre las competencias regionales "
    "de robótica o el torneo Kurios, comparte este enlace con toda la información oficial: "
    "https://info.kuriosedu.com/books/kmbs/#p=3\n"
    "  PAGO DE LA COMPETENCIA KURIOS: el costo de $10 por alumno (solo si es seleccionado) se paga "
    "DIRECTAMENTE AL COLEGIO — NO a Kurios. Se usan los mismos medios de pago del colegio "
    "(transferencia bancaria, Pago Móvil, Zelle, Cashea, efectivo USD, etc.). "
    "Tras realizar el pago, el representante debe notificar a pagos@ueipab.edu.ve.\n"
    "COMPETENCIA MOA'S SPELLING BEE 2026 — 'Spelling today, leading tomorrow':\n"
    "Organizada por MOA (Move on Academy), aliado educativo del colegio.\n"
    "FECHAS: 1 de junio de 2026 (Primaria) | 2 de junio de 2026 (Media General)\n"
    "El cronograma detallado se enviará una vez aprobado.\n"
    "NIVELES Y DINÁMICAS:\n"
    "- Preescolar (P3): fonética 'Repeat it', deletrear viendo la palabra, identificación visual 'Match it'\n"
    "- Primaria Baja (1° a 4°): deletreo estándar con apoyo visual para confirmar significado\n"
    "- Primaria Alta (5° y 6°): deletreo + prueba de sintaxis 'Sort it' (organizar oraciones)\n"
    "- Bachillerato (1° a 5° Año): deletreo de élite + prueba 'Use it' (crear oraciones originales)\n"
    "REGLAS PRINCIPALES (Protocolo Estándar Clásico CVA):\n"
    "- Say-Spell-Say: el alumno DEBE pronunciar la palabra antes y después del deletreo; omitir el cierre invalida el turno\n"
    "- No Retracing: una vez pronunciada una letra no se puede cambiar\n"
    "- El alumno puede pedir al jurado: repetición, definición, oración de ejemplo, categoría gramatical\n"
    "- Tiempo: 1er y 2do grado → 1 minuto | 3er grado en adelante → 45 segundos\n"
    "- Challenges: 1°-3° grado='Match it', 4°-6° grado='Sort it', Media General=producir oración\n"
    "ESTRUCTURA DE RONDAS:\n"
    "- Ronda 1 Easy: 12 participantes, clasifican los mejores 8-6\n"
    "- Ronda 2 Medium: eliminación progresiva hasta 2 finalistas; el eliminado obtiene 3er lugar\n"
    "- Ronda Final Difficult: duelo directo; se determina 1er y 2do lugar\n"
    "- Championship Word: si un finalista falla, el oponente debe deletrear esa palabra y una adicional para ganar\n"
    "RECOMENDACIÓN PARA PADRES: practicar constante y disciplinadamente tanto en el colegio como en casa.\n"
    "REGLAS COMPLETAS (PDF oficial): https://drive.google.com/file/d/11LG9BRDOMjbiJC-kjU4OysnjIDAhP29V/view?usp=drivesdk\n"
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
    "https://edge.akdemia.com/enrollments/b87d60bc6ba93746 — para nuevos aspirantes.\n"
    "- INSCRIPCIÓN (alumnos actuales que van a inscribirse para el próximo período): "
    "https://edge.akdemia.com/admissions/09f8190d36eef4ea/start\n"
    "- Para dudas adicionales: soporte@ueipab.edu.ve\n"
    "FLUJO CORRECTO PARA INSCRIPCIÓN DE ALUMNOS ACTUALES — sigue SIEMPRE este orden:\n"
    "1. PRIMERO — Verificar solvencia: ¿Está al día con el período 2025-2026?\n"
    "   Si tiene saldo pendiente → NO puede inscribirse. Orientar a pagos@ueipab.edu.ve primero.\n"
    "2. SEGUNDO — Verificar credenciales Akdemia ANTES de dar el enlace de inscripción:\n"
    "   '¿Tienes a mano el correo y contraseña de Akdemia?'\n"
    "   - Olvidó contraseña → pasos de recuperación: ir a https://edge.akdemia.com/login#resetPasswordModal\n"
    "     → clic en 'Olvidaste tu contraseña?' → ingresar correo → revisar bandeja (incl. spam) → crear nueva clave.\n"
    "   - No recuerda el correo institucional → usar ACTION:SCHOOL_ACCOUNT_HELP (ver sección de cuenta escolar).\n"
    "   NOTA: muchos representantes acuden en persona porque olvidaron credenciales. Anticipa siempre.\n"
    "3. TERCERO — Solo cuando confirmes solvencia y acceso a Akdemia → entregar enlace de inscripción:\n"
    "   https://edge.akdemia.com/admissions/09f8190d36eef4ea/start\n"
    "ASPIRANTES PROCEDENTES DEL EXTERIOR (regresan a Venezuela a mitad o inicio de año):\n"
    "- Si hay cupo disponible: el colegio acepta procesar la admisión.\n"
    "- BACHILLERATO (1° a 5° año Media General) — REQUISITO OBLIGATORIO antes de acudir al colegio:\n"
    "  1. Dirigirse a la Zona Educativa del estado Anzoátegui.\n"
    "  2. Llevar documentos académicos del exterior (certificados de notas, constancias).\n"
    "  3. Solicitar la equivalencia de grado conforme al currículo venezolano.\n"
    "  4. Obtener el documento oficial en físico que certifique en qué grado debe inscribirse.\n"
    "  5. Con ese documento en mano → acudir al colegio para procesar la inscripción.\n"
    "  SIN ese documento de la Zona Educativa, el colegio NO puede asignar el grado ni inscribir al alumno.\n"
    "- PRIMARIA e INICIAL: proceso puede ser diferente; orientar a soporte@ueipab.edu.ve para confirmar.\n"
    "- Ingreso tardío (finales 2026 o enero 2027): puede iniciarse la solicitud de cupo con anticipación.\n"
    "  Disponibilidad varía por grado. Contactar soporte@ueipab.edu.ve para detalles.\n"
    "- Solicitud de cupo inicial (todos los niveles): https://edge.akdemia.com/enrollments/b87d60bc6ba93746\n"
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
    "- Estas tarifas son oficiales (Opción A aprobada en consulta 26/05/2026). Para casos particulares, orientar a pagos@ueipab.edu.ve\n"
    "COSTOS ANUALES ÚNICOS (pago único por año escolar, sin descuento, por alumno — se suscriben mediante acuerdo especial de mayo a julio 2026):\n"
    "    Seguro Escolar: $30,58\n"
    "    Guía de Inglés: $35 (hasta el 31 jul 2026) | $40 (desde el 1 ago 2026)\n"
    "    Olimpiadas Recreativas de Lengua y Matemáticas: $10\n"
    "    Enciclopedia (Inicial, Primaria o Bachillerato): $36 (aplica a TODOS los niveles)\n"
    "    Total costos anuales por alumno: $111,58 (hasta el 31 jul 2026) | $116,58 (desde el 1 ago 2026)\n"
    "ACLARACIÓN — COSTOS ANUALES OPCIONALES (talleres y actividades extracurriculares):\n"
    "- Los costos de Modelo de Naciones Unidas, talleres, etc. se pagan mediante acuerdo anual\n"
    "  al INICIO del año escolar (mayo–julio). La participación ocurre durante TODO el año.\n"
    "- El pago no es al momento del taller — es único al inicio del año escolar.\n"
    "- Política de reembolso si el alumno inscribe una actividad pero no participa: NO está definida\n"
    "  en esta base de conocimiento. Orientar a pagos@ueipab.edu.ve para confirmar la política oficial.\n"
    "SEGURO ESCOLAR 2026-2027 — DETALLE:\n"
    "- Empresa: Seguros Caracas — Póliza Accidentes Escolares, Alternativa 2\n"
    "- Costo: $30,58 por alumno por año escolar (pago único)\n"
    "- Cobertura: accidentes escolares durante actividades del colegio\n"
    "- Para reclamaciones o información de la póliza:\n"
    "  * WhatsApp: 0414-903.3738\n"
    "  * Email: amis@grupov.com.ve\n"
    "  * App móvil: 'Asegurados' (Seguros Caracas)\n"
    "- Asesora local en El Tigre: Sra. Johanna Hernández\n"
    "  * WhatsApp directo: https://wa.me/584248340051\n"
    "- Si alguien pregunta por el nombre de la aseguradora, el tipo de seguro o cómo reclamar: "
    "proporciona esta información directamente.\n"
    "COSTOS OPCIONALES / CONDICIONALES (NO incluir en cotización estándar):\n"
    "    Competencia Kurios: $10 (solo si el alumno es seleccionado por el colegio) — "
    "pago DIRECTO AL COLEGIO con los medios de pago habituales; notificar a pagos@ueipab.edu.ve tras pagar.\n"
    "    Competencia MOA inglés: $25 (solo si el alumno es seleccionado por el colegio)\n"
    "    Encuentros Regionales/Nacionales: traslados y logística a cargo de los padres\n"
    "DESCUENTOS POR HERMANOS (aplica sobre mensualidad):\n"
    "- 1er alumno: 5% de descuento sobre mensualidad\n"
    "- 2do alumno: 8% de descuento sobre mensualidad\n"
    "- 3er alumno en adelante: 11% de descuento sobre mensualidad\n"
    "- Los descuentos de hermano y pronto pago se acumulan (el pronto pago se aplica sobre la mensualidad ya descontada)\n"
    "- Inscripción: precio completo por alumno, sin descuento por hermano\n"
    "TABLA DE MENSUALIDAD POR ALUMNO (tarifas Sep 2026, confirmadas Opción A — pronto pago = 5% dto. sobre mensualidad ya descontada):\n"
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
    "TARIFAS CONFIRMADAS 2026-2027 (Opción A aprobada 26/05/2026):\n"
    "- Nueva mensualidad base desde septiembre 2026: $218,88 (antes de descuentos por hermanos). Ver tabla de descuentos.\n"
    "- Costos anuales obligatorios (NO incluidos en la mensualidad): seguro escolar ($30,58), guía de inglés ($35 hasta el 31 jul / $40 desde el 1 ago), olimpiadas ($10) y enciclopedia de su nivel ($36) — total $111,58/alumno (hasta el 31 jul 2026) o $116,58/alumno (desde el 1 ago 2026).\n"
    "- Costos opcionales/condicionales (no incluir en cotización estándar): concursos nacionales (robótica, química, Kurios, MOA, etc.) y eventos externos — se pagan según selección o participación del alumno.\n"
    "ALIANZAS COMERCIALES LOCALES (El Tigre):\n"
    "- Almacenes París, Comercial Caracas y Ferretería Veramar ofrecen descuentos especiales en uniformes y útiles escolares a representantes del colegio.\n"
    "DISTINTIVO ESCOLAR (distintivo del uniforme):\n"
    "- Proveedor oficial autorizado: Almacenes París (El Tigre).\n"
    "- Costo aproximado: $8 a $10 por distintivo.\n"
    "- Contacto directo:\n"
    "    WhatsApp: https://wa.me/584148172725\n"
    "    Email: almacenpariseltigre@gmail.com\n"
    "    Instagram: https://www.instagram.com/almacenpariseltigre\n"
    "- Siempre ofrece los tres canales de contacto con sus hipervínculos para que el representante pueda hacer clic directamente.\n"
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

    # ── Family Billing Enrichment ────────────────────────────────────────────

    _BILLING_KEYWORDS = {
        'mensualidad', 'mensual', 'inscripcion', 'inscripción', 'cuota', 'pago',
        'costo', 'precio', 'tarifa', 'representado', 'hijo', 'hija', 'alumno',
        'alumna', 'estudiante', 'propuesta', 'opcion', 'opción', 'monto',
        'cuanto', 'cuánto', 'vale', 'cobra', 'cobran',
    }

    @staticmethod
    def _norm_phone(raw):
        """Normalize phone → 10-digit Venezuelan format."""
        p = (raw or '').strip().replace(' ', '').replace('-', '').lstrip('+')
        if p.startswith('58') and len(p) > 10:
            p = p[2:]
        p = p.lstrip('0')
        return p[-10:] if len(p) > 10 else p

    @staticmethod
    def _word_overlap(a, b):
        """Count matching words between two uppercased strings."""
        wa = set(a.upper().split())
        wb = set(b.upper().split())
        return len(wa & wb)

    def _load_family_billing_cache(self, conversation):
        raw = conversation.env['ir.config_parameter'].sudo().get_param(
            'school.family_billing_json', '{}')
        try:
            return json.loads(raw).get('families', [])
        except Exception:
            return []

    def _load_directory_cache(self, conversation):
        raw = conversation.env['ir.config_parameter'].sudo().get_param(
            'school.student_directory_json', '{}')
        try:
            return json.loads(raw).get('students', [])
        except Exception:
            return []

    def _lookup_grade(self, student_name, directory):
        """Return grade string for a student name via fuzzy match, or ''."""
        best, best_score = None, 1
        for s in directory:
            score = self._word_overlap(student_name, s.get('name', ''))
            if score > best_score:
                best, best_score = s, score
        if best:
            return best.get('grade') or best.get('ou') or ''
        return ''

    def _enrich_billing_context(self, conversation):
        """
        Look up the conversation partner in the family billing cache.
        Returns a formatted context block string, or '' if not found.

        Lookup strategy (in order):
        1. Phone match against billing cache
        2. No match → check latest inbound message for student names
        """
        import re
        families   = self._load_family_billing_cache(conversation)
        directory  = self._load_directory_cache(conversation)
        if not families:
            return ''

        family = None

        # Strategy 1 — phone match (WA: conversation.phone; Telegram: partner.mobile/phone)
        conv_phone = self._norm_phone(conversation.phone or '')
        if not conv_phone and conversation.partner_id:
            conv_phone = self._norm_phone(
                conversation.partner_id.mobile or conversation.partner_id.phone or ''
            )
        if conv_phone:
            for f in families:
                if f.get('phone') and self._norm_phone(f['phone']) == conv_phone:
                    family = f
                    break

        # Strategy 2 — student name mention in latest inbound message
        if not family:
            latest = conversation.env['ai.agent.message'].search(
                [('conversation_id', '=', conversation.id),
                 ('direction', '=', 'inbound')],
                order='id desc', limit=1)
            msg_text = (latest.body or '').upper() if latest else ''

            # Only attempt name search if billing keywords are present
            words_in_msg = set(re.sub(r'[^\w\s]', ' ', msg_text).split())
            has_billing_kw = bool(words_in_msg & {k.upper() for k in self._BILLING_KEYWORDS})

            if has_billing_kw and msg_text:
                best_family, best_score = None, 1
                for f in families:
                    for student in f.get('students', []):
                        score = self._word_overlap(student, msg_text)
                        if score > best_score:
                            best_family, best_score = f, score
                family = best_family

        if not family:
            return ''

        # Build grade info for each student
        student_lines = []
        for student in family.get('students', []):
            grade = self._lookup_grade(student, directory)
            grade_str = f' → {grade}' if grade else ''
            student_lines.append(f'    · {student}{grade_str}')

        monthly   = family.get('monthly', 0.0)
        quantity  = family.get('quantity', 1)
        discount  = family.get('discount', '')
        status    = family.get('status', '')
        parent    = family.get('parent_name', '')

        discount_note = f' | Descuento: {discount}' if discount else (
            ' | Descuento hermanos aplicado' if quantity > 1 else '')

        status_note = f' | Estado: {status}' if status and status != 'ACTIVE' else ''

        # ── Remaining months forecast (2025-2026 billing period ends Aug 31) ──
        from datetime import date as _date
        _MONTH_ES = {1:'enero',2:'febrero',3:'marzo',4:'abril',5:'mayo',
                     6:'junio',7:'julio',8:'agosto',9:'septiembre',
                     10:'octubre',11:'noviembre',12:'diciembre'}
        _SCHOOL_YEAR_END_MONTH = 8   # August
        today = _date.today()
        next_month = today.month + 1 if today.month < 12 else 1
        remaining = [m for m in range(next_month, _SCHOOL_YEAR_END_MONTH + 1)]
        forecast_block = ''
        # One-time annual costs 2026-2027 per student (guía inglés $35 until Jul 31, $40 from Aug 1)
        _GUIDE_INGLES = 35.0 if today < _date(2026, 8, 1) else 40.0
        _ANNUAL_COST_PER_STUDENT = round(30.58 + _GUIDE_INGLES + 10.0 + 36.0, 2)
        annual_total = _ANNUAL_COST_PER_STUDENT * quantity

        if remaining:
            n            = len(remaining)
            month_names  = ', '.join(_MONTH_ES.get(m, str(m)) for m in remaining)
            total_reg    = monthly * n
            total_pp     = monthly * 0.95 * n
            forecast_block = (
                f"  PRONÓSTICO AÑO ESCOLAR 2025-2026 (meses aún no facturados):\n"
                f"    Meses pendientes : {month_names} ({n} mensualidad{'es' if n!=1 else ''})\n"
                f"    Total regular    : {n} × ${monthly:,.2f} = ${total_reg:,.2f}\n"
                f"    Total pronto pago: {n} × ${monthly * 0.95:,.2f} = ${total_pp:,.2f}\n"
                f"    (Pronto pago = pagar en los primeros 10 días de cada mes)\n"
                f"  COSTOS ÚNICOS 2026-2027 (acuerdo especial, por alumno):\n"
                f"    {quantity} alumno(s) × ${_ANNUAL_COST_PER_STUDENT:,.2f} = ${annual_total:,.2f}\n"
                f"    (seguro $30,58 + guía inglés ${_GUIDE_INGLES:,.2f} + olimpiadas $10 + enciclopedia $36)\n"
                f"  USA ESTOS DATOS para responder sin preguntar al representante. ──\n"
            )

        block = (
            "\n📋 DATOS FAMILIARES (fuente: sistema escolar — NO solicitar al representante):\n"
            f"  Representante : {parent}{status_note}\n"
            f"  Estudiantes   :\n"
            + '\n'.join(student_lines) + '\n'
            + f"  Mensualidad actual: ${monthly:,.2f} | {quantity} estudiante(s){discount_note}\n"
            + forecast_block
            + "  ── Con la tarifa aprobada (Opción A, +10,89%), la nueva mensualidad desde sep 2026 sería:\n"
            f"     ${monthly * 1.1089:,.2f}/mes "
            f"(pronto pago ${monthly * 1.1089 * 0.95:,.2f})\n"
            "  IMPORTANTE: Responde directamente con estos datos. "
            "No los pidas al representante. ──\n"
        )
        return block

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

        # Option-A auto-link: cédula confirmed identity → write telegram_chat_id to real partner
        if partner and conversation.channel == 'telegram' and conversation.telegram_chat_id:
            if not partner.telegram_chat_id:
                partner.write({'telegram_chat_id': conversation.telegram_chat_id})
                _logger.info(
                    "Telegram auto-link: partner %s (%d) ← chat_id %s (via cédula)",
                    partner.name, partner.id, conversation.telegram_chat_id,
                )

        # Gap-3 fix: promote conversation to real partner immediately so the next
        # turn builds context from the identified record (both WA and Telegram).
        if partner and conversation.partner_id.id != partner.id:
            conversation.sudo().write({'partner_id': partner.id})
            _logger.info(
                "Cedula match: promoted conv %d partner %s → %s",
                conversation.id, conversation.partner_id.name, partner.name,
            )

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

    @staticmethod
    def _get_prior_conversation_summary(conversation):
        """Return a compact summary of the last 1-2 resolved conversations for this contact.

        Injected into the system prompt so Glenda can maintain continuity when a contact
        opens a new conversation shortly after a previous one (e.g. a follow-up question
        2 minutes later) or returns days later without re-introducing themselves.

        Match priority: telegram_chat_id > identified partner_id > phone.
        Window: resolved conversations in the last 7 days with at least 1 message.
        """
        from datetime import datetime, timedelta

        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

        Conversation = conversation.env['ai.agent.conversation']
        base_domain = [
            ('id', '!=', conversation.id),
            ('state', '=', 'resolved'),
            ('create_date', '>=', cutoff),
        ]

        if conversation.telegram_chat_id:
            domain = base_domain + [('telegram_chat_id', '=', conversation.telegram_chat_id)]
        elif (conversation.partner_id
                and not conversation.partner_id.name.startswith('Consulta WhatsApp')):
            domain = base_domain + [('partner_id', '=', conversation.partner_id.id)]
        elif conversation.phone:
            domain = base_domain + [('phone', '=', conversation.phone)]
        else:
            return ''

        prior_convs = Conversation.search(domain, order='create_date desc', limit=2)
        if not prior_convs:
            return ''

        now_utc = datetime.utcnow()
        lines = []

        for pc in prior_convs:
            content_msgs = [m for m in pc.agent_message_ids.sorted('timestamp') if m.body]
            if not content_msgs:
                continue

            delta_secs = int((now_utc - pc.create_date).total_seconds())
            if delta_secs < 3600:
                ago = f"hace {delta_secs // 60} minuto(s)"
            elif delta_secs < 86400:
                ago = f"hace {delta_secs // 3600} hora(s)"
            elif delta_secs < 172800:
                ago = "ayer"
            else:
                ago = f"hace {delta_secs // 86400} días"

            snippets = []
            for m in content_msgs[:6]:
                tag = "Representante" if m.direction == 'inbound' else "Glenda"
                text = (m.body or '').replace('\n', ' ')[:150]
                snippets.append(f"  [{tag}]: {text}")
                if len(snippets) >= 4:
                    break

            if snippets:
                lines.append(f"— Conversación {ago}:")
                lines.extend(snippets)

        if not lines:
            return ''

        return (
            "\nHISTORIAL PREVIO CON ESTE CONTACTO (últimos 7 días):\n"
            + "\n".join(lines) + "\n"
            + "► Si el mensaje actual parece continuar un tema anterior "
            "(referencia a 'eso', 'ese precio', 'lo que dijiste', pregunta sin contexto propio), "
            "responde directamente usando ese historial. "
            "No repitas el saludo genérico ni el menú de bienvenida.\n"
        )

    def _get_customers_sheet_context(self, conversation):
        """Return name hint from Customers sheet for unidentified Telegram/WA contacts."""
        # Only useful when partner is a placeholder (unidentified)
        partner = conversation.partner_id
        if partner and not partner.name.startswith(('Consulta WhatsApp', 'Telegram ')):
            return ''  # already identified

        raw = conversation.env['ir.config_parameter'].sudo().get_param(
            'school.customers_sheet_json', '')
        if not raw:
            return ''

        try:
            import json as _json
            data = _json.loads(raw)
        except Exception:
            return ''

        # Try to match by email stored on partner
        email = (partner.email or '').lower() if partner else ''
        if email and email in data:
            name = data[email]
            return (
                f"HOJA CUSTOMERS: El email {email} corresponde a {name} "
                f"según la hoja de cálculo del colegio.\n"
            )

        return ''

    def get_context(self, conversation):
        cfg = self._get_agent_config(conversation)
        partner = conversation.partner_id
        partner_found = bool(
            partner and not partner.name.startswith(('Consulta WhatsApp', 'Telegram '))
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
            'billing_enrichment':        self._enrich_billing_context(conversation),
            'customers_sheet_context':   self._get_customers_sheet_context(conversation),
            'prior_history':             self._get_prior_conversation_summary(conversation),
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
                f"'no entendiste', 'fallo en', o similares, captura la sugerencia en una SOLA LÍNEA "
                f"al final de tu respuesta con el marcador interno:\n"
                f"  ACTION:LOG_FEEDBACK:categoria|texto_de_la_sugerencia_en_una_sola_linea\n"
                f"  Categorías válidas: flujo, respuesta, idioma, asistencia, conocimiento, tecnico, otro\n"
                f"  Ejemplo: ACTION:LOG_FEEDBACK:flujo|Debería poder retomar una conversación anterior sin empezar de cero\n"
                f"  IMPORTANTE: el texto debe ir en UNA SOLA LÍNEA sin saltos de línea dentro del marcador.\n"
                f"- Agradece brevemente la sugerencia. Aplica igual la regla de NO terminar con '¿Hay algo más?'.\n"
                f"- Si {first} quiere probar un escenario específico (ej: 'actúa como si fuera un representante'), "
                f"entra en ese rol naturalmente y demuestra tus capacidades.\n"
                f"- ACTION:LOG_FEEDBACK es un marcador interno. {first} NO lo verá.\n\n"
            )

        billing_enrichment = context.get('billing_enrichment', '')
        customers_sheet_context = context.get('customers_sheet_context', '')
        prior_history = context.get('prior_history', '')

        community_block = (
            "CONTEXTO DE LA COMUNIDAD — LEE ESTO PRIMERO:\n"
            "Hablas con padres y representantes de El Tigre, Anzoategui, Venezuela.\n"
            "Esta comunidad vive una situacion economica muy dificil. Muchos de los padres "
            "que te escriben estan preocupados, cansados o bajo presion cuando lo hacen.\n"
            "Tu objetivo es hacer que se sientan ATENDIDOS, no INFORMADOS.\n"
            "Un padre que recibe una respuesta corta y precisa se siente respetado. "
            "Un padre que recibe 5 parrafos siente que la maquina no lo esta escuchando.\n"
            "Comunica como lo haria una persona de confianza: directo, calido, sin florituras.\n\n"
        )

        audience_block = (
            "CONTEXTO DE AUDIENCIA:\n"
            "- Los representantes tienen distintos niveles de familiaridad con tecnologia. "
            "Muchos son padres de alumnos de Media General con poca experiencia con asistentes virtuales.\n"
            "- Routing del menu de bienvenida: si escribe '1' o menciona saldo/deuda/cuenta → consulta balance de inmediato; "
            "'2' o propuesta/precio/mensualidad proximo año → presenta la tarifa aprobada (Opción A) "
            "comenzando por la promo de inscripcion anticipada hasta el 31 jul 2026; "
            "'3' o inscripcion/matricula → presenta promo anticipada $187,51; "
            "'4' o informacion/horarios/uniformes → pide que especifique el tema; "
            "'5' u otro → pide que describa su consulta.\n"
            "- Tono: parrafo corto primero — ofrece detalle si lo pide. Sin jergon tecnico ni menciones a sistemas internos. "
            "Si el representante repite una pregunta, respondela con igual paciencia (nunca decir 'como ya te indique'). "
            "Si no puedes resolver, ofrece siempre soporte@ueipab.edu.ve o pagos@ueipab.edu.ve. "
            "Si pregunta si eres persona o IA: confirma que eres asistente virtual del colegio "
            "y que el equipo revisa las conversaciones.\n"
        )

        wa_invite = (
            "\n\n[Solo WhatsApp — agregar al final del menu]: Para respuestas al instante, "
            "tambien puedes contactarme por Telegram: https://t.me/GlendaUeipabBot"
            if conversation.channel == 'whatsapp' else ""
        )

        if prior_history:
            # Returning contact: Python already knows there's history — no need for Claude to detect it.
            # Steer back to prior thread instead of replaying the full menu.
            menu_block = (
                "PRIMER MENSAJE — CONTACTO CON HISTORIAL PREVIO:\n"
                "Este contacto ya conversó contigo antes (ver HISTORIAL PREVIO arriba). "
                "Si su mensaje es solo un saludo generico (hola, buenas, buenos dias, etc.):\n"
                "  → NO mostrar el menu completo.\n"
                "  → Saludar por nombre si lo conoces + retomar el hilo del tema anterior en 1 linea.\n"
                "  → Ejemplo (tema = mensualidad): '¡Hola [nombre]! ¿Pudiste revisar la informacion de tarifas 2026-2027? ¿Te hago la cotizacion?'\n"
                "  → Ejemplo (tema = saldo/deuda): '¡Hola [nombre]! ¿Pudiste coordinar el pago con pagos@ueipab.edu.ve?'\n"
                "  → Si el historial no deja claro el tema: '¡Hola [nombre]! ¿En que puedo ayudarte hoy?' — sin menu.\n"
                "Si su mensaje incluye una consulta especifica: responde directamente usando el historial como contexto.\n"
            )
        else:
            menu_block = (
                "MENU DE BIENVENIDA — PRIMER MENSAJE GENÉRICO:\n"
                "Si el primer mensaje del representante es solo un saludo sin consulta especifica "
                "(hola, buenas, buenos dias, buenas tardes, etc.): responde con el menu de opciones. "
                "Si el mensaje ya incluye una consulta especifica: responde directamente a esa consulta.\n"
                "Formato del menu (adapta el saludo segun la hora del dia):\n"
                "---\n"
                "[Saludo apropiado]! Soy [nombre], asistente virtual del Colegio Andres Bello.\n\n"
                "Puedo ayudarte con lo siguiente:\n\n"
                "1️⃣  Mi estado de cuenta / saldo pendiente\n"
                "2️⃣  Tarifas 2026-2027 e inscripcion anticipada\n"
                "3️⃣  Inscripcion anticipada y matricula\n"
                "4️⃣  Informacion general (horarios, uniformes, cursos)\n"
                "5️⃣  Otro asunto\n\n"
                "Responde con el numero de tu opcion, o escribe directamente tu consulta."
                + wa_invite
                + "\n---\n"
            )

        return (
            f"Eres {agent_name}, asistente virtual del {institution}, ubicada en Venezuela.\n\n"
            + community_block
            + calibration_block
            + audience_block
            + _INSTITUTIONAL_KNOWLEDGE
            + _BUDGET_KNOWLEDGE
            + self._build_bcv_block(bcv) + "\n"
            + balance_ctx + "\n"
            + billing_enrichment
            + (customers_sheet_context if customers_sheet_context else '')
            + "CONTEXTO:\n"
            "- Esta persona escribió directamente a este número de WhatsApp sin que nosotros la hayamos contactado.\n"
            + contact_ctx
            + prior_history
            + "\nFLYERS DISPONIBLES (imágenes informativas que puedes enviar):\n"
            + flyer_list + "\n"
            + "\nINSTRUCCIONES:\n"
            "- Comunícate siempre en español venezolano, cálida y profesionalmente.\n"
            "- Salúdala y preséntate brevemente como asistente del colegio.\n"
            + menu_block
            + "- Entiende su consulta. Responde preguntas generales con el conocimiento institucional que tienes "
            "(medios de pago, mensualidades, fechas, información general del colegio).\n"
            "PROPUESTA ECONÓMICA 2026-2027 — RESULTADO FINAL (OPCIÓN A APROBADA):\n"
            "La consulta presupuestaria cerró el 26/05/2026 y la OPCIÓN A fue aprobada. NO proceses votos.\n"
            "Si un representante pregunta por la mensualidad, el resultado o la votación:\n"
            "- Carta oficial de resultados: https://docs.google.com/document/d/1GSGzXLxGaaMvYtbyJuGki5KFodmpoy5OyHk0fm4e2fg/edit?usp=sharing\n"
            "- Tarifa aprobada (Opción A): $218,88/mes desde sep 2026 (incremento 10,89%). Pronto pago: $207,93.\n"
            "- La Opción B NO fue aprobada: no la menciones ni la cotices. Solo si preguntan "
            "expresamente por el resultado de la votación puedes indicar que la Opción A ganó.\n"
            "- Para consultas sobre la tarifa aprobada: pagos@ueipab.edu.ve.\n"
            + self._get_voting_wa_block(conversation)
            +
            "PRIORIDAD AL RESPONDER SOBRE TARIFAS E INSCRIPCION (VIGENTES):\n"
            "- Mensualidad ACTUAL vigente: $197,38\n"
            "- Pronto pago (primeros 10 días del mes): $162,39\n"
            "- Cashea: opción de pago en cuotas (confirmar enlace con pagos@ueipab.edu.ve)\n"
            "- SIEMPRE ofrece la PROMOCION DE INSCRIPCION ANTICIPADA (mayo - 31 julio 2026): "
            "inscripción $187,51 + mensualidad septiembre $197,38. Requisito: 2025-2026 saldado.\n"
            "- Menciona siempre Cashea como opción de pago.\n"
            "- Si la persona pregunta por inscripciones, mensualidad, cursos extracurriculares, métodos de pago "
            "u otros temas cubiertos por un flyer disponible, añade ACTION:SEND_FLYER:clave al final de tu "
            "respuesta (usa exactamente la clave de la lista de flyers). Solo un flyer por respuesta.\n"
            "  Ejemplo: ACTION:SEND_FLYER:inscripcion\n"
            "PERÍODO DE FACTURACIÓN 2025-2026:\n"
            "- El año escolar 2025-2026 se factura hasta el 31 de agosto de 2026.\n"
            "- Cuando un representante pregunte cuánto falta para culminar el año o el total de meses "
            "pendientes: NUNCA le preguntes cuántos meses le quedan. En su lugar:\n"
            "  1. Si el contacto está identificado → usa ACTION:QUERY_BALANCE:FOUND para obtener las "
            "facturas pendientes reales del sistema.\n"
            "  2. El bloque 📋 DATOS FAMILIARES ya incluye el PRONÓSTICO con los meses exactos "
            "y montos calculados. Úsalos directamente para responder sin inventar cifras.\n"
            "  3. Presenta: saldo pendiente (si hay) + meses no facturados del pronóstico = total.\n"
            "- Si el contacto NO está identificado: pídele la cédula para consultar su saldo.\n"
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
            "BALANCE 2025-2026 — VERIFICAR SIEMPRE ANTES DE COTIZAR 2026-2027:\n"
            "Cuando el representante pregunte por inscripcion, mensualidad del proximo año o tarifas:\n"
            "  1. Consulta el bloque SALDO EN SISTEMA:\n"
            "     - Si hay facturas pendientes: informa el saldo PRIMERO. Para firmar el convenio del "
            "1er llamado basta estar solvente al menos con el mes de JUNIO 2026 (julio y agosto se "
            "pagan con normalidad bajo el convenio). Si solo debe junio: dile que al pagarlo ya puede "
            "firmar su convenio con la tarifa promocional. Para el 2do llamado se requiere solvencia "
            "al 31/07/2026; para el 3er llamado, solvencia total del periodo 2025-2026.\n"
            "     - Si saldo es cero: confirma que esta al dia y procede con la cotizacion.\n"
            "  2. Si el contacto no esta identificado: pide cedula primero (para verificar saldo).\n"
            "COTIZACIÓN 2026-2027 — GENERADOR AUTOMATICO (ACTION:QUOTE) — Comunicado oficial 10/06/2026:\n"
            "El sistema genera la cotizacion formal EXACTA desde Odoo (productos oficiales). "
            "NUNCA calcules ni cites montos totales tu mismo: usa el marcador y el sistema enviara "
            "la cotizacion en un mensaje aparte.\n"
            "- Cuando un representante IDENTIFICADO pida precios, cotizacion o costos de inscripcion "
            "2026-2027 y sepas cuantos alumnos inscribira, emite al final de tu respuesta:\n"
            "    ACTION:QUOTE:numero_de_alumnos\n"
            "  Ejemplo: 'Con gusto, te preparo la cotizacion formal para tus 2 hijos. 😊\\n\\nACTION:QUOTE:2'\n"
            "- Si no sabes cuantos alumnos inscribira: pregunta primero ('¿Para cuantos alumnos seria?').\n"
            "- Si el contacto NO esta identificado: pide cedula primero. NUNCA emitas ACTION:QUOTE sin identificacion.\n"
            "- NO emitas ACTION:HANDOFF en el mismo mensaje que ACTION:QUOTE; el handoff va en un turno posterior.\n"
            "CRONOGRAMA DE LLAMADOS (contexto conversacional — el sistema cotiza automaticamente el llamado vigente):\n"
            "  1er llamado (11 jun - 31 jul 2026) PROMOCION ESPECIAL: inscripcion $187,51 / mensualidad $197,38.\n"
            "    Incluye CONVENIO DE PAGO a tarifa preferencial: julio y agosto se pagan con normalidad, "
            "y el representante planifica las fechas de pago de inscripcion, septiembre, seguro escolar y "
            "enciclopedias. Requisito: solvente al menos con junio 2026. Las fechas DEFINITIVAS del "
            "convenio se acuerdan y firman EN LA INSTITUCION (invita a visitar la administracion, "
            "lunes a viernes, tambien durante agosto).\n"
            "  2do llamado (1 - 31 ago 2026) PROMOCION VACACIONAL: inscripcion $207,93 / mensualidad $218,88. "
            "Sin convenio; requiere solvencia al 31/07/2026.\n"
            "  3er llamado (1 - 30 sep 2026) REGULAR: inscripcion $218,88 / mensualidad $218,88. "
            "Sin convenio; requiere solvencia total 2025-2026.\n"
            "  Descuentos hermanos en mensualidad (aplican TAMBIEN sobre la tarifa promocional): "
            "2 hijos -5% | 3 hijos -8% | 4+ hijos -11%.\n"
            "  Costos anuales por alumno: $111,58 hasta el 31 jul (seguro $30,58 + guia ingles $35 + "
            "olimpiadas $10 + enciclopedia $36); $116,58 desde el 1 ago (guia ingles sube a $40).\n"
            "  Desde el 17/07/2026 las mensualidades de julio y agosto se facturan por anticipado en el estado de cuenta.\n"
            "- Todos los montos en USD, pagaderos a tasa BCV del dia.\n"
            "- NO presentes la Opcion B ni hables de opciones pendientes: la tarifa es definitiva (Opcion A).\n"
            "- Costos opcionales (Kurios, MOA, traslados): NO se incluyen en cotizacion estandar.\n"
            "- En el turno SIGUIENTE a la cotizacion, haz el handoff: ACTION:HANDOFF:nombre|cotizacion 2026-2027 generada|billing\n"
            "TARIFAS VIGENTES vs PRÓXIMAS:\n"
            "- Si preguntan por costos ACTUALES (antes de septiembre 2026): inscripción $197,38, mensualidad $197,38 (pronto pago $162,39).\n"
            "- Si preguntan por costos del PRÓXIMO AÑO ESCOLAR o a partir de septiembre 2026: inscripción en promoción $187,51 (hasta el 31 jul), mensualidad desde sep base $218,88 ($207,94 para el 1er alumno con 5% dto. hermano; pronto pago $197,54). Tarifas confirmadas — Opción A aprobada el 26/05/2026.\n"
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
            "la fecha límite para comunicar su decisión por escrito a pagos@ueipab.edu.ve fue el "
            "lunes 08 de junio de 2026 a las 12:30 p.m.; si no respondió, el sistema asumió la "
            "aceptación de las nuevas condiciones, pero aún puede escribir a pagos@ueipab.edu.ve "
            "para revisar su caso. Menciona que si su alumno tiene méritos académicos o "
            "deportivos excepcionales, puede solicitar revisión de un 'Caso Especial' individual via email. "
            "Invítala a comunicarse con pagos@ueipab.edu.ve antes de tomar cualquier decisión. "
            "No presiones ni repitas la política fríamente. "
            "Usa ACTION:HANDOFF con ruta 'pdvsa_retention'.\n"
            "- Si preguntan por la FECHA LÍMITE: fue el 08 de junio de 2026 a las 12:30 p.m. (ya venció). "
            "Sin respuesta antes de esa fecha, el sistema asumió aceptación de las nuevas condiciones. "
            "Casos particulares: pagos@ueipab.edu.ve.\n"
            "- Si preguntan si su alumno califica como CASO ESPECIAL: los criterios son excelente "
            "rendimiento académico, atleta con medallas nacionales, músico activo del Sistema de "
            "Orquestas Juveniles, o habilidades destacadas reconocidas. Orientar a pagos@ueipab.edu.ve "
            "para solicitud individual. No hay excepciones generales.\n"
            "- Si preguntan por el aumento de tarifas 2026-2027: el ajuste aprobado es de 10,89% "
            "(Opción A — mensualidad base $218,88 desde septiembre 2026). "
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
            "LONGITUD DE RESPUESTA — REGLA CRITICA:\n"
            "Estas en WhatsApp o Telegram. Los padres leen en el movil, con poco tiempo y mucho estres. "
            "Responde como lo haria una persona eficiente, no un manual.\n"
            "Limites estrictos por tipo de mensaje:\n"
            "- Saludo simple / sin consulta especifica → menu (maximo 8 lineas, nada mas)\n"
            "- Consulta de saldo → 2-3 lineas con el dato + proximo paso\n"
            "- Pregunta de mensualidad / precio / tarifa → maximo 5 lineas:\n"
            "  (1) Promo 1er llamado: inscripcion $187,51 + mensualidad $197,38, vigente hasta el 31 jul 2026 — SIEMPRE abre con esto\n"
            "  (2) Pregunta cuantos alumnos inscribira; cuando tengas la cifra y el contacto este "
            "identificado, emite ACTION:QUOTE:n y el sistema enviara la cotizacion formal exacta\n"
            "  (3) Menciona el convenio de pago del 1er llamado (planifica sus fechas; se firma en la institucion)\n"
            "- Dificultad economica / queja → 3-4 lineas, calidas, sin enumerar pasos\n"
            "- Despedida → 1 linea, nada mas\n"
            "- Cualquier otra consulta → maximo 5 lineas\n"
            "PROHIBIDO:\n"
            "- Reintroducirte si ya te presentaste antes en la misma conversacion\n"
            "- Repetir la pregunta del cliente antes de responderla\n"
            "- Dar contexto que no pidio\n"
            "- Enumerar mas de 3 cosas en una respuesta\n"
            "- Usar mas de un emoji por mensaje\n"
            "Ejemplos:\n"
            "  ❌ MAL (consulta de saldo): 'Hola Maria! Entiendo que deseas conocer tu estado de cuenta. "
            "Con mucho gusto te ayudo. Segun nuestros registros tienes un saldo de $394,76 correspondiente "
            "a los meses de marzo y abril. Te recomendamos ponerte al dia...'\n"
            "  ✅ BIEN: 'Hola Maria. Tienes $394,76 pendiente (marzo y abril). "
            "Para coordinar el pago: pagos@ueipab.edu.ve 😊'\n"
            "- Un solo mensaje por turno: consolida toda tu respuesta en un único mensaje. Nunca envíes dos mensajes seguidos sobre el mismo tema.\n"
            "- PROHIBIDO terminar cualquier respuesta con '¿Hay algo más en lo que pueda ayudarte?', "
            "'¿Puedo ayudarte en algo más?', '¿Necesitas algo más?' o variantes similares. "
            "Si respondiste la consulta, para ahí. El representante sabe que puede escribirte de nuevo.\n"
            "- DESPEDIDA — REGLA ESTRICTA: cuando el cliente envíe cualquiera de estas frases o similares: "
            "'gracias', 'hasta luego', 'hasta pronto', 'feliz día', 'buenas noches', 'nos vemos', 'adiós', "
            "'chao', 'no es todo', 'eso es todo', 'listo', 'ya es todo', 'muchas gracias', 'mil gracias', "
            "'que tengas', 'que tenga', 'igualmente' — responde con UNA SOLA LÍNEA de cierre y NADA MÁS. "
            "PROHIBIDO: añadir preguntas de seguimiento, ofrecer más ayuda, repetir el saludo, ni enviar "
            "mensajes adicionales. La conversación termina ahí.\n"
            "  ❌ MAL: '¡Hasta pronto! ¿Puedo ayudarte en algo más hoy? ¡Que tengas un excelente día!'\n"
            "  ✅ BIEN: '¡Hasta pronto!'\n"
            "  ❌ MAL: 'Fue un placer. Si necesitas algo más, aquí estaré. ¡Hasta luego!'\n"
            "  ✅ BIEN: '¡Con mucho gusto! ¡Hasta luego!'\n"
            "- No insistas después del cierre: si el cliente no ha dicho explícitamente adiós pero el tema claramente terminó ('ok', 'listo', 'entendido', 'perfecto'), responde brevemente y espera — no generes más preguntas.\n"
            + (
                "- DEMORAS EN WHATSAPP — REGLA OBLIGATORIA: WhatsApp tiene una demora estructural "
                "de hasta 5 minutos entre mensajes (el sistema revisa de forma periódica). "
                "Si el representante se queja de que tardas mucho, de que no respondes, o pide más rapidez, DEBES: "
                "(1) disculparte brevemente con empatía, "
                "(2) explicar que WhatsApp puede tener hasta 5 minutos de demora por limitaciones técnicas, "
                "(3) recomendar activamente cambiar a Telegram donde las respuestas son instantáneas — "
                "proporcionar el enlace: https://t.me/GlendaUeipabBot (@GlendaUeipabBot). "
                "Ejemplo: 'Disculpa la espera, Maria. WhatsApp tiene una demora técnica de hasta 5 minutos. "
                "Para respuestas al instante, te invito a escribirme por Telegram: https://t.me/GlendaUeipabBot — "
                "es gratis, igual de seguro y respondo de inmediato.'\n"
                if conversation.channel == 'whatsapp' else ''
            )
            + "- No uses emojis decorativos, excepto los numeros del menu de bienvenida (1️⃣, 2️⃣, 3️⃣, 4️⃣, 5️⃣). No reveles que eres un sistema automatico a menos que pregunten directamente.\n"
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
        """Welcome menu sent when a conversation is manually started via action_start."""
        saludo = get_ve_greeting()
        agent_name = context.get('agent_name', 'Glenda')
        institution = context.get('institution', 'Instituto Privado Andrés Bello')
        telegram_line = (
            "\n\nPara respuestas al instante, tambien puedes escribirme por Telegram:\n"
            "https://t.me/GlendaUeipabBot"
            if getattr(conversation, 'channel', 'whatsapp') == 'whatsapp'
            else ''
        )
        return (
            f"{saludo}! Soy {agent_name}, asistente virtual del {institution}.\n\n"
            "Puedo ayudarte con lo siguiente:\n\n"
            "1️⃣  Mi estado de cuenta / saldo pendiente\n"
            "2️⃣  Propuesta economica 2026-2027 (opciones, tarifas, votacion)\n"
            "3️⃣  Inscripcion anticipada y matricula\n"
            "4️⃣  Informacion general (horarios, uniformes, cursos)\n"
            "5️⃣  Otro asunto\n\n"
            "Responde con el numero de tu opcion, o escribe directamente tu consulta."
            + telegram_line
        )

    def _extract_visible_text(self, ai_response):
        """Strip all ACTION:* markers from the response before sending to customer."""
        text = re.sub(r'\n?ACTION:\w+[^\n]*', '', ai_response)
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

    @staticmethod
    def _fmt_usd(value):
        """Format 1442.04 → '1.442,04' (Venezuelan separators)."""
        return f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def _handle_quote_action(self, conversation, ai_response, context):
        """Resolve ACTION:QUOTE:<n_students> via sale.order.create_ai_quote (ueipab_sales).

        Returns the formatted quote message (numbers 100% from Odoo products,
        never written by the LLM), an identification request if the contact is
        not verified, or None when no marker is present.
        """
        match = re.search(r'ACTION:QUOTE:(\d+)', ai_response, re.MULTILINE)
        if not match:
            return None
        n_students = int(match.group(1))

        partner = conversation.partner_id
        identified = bool(partner) and not partner.name.startswith(
            ('Consulta WhatsApp', 'Telegram '))
        if not identified:
            return (
                "Para preparar tu cotización formal primero necesito verificar tu "
                "identidad. ¿Me indicas tu cédula, por favor?"
            )

        if 'sale.order' not in conversation.env:
            _logger.error("ACTION:QUOTE: module ueipab_sales/sale not installed")
            return None
        try:
            quote = conversation.env['sale.order'].sudo().create_ai_quote(
                partner.id, n_students, channel=conversation.channel or 'whatsapp')
            conversation.env.cr.commit()
        except Exception as e:
            _logger.error("ACTION:QUOTE failed for conv %d: %s", conversation.id, e)
            return (
                "No pude generar la cotización formal en este momento. "
                "Escríbenos a pagos@ueipab.edu.ve y con gusto te la preparamos."
            )

        conversation.message_post(body=(
            "📋 Cotización generada por Glenda: %s — %d alumno(s) — $%s USD (%s)"
        ) % (quote['name'], n_students, self._fmt_usd(quote['amount_total']),
             quote['llamado_name']))
        return self._format_quote_message(quote)

    def _format_quote_message(self, quote):
        """Build the customer-facing quote message from create_ai_quote()'s dict."""
        label = 'alumno' if quote['n_students'] == 1 else 'alumnos'
        try:
            from datetime import datetime as _dt
            valid = _dt.strptime(quote['validity_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            valid = quote['validity_date']

        lines = [
            f"📋 *Cotización {quote['name']} — Inscripción 2026-2027*",
            f"{quote['llamado_name']} · {quote['n_students']} {label}",
            "",
        ]
        for l in quote['lines']:
            lines.append(
                f"• {l['name']}: {int(l['qty'])} × ${self._fmt_usd(l['price_unit'])}"
                f" = ${self._fmt_usd(l['subtotal'])}"
            )
        lines += [
            "",
            f"💰 *TOTAL PRIMER MES: ${self._fmt_usd(quote['amount_total'])} USD*",
            f"Tarifas válidas hasta el {valid}.",
            "",
            f"⚠ {quote['bcv_note']}",
        ]
        if quote.get('convenio'):
            lines += [
                "",
                "✍️ Con el *convenio de pago* del 1er llamado puedes planificar las "
                "fechas de pago de cada concepto. Las fechas definitivas se acuerdan "
                "y firman en la institución (lunes a viernes). ¡Te esperamos!",
            ]
        return "\n".join(lines)

    def _get_voting_wa_block(self, conversation):
        """Voting period closed 2026-05-26. Direct parents to the results letter."""
        return (
            "CONSULTA PRESUPUESTARIA 2026-2027 — VOTACIÓN CERRADA (26/05/2026):\n"
            "Si el representante menciona la votación, quiere votar, o pregunta por el resultado:\n"
            "\n"
            "FORMATO DE RESPUESTA (úsalo tal cual, adaptando el nombre):\n"
            "---\n"
            "¡Hola, [nombre]! Gracias por su interés en la *Consulta Presupuestaria 2026-2027*.\n"
            "\n"
            "El período de votación concluyó el 26 de mayo y la Opción A fue aprobada. "
            "Los resultados están disponibles en la carta oficial del colegio:\n"
            "📄 https://docs.google.com/document/d/1GSGzXLxGaaMvYtbyJuGki5KFodmpoy5OyHk0fm4e2fg/edit?usp=sharing\n"
            "\n"
            "Para cualquier consulta adicional sobre la propuesta económica, puede escribirnos "
            "a pagos@ueipab.edu.ve con gusto le atendemos. 🙏\n"
            "---\n"
            "\n"
            "REGLA ESTRICTA: NO proceses ni registres ningún voto. El proceso está cerrado.\n"
        )

    def _handle_record_vote(self, conversation, ai_response, context):
        """Record a WA vote when ACTION:RECORD_VOTE:A|B is found in the AI response."""
        match = re.search(r'ACTION:RECORD_VOTE:([AB])\b', ai_response, re.IGNORECASE)
        if not match:
            return
        option   = match.group(1).upper()
        decision = 'continuing' if option == 'A' else 'leaving'

        # Find pending ACK by partner_id first, phone fallback
        Ack = conversation.env['partner.communication.ack'].sudo()
        ack = None
        if conversation.partner_id:
            ack = Ack.search([
                ('notice_key', '=', 'budget_consulta_2026_2027'),
                ('partner_id', '=', conversation.partner_id.id),
                ('state',      '=', 'pending'),
            ], limit=1)
        if not ack and conversation.phone:
            ack = Ack.search([
                ('notice_key',    '=', 'budget_consulta_2026_2027'),
                ('partner_phone', '=', conversation.phone),
                ('state',         '=', 'pending'),
            ], limit=1)
        if not ack:
            _logger.warning("RECORD_VOTE: no pending ACK for conv %d", conversation.id)
            return

        from datetime import datetime as _dt
        notes = (
            f"WhatsApp (Glenda) — conv #{conversation.id} — "
            f"{_dt.now().strftime('%d/%m/%Y %H:%M')}"
        )
        ack._record_decision(decision=decision, channel='whatsapp', notes=notes)
        _logger.info("RECORD_VOTE: conv %d → Opción %s recorded for %s",
                     conversation.id, option, ack.partner_name)

        # Best-effort: close the FreeScout monitoring conversation
        if ack.freescout_conv_id:
            self._close_freescout_vote_conv(conversation, ack, option)

    def _close_freescout_vote_conv(self, conversation, ack, option):
        """Add internal note + close the FreeScout votacion@ conv for this ACK."""
        try:
            import requests as _req
            from datetime import datetime as _dt
            icp     = conversation.env['ir.config_parameter'].sudo()
            fs_url  = icp.get_param('ai_agent.freescout_api_url', '').rstrip('/')
            fs_key  = icp.get_param('ai_agent.freescout_api_key', '')
            if not fs_url or not fs_key:
                return
            headers = {'X-FreeScout-API-Key': fs_key,
                       'Content-Type': 'application/json',
                       'Accept': 'application/json'}
            fs_id   = int(ack.freescout_conv_id)
            dt      = _dt.now().strftime('%d/%m/%Y %H:%M')
            note    = (
                f'✅ <strong>Voto registrado vía WhatsApp</strong><br>'
                f'Opción <strong>{option}</strong> — {ack.partner_name} — {dt}<br>'
                f'Glenda conv #{conversation.id}'
            )
            _req.post(f'{fs_url}/conversations/{fs_id}/threads',
                      json={'type': 'note', 'text': note, 'user': 10},
                      headers=headers, timeout=10)
            _req.put(f'{fs_url}/conversations/{fs_id}',
                     json={'status': 'closed', 'byUser': 10},
                     headers=headers, timeout=10)
            _logger.info("FreeScout conv %s closed — Opción %s", fs_id, option)
        except Exception as e:
            _logger.warning("Could not close FreeScout vote conv: %s", e)

    def _handle_log_feedback(self, conversation, ai_response, context):
        """Create ai.agent.feedback record if ACTION:LOG_FEEDBACK marker is present."""
        match = re.search(
            r'ACTION:LOG_FEEDBACK:(\w+)\|([^\n]+)',
            ai_response, re.MULTILINE
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

        # Record WA vote if present (before stripping markers)
        self._handle_record_vote(conversation, ai_response, context)

        # Check for balance query — resolve and append to visible text before other actions
        balance_msg = self._handle_balance_action(conversation, ai_response, context)

        # Check for quotation request — generated 100% from Odoo products (ueipab_sales)
        quote_msg = self._handle_quote_action(conversation, ai_response, context)

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
            if quote_msg:
                result['quote_message'] = quote_msg
            return result

        visible_text = self._extract_visible_text(ai_response)
        # If balance query resolved, append the breakdown as a second message
        if balance_msg:
            final_text = visible_text or ai_response
            result = {'message': final_text, 'balance_message': balance_msg}
        else:
            result = {'message': visible_text or ai_response}
        if quote_msg:
            result['quote_message'] = quote_msg
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
