import logging
import sys
from typing import Any

from devops_resolver.shared.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structured JSON logging once at application startup."""

    root_logger = logging.getLogger()
    if root_logger.__dict__.get("_devops_resolver_configured", False):
        return

    handler = logging.StreamHandler(sys.stdout)
    try:
        from pythonjsonlogger.json import JsonFormatter

        handler.setFormatter(
            JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s "
                "%(incident_id)s %(agent)s %(tool)s"
            )
        )
    except ModuleNotFoundError:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s "
                "incident_id=%(incident_id)s agent=%(agent)s tool=%(tool)s"
            )
        )
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())
    root_logger.__dict__["_devops_resolver_configured"] = True


def log_extra(**values: Any) -> dict[str, Any]:
    return {
        "incident_id": values.get("incident_id", ""),
        "agent": values.get("agent", ""),
        "tool": values.get("tool", ""),
    }
