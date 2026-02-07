from datetime import datetime, timezone, timedelta

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
    return full_name.strip().split()[0]


# Import skill modules to trigger registration
from . import bounce_resolution
from . import bill_reminder
from . import billing_support
