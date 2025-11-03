import threading
from functools import wraps

def debounce(wait):
    """Decorator that will postpone a function's execution until after `wait` seconds
    have elapsed since the last time it was invoked.
    """
    def decorator(fn):
        timer_attr = f'_debounce_timer_for_{fn.__name__}'

        @wraps(fn)
        def debounced(self, *args, **kwargs):
            """The debounced function."""
            if hasattr(self, timer_attr):
                getattr(self, timer_attr).cancel()

            timer = threading.Timer(wait, lambda: fn(self, *args, **kwargs))
            setattr(self, timer_attr, timer)
            timer.start()

        return debounced
    return decorator