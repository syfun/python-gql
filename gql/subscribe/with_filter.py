from functools import wraps
from typing import Any, AsyncIterator, Awaitable, Callable, Dict

ResolverFn = Callable[[Any, Any, Dict[str, Any]], Awaitable[AsyncIterator]]
FilterFn = Callable[[Any, Any, Dict[str, Any]], bool]


def with_filter(filter_fn: FilterFn) -> Callable[[ResolverFn], ResolverFn]:
    def wrap(func: ResolverFn) -> ResolverFn:
        @wraps(func)
        async def _wrap(parent: Any, info: Any, **kwargs: Any) -> Awaitable[AsyncIterator]:
            iterator = await func(parent, info, **kwargs)
            async for result in iterator:
                if filter_fn(result, info, **kwargs):
                    yield result

        return _wrap

    return wrap
