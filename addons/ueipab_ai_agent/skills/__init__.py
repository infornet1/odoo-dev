import calendar
import re
from datetime import datetime, timezone, timedelta, date

SKILL_REGISTRY = {}

# Venezuela timezone: UTC-4
VE_TZ = timezone(timedelta(hours=-4))


def register_skill(code):
    """Decorator to register a skill handler class."""
    def decorator(cls):
        SKILL_REGISTRY[code] = cls()
        return cls
    return decorator


def get_skill(code):
    """Get a registered skill handler by code."""
    return SKILL_REGISTRY.get(code)


def get_ve_greeting():
    """Return time-appropriate greeting for Venezuela (UTC-4).

    6:00-11:59  -> Buenos días
    12:00-17:59 -> Buenas tardes
    18:00-5:59  -> Buenas noches
    """
    hour = datetime.now(VE_TZ).hour
    if 6 <= hour < 12:
        return "Buenos días"
    elif 12 <= hour < 18:
        return "Buenas tardes"
    return "Buenas noches"


def get_first_name(full_name):
    """Extract first name from a full name string."""
    if not full_name:
        return "estimado/a"
    return full_name.strip().split()[0].title()


def normalize_ve_phone(phone_str):
    """Normalize Venezuelan phone to +58 XXX XXXXXXX format.

    Accepted inputs: 04142337463, 0414-233-7463, 584142337463, +584142337463
    Output: +58 414 2337463
    Returns None if input cannot be parsed as a valid VE phone.
    """
    if not phone_str:
        return None
    digits = re.sub(r'[^0-9]', '', phone_str)
    # Strip leading country code
    if digits.startswith('58') and len(digits) == 12:
        digits = digits[2:]  # remove 58 prefix
    elif digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]  # remove leading 0
    if len(digits) != 10:
        return None
    # VE mobile area codes: 412, 414, 416, 424, 426 (main carriers)
    area = digits[:3]
    number = digits[3:]
    return f"+58 {area} {number}"


def validate_rif_format(rif_str):
    """Validate Venezuelan RIF format.

    Accepts with or without dashes (V-15128008-7, V151280087, V15128008-7).
    Returns official convention format without dashes: V151280087.
    """
    if not rif_str:
        return None
    clean = rif_str.strip().upper().replace(' ', '')
    # Remove dashes for validation
    nodash = clean.replace('-', '')
    # Pattern: letter + 8-9 digits (last digit is check digit)
    m = re.match(r'^([VEJGPC])(\d{8,9})$', nodash)
    if not m:
        return None
    prefix = m.group(1)
    num = m.group(2)
    # Official VE convention: no dashes (e.g. V151280087)
    return f"{prefix}{num}"


def parse_ve_address(address_str):
    """Parse a Venezuelan address string into structured components.

    Extracts city, state, and zip code from free-text addresses commonly
    found on RIF documents, leaving the street portion clean.

    Input:  "Calle 20 Sur Casa La Perdomera Nro 40 Urb Pueblo Nuevo Sur
             El Tigre Anzoategui Zona Postal 6050"
    Output: {
        'street': 'Calle 20 Sur Casa La Perdomera Nro 40 Urb Pueblo Nuevo Sur',
        'city': 'El Tigre',
        'state_code': 'V01',
        'zip': '6050',
    }
    """
    if not address_str:
        return {'street': '', 'city': '', 'state_code': '', 'zip': ''}

    text = address_str.strip()

    # --- Extract zip code ---
    zip_code = ''
    # "ZONA POSTAL 6050" or "ZONA POSTAL: 6050" or "CP 6050"
    m = re.search(r'(?:ZONA\s+POSTAL|C\.?P\.?)\s*:?\s*(\d{4,5})', text, re.IGNORECASE)
    if m:
        zip_code = m.group(1)
        text = text[:m.start()].rstrip(' ,.-') + text[m.end():]
    else:
        # Trailing 4-digit number at end
        m = re.search(r'\b(\d{4})\s*$', text)
        if m:
            zip_code = m.group(1)
            text = text[:m.start()].rstrip(' ,.-')

    # --- Venezuelan states mapping (name variants → Odoo code) ---
    # Odoo codes: V01=Amazonas, V02=Anzoátegui, ..., V24=Zulia
    VE_STATES = {
        'AMAZONAS': 'V01', 'ANZOATEGUI': 'V02', 'ANZOÁTEGUI': 'V02',
        'APURE': 'V03', 'ARAGUA': 'V04', 'BARINAS': 'V05',
        'BOLIVAR': 'V06', 'BOLÍVAR': 'V06', 'CARABOBO': 'V07',
        'COJEDES': 'V08', 'DELTA AMACURO': 'V09', 'DISTRITO CAPITAL': 'V10',
        'FALCON': 'V11', 'FALCÓN': 'V11', 'GUARICO': 'V12', 'GUÁRICO': 'V12',
        'LARA': 'V13', 'MERIDA': 'V14', 'MÉRIDA': 'V14',
        'MIRANDA': 'V15', 'MONAGAS': 'V16', 'NUEVA ESPARTA': 'V17',
        'PORTUGUESA': 'V18', 'SUCRE': 'V19', 'TACHIRA': 'V20', 'TÁCHIRA': 'V20',
        'TRUJILLO': 'V21', 'VARGAS': 'V22', 'LA GUAIRA': 'V22',
        'YARACUY': 'V23', 'ZULIA': 'V24',
    }

    state_code = ''
    for state_name, code in sorted(VE_STATES.items(), key=lambda x: -len(x[0])):
        pattern = r'\b' + re.escape(state_name) + r'\b'
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            state_code = code
            text = text[:m.start()].rstrip(' ,.-') + text[m.end():]
            break

    # --- Known cities (longest first to avoid partial matches) ---
    VE_CITIES = [
        'SAN JOSE DE GUANIPA', 'SAN TOME', 'SAN TOMÉ',
        'PUERTO LA CRUZ', 'BARCELONA', 'PUERTO ORDAZ',
        'CIUDAD BOLIVAR', 'CIUDAD BOLÍVAR',
        'EL TIGRE', 'EL TIGRITO', 'CARACAS', 'MARACAIBO',
        'VALENCIA', 'MARACAY', 'BARQUISIMETO', 'MATURIN', 'MATURÍN',
        'CUMANA', 'CUMANÁ',
    ]

    city = ''
    for city_name in VE_CITIES:
        pattern = r'\b' + re.escape(city_name) + r'\b'
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            city = city_name.title()
            text = text[:m.start()].rstrip(' ,.-') + text[m.end():]
            break

    # Clean up leftover whitespace/punctuation
    street = re.sub(r'\s{2,}', ' ', text).strip().rstrip(' ,.-')

    return {
        'street': street,
        'city': city,
        'state_code': state_code,
        'zip': zip_code,
    }


def parse_cedula_expiry(expiry_str):
    """Convert Venezuelan cedula expiry MM/YYYY to last day of month.

    Input: '06/2035' or '06-2035' or '6/2035'
    Output: date(2035, 6, 30)
    Returns None if cannot parse.
    """
    if not expiry_str:
        return None
    clean = expiry_str.strip().replace('-', '/')
    m = re.match(r'^(\d{1,2})/(\d{4})$', clean)
    if not m:
        return None
    month = int(m.group(1))
    year = int(m.group(2))
    if month < 1 or month > 12 or year < 2000 or year > 2100:
        return None
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


# Import skill modules to trigger registration
from . import bounce_resolution
from . import bill_reminder
from . import billing_support
from . import hr_data_collection
