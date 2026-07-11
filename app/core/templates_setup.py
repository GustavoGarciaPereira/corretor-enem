import json
from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _from_json(value):
    """Parse a JSON string into a Python dict."""
    if isinstance(value, str):
        return json.loads(value)
    return value


def _get_attr(obj, name):
    """Get an attribute of an object by name (for dynamic template access)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


# Register custom filters
templates.env.filters["from_json"] = _from_json
templates.env.filters["attr"] = _get_attr
