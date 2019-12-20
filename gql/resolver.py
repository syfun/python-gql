from collections import defaultdict
from functools import wraps
from inspect import iscoroutine, iscoroutinefunction, isawaitable
from typing import Dict

from graphql import GraphQLFieldResolver, GraphQLSchema, is_object_type, is_interface_type, assert_object_type, \
    assert_interface_type

from .utils import to_camel_case, recursive_to_camel_case

FieldResolverMap = Dict[str, Dict[str, GraphQLFieldResolver]]

resolver_map: FieldResolverMap = defaultdict(dict)


def resolver(type_name: str, field_name: str = '', to_camel: bool = True):
    def _resolver(func: GraphQLFieldResolver):
        @wraps(func)
        async def __resolver(*args, **kwargs):
            result = func(*args, **kwargs)
            if isawaitable(result):
                result = await result
            if to_camel:
                result = recursive_to_camel_case(result)
            return result

        name = to_camel_case(field_name or func.__name__)
        resolver_map[type_name][name] = __resolver
        return __resolver

    return _resolver


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
            field.resolve = field_resolver
