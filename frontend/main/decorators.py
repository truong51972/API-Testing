from functools import wraps

def set_test_suites_show(show):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            setattr(request, '_test_suites_show', show)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
