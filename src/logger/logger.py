import logging
import regex as re
from pythonjsonlogger import json
from datetime import datetime, timezone


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        pattern = r"[A-Z0-9]{20,}"
        if isinstance(record.msg, str):
            record.msg = re.sub(pattern, "[MASKED]", record.msg)
        if record.args:
            new_args = list(record.args)
            for i, arg in enumerate(new_args):
                if isinstance(arg, str):
                    new_args[i] = re.sub(pattern, "[MASKED]", arg)
            record.args = tuple(new_args)
        return True


class CustomJsonFormatter(json.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        log_record["level"] = record.levelname


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": CustomJsonFormatter,
        },
    },
    "filters": {
        "masking": {
            "()": MaskingFilter,
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
            "filters": ["masking"],
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "": {"handlers": ["console"], "level": "INFO"},
    },
}
