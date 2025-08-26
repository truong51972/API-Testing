import hashlib
import inspect
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


def cache_func_wrapper(func):
    """
    Decorator to cache function results in Redis using a key generated from function source and arguments.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get Redis client instance
        redis_client = get_redis_client()
        # Generate cache key for current function and arguments
        cache_key = __make_cache_key(func, args, kwargs)
        # Try to get cached result from Redis
        cached_result = redis_client.get(cache_key)
        if cached_result is not None:
            # Return cached result if available
            return pickle.loads(cached_result)

        # Call the original function if cache miss
        result = func(*args, **kwargs)

        # Store result in Redis with 1 hour expiration
        redis_client.set(cache_key, pickle.dumps(result), ex=3600)
        return result

    return wrapper
