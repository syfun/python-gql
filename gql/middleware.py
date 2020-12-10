from functools import partial, reduce
from inspect import isfunction
from typing import Callable, Iterator, Any, Dict, List

from graphql.execution.middleware import MiddlewareManager as BaseMiddlewareManager

GraphQLFieldResolver = Callable[..., Any]


class MiddlewareManager(BaseMiddlewareManager):
    middlewares: dict
    exclude: List[str]

    def __init__(self, middlewares: Dict[str, list], exclude: List[str] = None):
        assert isinstance(middlewares, dict), f'MiddlewareManager expected dict, not {type(middlewares)}'
        self.middlewares = {
            key: list(get_middleware_resolvers(value)) if value else None for key, value in middlewares.items()
        }
        self._cached_resolvers = {}
        self.exclude = exclude or []

    def get_field_resolver_by_parent(
        self, field_resolver: GraphQLFieldResolver, parent_type: str, field_name: str
    ) -> GraphQLFieldResolver:
        field = f'{parent_type}.{field_name}'
        if field in self.exclude or parent_type not in self.middlewares and field not in self.middlewares:
            return field_resolver

        if field_resolver not in self._cached_resolvers:
            middlewares = self.middlewares[parent_type] if parent_type in self.middlewares else self.middlewares[field]
            self._cached_resolvers[field_resolver] = reduce(
                lambda chained_fns, next_fn: partial(next_fn, chained_fns),
                middlewares,
                field_resolver,
            )
        return self._cached_resolvers[field_resolver]


def get_middleware_resolvers(middlewares: list) -> Iterator[Callable]:
    """Get a list of resolver functions from a list of classes or functions."""
    for middleware in middlewares:
        if isfunction(middleware):
            yield middleware
        else:  # middleware provided as object with 'resolve' method
            resolver_func = getattr(middleware, "resolve", None)
            if resolver_func is not None:
                yield resolver_func
