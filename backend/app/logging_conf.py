import logging
import sys

from app.config import get_settings


def configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().devfoundry_log_level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
