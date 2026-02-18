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
    """Validate Venezuelan RIF format: V-12345678-9 or V123456789.

    Accepts with or without dashes. Returns normalized form V-XXXXXXXX-X
    or None if invalid.
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
    if len(num) == 9:
        return f"{prefix}-{num[:8]}-{num[8]}"
    # 8 digits — no check digit provided, still valid
    return f"{prefix}-{num}"


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
