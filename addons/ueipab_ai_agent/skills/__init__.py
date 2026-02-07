SKILL_REGISTRY = {}


def register_skill(code):
    """Decorator to register a skill handler class."""
    def decorator(cls):
        SKILL_REGISTRY[code] = cls()
        return cls
    return decorator


def get_skill(code):
    """Get a registered skill handler by code."""
    return SKILL_REGISTRY.get(code)


# Import skill modules to trigger registration
from . import bounce_resolution
from . import bill_reminder
from . import billing_support
