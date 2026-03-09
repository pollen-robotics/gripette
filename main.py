"""Entry point for grabette-gripper gRPC service."""

import logging

from grabette_gripper.config import settings
from grabette_gripper.server import serve

if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    serve()
