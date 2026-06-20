from functools import wraps
from fastapi import Response
from typing import Optional, Callable, Any

def cache_control(max_age: int, public: bool = True, stale_while_revalidate: Optional[int] = None):
    """
    FastAPI decorator to automatically set Cache-Control headers on responses.

    For endpoints returning raw data (dicts, Pydantic models), the endpoint
    function must explicitly include a 'response: Response' parameter in its signature
    for this decorator to inject the headers.
    """
    directives = [
        "public" if public else "private",
        f"max-age={max_age}"
    ]
    if stale_while_revalidate:
        directives.append(f"stale-while-revalidate={stale_while_revalidate}")
    cache_header_value = ", ".join(directives)

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract the FastAPI Response object if passed as a keyword argument
            response: Optional[Response] = kwargs.get("response")

            res = func(*args, **kwargs)

            # Prioritize modifying the directly returned Response object.
            # Fallback to the injected response parameter if the endpoint returns raw data.
            if isinstance(res, Response):
                res.headers["Cache-Control"] = cache_header_value
            elif response:
                response.headers["Cache-Control"] = cache_header_value

            return res
        return wrapper
    return decorator