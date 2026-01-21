import logging
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime, timezone

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
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
        kwargs.setdefault('stacklevel', 2)
        self.logger.info(msg, extra=extra, **kwargs)
    
    def error(self, msg, extra=None, **kwargs):
        if extra is None:
            extra = {}
        kwargs.setdefault('stacklevel', 2)
        self.logger.error(msg, extra=extra, **kwargs)
