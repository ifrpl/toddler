
from functools import wraps
import traceback

__all__ = ['run_only_once', 'has_been_run']


def _set_already_run_flag(func):
    setattr(func, '_already_run', True)
    try:
        setattr(func, '_last_call_trace', ''.join(traceback.format_stack()))
    except TypeError:
        pass


def run_only_once(arg):
    """
    === Run only once ===
    Make sure that this function will run only once
    If it was run it will raise exception
    :param arg: function to wrap or a boolean that indicates if it should
     raise an exception
    :return decorator:
    """

    if isinstance(arg, bool):
        should_not_raise_exception = arg
    else:
        should_not_raise_exception = False

    def decorator(func):
        nonlocal should_not_raise_exception
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal should_not_raise_exception
            if getattr(func, '_already_run', False):
                if not should_not_raise_exception:
                    raise SystemError(
                        "{} has been already run once here: {}".format(
                            func,
                            getattr(func, '_last_call_trace', '')
                        )
                    )
                else:
                    return None

            _set_already_run_flag(func)
            return func(*args, **kwargs)

        return wrapper

    if callable(arg):
        return decorator(arg)
    else:
        return decorator


def _reset_already_run(func):
    return setattr(func.__wrapped__, '_already_run', False)


def has_been_run(func):
    """
    Checker if func wrapped with `run_only_once` was already run

    :param func:
    :return:
    """
    return getattr(func.__wrapped__, '_already_run', False)