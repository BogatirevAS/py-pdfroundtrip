import signal
import sys
from functools import wraps
from typing import Callable, ParamSpec, TypeVar
from logger import LoggerMixin


P = ParamSpec("P")
R = TypeVar("R")
_HAS_ALARM = hasattr(signal, "SIGALRM")


class CustomTimeoutException(Exception):
    pass


class CustomTimeout(LoggerMixin):
    """
    A custom timeout used as a fuse against hanging problematic functions.
    Only unix systems.

    :param int timeout: Time in seconds
    """
    def __init__(self, timeout=5):
        self.timeout = timeout

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        if not _HAS_ALARM:
            return func

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            def handler(signum, frame):
                raise CustomTimeoutException("Custom timeout is over!")

            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(self.timeout)
            try:
                return func(*args, **kwargs)
            except CustomTimeoutException as exc:
                self.logger.exception(exc)
                sys.exit(1)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

        return wrapper
