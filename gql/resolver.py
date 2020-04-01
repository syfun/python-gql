from collections import defaultdict
from functools import partial, wraps
from inspect import isawaitable, iscoroutinefunction, isfunction
from typing import Dict, Union

from graphql import (
    GraphQLFieldResolver,
    GraphQLSchema,
    GraphQLTypeResolver,
    assert_interface_type,
    assert_object_type,
    assert_union_type,
    is_interface_type,
    is_object_type,
    is_union_type,
)

from .utils import recursive_to_camel_case, to_camel_case

FieldResolverMap = Dict[str, Dict[str, GraphQLFieldResolver]]
TypeResolverMap = Dict[str, GraphQLTypeResolver]

field_resolver_map: FieldResolverMap = defaultdict(dict)
type_resolver_map: TypeResolverMap = {}


def type_resolver(type_name: str):
    def wrap(func):
        type_resolver_map[type_name] = func
        return func

    return wrap


def field_resolver(
    type_name: str, func_or_field: Union[GraphQLFieldResolver, str] = None, to_camel: bool = True
):
    def wrap(func: GraphQLFieldResolver):
        @wraps(func)
        def _resolver(*args, **kwargs):
            result = func(*args, **kwargs)
            if to_camel:
                result = recursive_to_camel_case(result)
            return result

        @wraps(func)
        async def async_resolver(*args, **kwargs):
            result = func(*args, **kwargs)
            if isawaitable(result):
                result = await result
            if to_camel:
                result = recursive_to_camel_case(result)
            return result

        if isinstance(func_or_field, str):
            name = to_camel_case(func_or_field or func.__name__)
        else:
            name = func.__name__

        if iscoroutinefunction(func):
            field_resolver_map[type_name][name] = async_resolver
            return async_resolver

        field_resolver_map[type_name][name] = _resolver
        return _resolver

    if isfunction(func_or_field):
        return wrap(func_or_field)

    return wrap


mutate = partial(field_resolver, 'Mutation')
query = partial(field_resolver, 'Query')
subscribe = partial(field_resolver, 'Subscription')


def register_type_resolvers(schema: GraphQLSchema):
    for type_name, type_resolver in type_resolver_map.items():
        type_ = schema.get_type(type_name)
        if is_interface_type(type_):
            type_ = assert_interface_type(type_)
        elif is_union_type(type_):
            type_ = assert_union_type(type_)
        else:
            continue
        type_.resolve_type = type_resolver


def register_field_resolvers(schema: GraphQLSchema):
    for type_name, field_resolvers in field_resolver_map.items():
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


def register_resolvers(schema: GraphQLSchema):
    register_field_resolvers(schema)
    register_type_resolvers(schema)
