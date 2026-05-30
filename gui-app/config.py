import json
import os
from pathlib import Path

_CONFIG_DIR = Path.home() / '.ppt-remote'
_CONFIG_FILE = _CONFIG_DIR / 'config.json'

DEFAULTS = {
    'gateway_url': os.environ.get('PPT_REMOTE_GATEWAY', 'ws://localhost:5000'),
}


def load() -> dict:
    try:
        return {**DEFAULTS, **json.loads(_CONFIG_FILE.read_text())}
    except Exception:
        return dict(DEFAULTS)


def save(data: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = {**load(), **data}
    _CONFIG_FILE.write_text(json.dumps(merged, indent=2))
