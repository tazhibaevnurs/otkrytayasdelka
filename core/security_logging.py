"""Структурированные записи для security-логгера (JSON через LOGGING)."""

import logging

logger = logging.getLogger('security')


def log_event(event: str, **fields):
    """Событие безопасности: event + плоские поля в extra для JSON-форматтера."""
    logger.info(
        event,
        extra={
            'event': event,
            **{k: v for k, v in fields.items() if v is not None},
        },
    )


def log_warning_event(event: str, **fields):
    logger.warning(
        event,
        extra={
            'event': event,
            **{k: v for k, v in fields.items() if v is not None},
        },
    )
