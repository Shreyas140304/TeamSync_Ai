import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from uuid import uuid4

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "teamsync.log"


def setup_logging():
    logger = logging.getLogger("teamsync")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


logger = setup_logging()


def log_event(level, event, request_id=None, **details):
    """Write a structured event without logging secrets."""
    request_id = request_id or str(uuid4())[:8]

    safe_details = " ".join(
        f"{key}={value}"
        for key, value in details.items()
        if value is not None
    )

    message = f"event={event} request_id={request_id}"
    if safe_details:
        message += f" {safe_details}"

    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message)

    return request_id