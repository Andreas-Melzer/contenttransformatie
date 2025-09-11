import threading
from functools import wraps

def debounce(wait):
    """Decorator that will postpone a function's execution until after `wait` seconds
    have elapsed since the last time it was invoked."""
    def decorator(fn):
        timer = None
        @wraps(fn)
        def debounced(*args, **kwargs):
            nonlocal timer
            if timer is not None:
                timer.cancel()
            timer = threading.Timer(wait, lambda: fn(*args, **kwargs))
            timer.start()
        return debounced
    return decorator