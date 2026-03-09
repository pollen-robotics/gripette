"""Entry point for `python -m grabette_gripper`."""

import logging

from .config import settings
from .server import serve

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
serve()
