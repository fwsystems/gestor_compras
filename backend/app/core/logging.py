import logging

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure basic process logging without infrastructure details."""
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_startup(settings: Settings) -> None:
    logging.getLogger("app.startup").info(
        "Starting application=%s version=%s environment=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env.value,
    )
