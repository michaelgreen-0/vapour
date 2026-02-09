import logging
import sys
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


class Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(CustomJsonFormatter())
    logger.addHandler(log_handler)

    def info(self, msg, extra=None, **kwargs):
        if extra is None:
            extra = {}
        kwargs.setdefault("stacklevel", 2)
        self.logger.info(msg, extra=extra, **kwargs)

    def error(self, msg, extra=None, **kwargs):
        if extra is None:
            extra = {}
        kwargs.setdefault("stacklevel", 2)
        self.logger.error(msg, extra=extra, **kwargs)
