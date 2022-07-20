import time
from typing import Callable, Dict, Tuple, Type


def assert_stops_raising(
    fn: Callable,
    args: Tuple = (),
    kwargs: Dict = None,
    exception_type: Type[Exception] = Exception,
    timeout: float = 20,
    interval: float = 2,
) -> None:
    """Assert that ``fn`` returns successfully within ``timeout``
    seconds, trying every ``interval`` seconds.
    If ``exception_type`` is provided, fail unless the exception thrown is
    an instance of ``exception_type``.
    """
    if kwargs is None:
        kwargs = {}

    give_up = time.time() + timeout
    while True:
        try:
            return fn(*args, **kwargs)
        except exception_type:
            if time.time() >= give_up:
                raise
        time.sleep(interval)
