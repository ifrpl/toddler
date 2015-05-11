
from functools import wraps
import traceback

def run_only_once(func):
    """
    === Run only once ===
    Make sure that this function will run only once
    If it was run it will raise exception
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if getattr(func, '_already_run', False):
            raise SystemError("{} has been already run once here: {}".format(
                    func,
                    getattr(func, '_last_call_trace', '')
                )
            )
        setattr(func, '_already_run', True)
        setattr(func, '_last_call_trace', ''.join(traceback.format_stack()))
        return func(*args, **kwargs)

    return wrapper


def _reset_already_run(func):
    return setattr(func.__wrapped__, '_already_run', False)


def has_been_run(func):
    """
    Checker if func wrapped with `run_only_once` was already run

    :param func:
    :return:
    """
    return getattr(func.__wrapped__, '_already_run', False)