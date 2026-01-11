import hashlib
import inspect
import logging
import pickle
from functools import wraps

from src.settings import get_redis_client


def __make_cache_key(func, args, kwargs):
    """
    Generate a unique cache key based on the function source code and its arguments.
    Avoids pickling non-pickle-able objects.
    """
    # Get function source code as bytes
    src_func = inspect.getsource(func).encode()
    # Safely serialize arguments, fallback to str if pickle fails
    try:
        args_bytes = pickle.dumps(args)
    except Exception:
        args_bytes = str(args).encode()
    try:
        kwargs_bytes = pickle.dumps(tuple(sorted(kwargs.items())))
    except Exception:
        kwargs_bytes = str(tuple(sorted(kwargs.items()))).encode()
    # Combine all parts and hash for uniqueness
    key_bytes = src_func + args_bytes + kwargs_bytes
    key_hash = hashlib.md5(key_bytes).hexdigest()
    return key_hash


def cache_func_wrapper(func=None, *, ex=3600):
    """
    Decorator to cache function results in Redis using a key generated from function source and arguments.
    ex: expiration time in seconds (default 3600s = 1 hour)
    """

    def decorator(inner_func):
        @wraps(inner_func)
        def wrapper(*args, **kwargs):
            # Check for no_cache flag in kwargs
            no_cache = kwargs.pop("no_cache", False)
            # Get Redis client instance
            redis_client = get_redis_client()
            # Generate cache key for current function and arguments
            cache_key = __make_cache_key(inner_func, args, kwargs)
            if not no_cache:
                # Try to get cached result from Redis
                cached_result = redis_client.get(cache_key)
                if cached_result is not None:
                    logging.info(f"Cache hit for key: {cache_key}")
                    # Return cached result if available
                    return pickle.loads(cached_result)

            # Call the original function if cache miss
            result = inner_func(*args, **kwargs)

            if not no_cache:
                # Store result in Redis with expiration time
                redis_client.set(cache_key, pickle.dumps(result), ex=ex)
            return result

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)
