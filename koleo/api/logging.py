import logging


class LoggingMixin:
    _l: logging.Logger
    _l_name: str | None = None

    def __init__(self, name: str | None = None) -> None:
        if name:
            self._l_name = name

    @property
    def logger(self) -> logging.Logger:
        if not getattr(self, "_l", None):
            self._l = logging.getLogger(self.logger_name)
        return self._l

    @property
    def logger_name(self) -> str:
        return getattr(self, "_l_name", None) or self.__class__.__name__.lower()

    def dl(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def create_logging_context(self, prefix: str) -> "ContextLogger":
        return ContextLogger(self.logger, prefix)


class ContextLogger:
    def __init__(self, logger: logging.Logger, prefix: str) -> None:
        self.logger = logger
        self.prefix = prefix

    def _make_msg(self, msg: str):
        return f"{self.prefix}: {msg}"

    def dl(self, msg, *args, **kwargs):
        self.logger.debug(self._make_msg(msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(self._make_msg(msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(self._make_msg(msg), *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self.logger.warning(self._make_msg(msg), *args, **kwargs)
