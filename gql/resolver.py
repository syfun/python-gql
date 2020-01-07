from collections import defaultdict
from functools import partial, wraps
from inspect import isawaitable
from typing import Dict

from graphql import (
    GraphQLFieldResolver,
    GraphQLSchema,
    assert_interface_type,
    assert_object_type,
    is_interface_type,
    is_object_type,
)

from .utils import recursive_to_camel_case, to_camel_case

FieldResolverMap = Dict[str, Dict[str, GraphQLFieldResolver]]

resolver_map: FieldResolverMap = defaultdict(dict)


def resolver(_func, *, type_name: str = '', field_name: str = '', to_camel: bool = True):
    def wrap(func: GraphQLFieldResolver):
        @wraps(func)
        async def _resolver(*args, **kwargs):
            result = func(*args, **kwargs)
            if isawaitable(result):
                result = await result
            if to_camel:
                result = recursive_to_camel_case(result)
            return result

        name = to_camel_case(field_name or func.__name__)
        resolver_map[type_name][name] = _resolver
        return _resolver

    if _func is None:
        return wrap
    return wrap(_func)


mutate = partial(resolver, type_name='Mutation')
query = partial(resolver, type_name='Query')
subscribe = partial(resolver, type_name='Subscription')


def register_resolvers(schema: GraphQLSchema):
    for type_name, field_resolvers in resolver_map.items():
        type_ = schema.get_type(type_name)
        if is_object_type(type_):
            type_ = assert_object_type(type_)
        elif is_interface_type(type_):
            type_ = assert_interface_type(type_)
        else:
            continue

        for name, field_resolver in field_resolvers.items():
            field = type_.fields.get(name)
            if not field:
                return
            if type_name == 'Subscription':
                field.subscribe = field_resolver
            else:
                field.resolve = field_resolver
