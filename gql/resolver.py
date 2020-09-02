import traceback
from collections import defaultdict
from enum import Enum
from functools import partial, wraps
from inspect import iscoroutinefunction, isfunction
from typing import Any, Callable, Dict, Mapping, Union

from graphql import (
    GraphQLFieldResolver,
    GraphQLResolveInfo,
    GraphQLSchema,
    GraphQLTypeResolver,
    assert_interface_type,
    assert_object_type,
    assert_union_type,
    is_interface_type,
    is_object_type,
    is_union_type,
)

from .utils import execute_async_function, recursive_to_snake_case, to_camel_case, to_snake_case

ReferenceResolver = Callable[[Any, GraphQLResolveInfo, dict], Any]
FieldResolverMap = Dict[str, Dict[str, GraphQLFieldResolver]]
TypeResolverMap = Dict[str, GraphQLTypeResolver]
ReferenceResolverMap = Dict[str, ReferenceResolver]

field_resolver_map: FieldResolverMap = defaultdict(dict)
type_resolver_map: TypeResolverMap = {}
reference_resolver_map: ReferenceResolverMap = {}


def reference_resolver(type_name: str):
    def wrap(func: ReferenceResolver):
        @wraps(func)
        def sync_resolver(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                traceback.print_exc()
                raise exc

        @wraps(func)
        async def async_resolver(*args, **kwargs):
            try:
                return await execute_async_function(func, *args, **kwargs)
            except Exception as exc:
                traceback.print_exc()
                raise exc

        if iscoroutinefunction(func):
            reference_resolver_map[type_name] = async_resolver
            return async_resolver
        reference_resolver_map[type_name] = sync_resolver
        return sync_resolver

    return wrap


def type_resolver(type_name: str):
    def wrap(func):
        type_resolver_map[type_name] = func
        return func

    return wrap


def field_resolver(
    type_name: str,
    func_or_field: Union[GraphQLFieldResolver, str] = None,
    print_exc: bool = True,
    snake_argument: bool = True,
):
    def wrap(func: GraphQLFieldResolver):
        @wraps(func)
        def sync_resolver(*args, **kwargs):
            if snake_argument:
                kwargs = recursive_to_snake_case(kwargs)
            if not print_exc:
                return func(*args, **kwargs)

            try:
                return func(*args, **kwargs)
            except Exception as exc:
                traceback.print_exc()
                raise exc

        @wraps(func)
        async def async_resolver(*args, **kwargs):
            if snake_argument:
                kwargs = recursive_to_snake_case(kwargs)
            if not print_exc:
                return await execute_async_function(func, *args, **kwargs)

            try:
                return await execute_async_function(func, *args, **kwargs)
            except Exception as exc:
                traceback.print_exc()
                raise exc

        if isinstance(func_or_field, str):
            name = to_camel_case(func_or_field or func.__name__)
        else:
            name = to_camel_case(func.__name__)

        if iscoroutinefunction(func):
            field_resolver_map[type_name][name] = async_resolver
            return async_resolver

        field_resolver_map[type_name][name] = sync_resolver
        return sync_resolver

    if isfunction(func_or_field):
        return wrap(func_or_field)

    return wrap


mutate = partial(field_resolver, 'Mutation')
query = partial(field_resolver, 'Query')
subscribe = partial(field_resolver, 'Subscription')


def register_reference_resolvers(schema: GraphQLSchema):
    for type_name, resolver in reference_resolver_map.items():
        type_ = schema.get_type(type_name)
        type_.__resolve_reference__ = resolver


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
                continue
            if type_name == 'Subscription':
                field.subscribe = field_resolver
            else:
                field.resolve = field_resolver


def register_resolvers(schema: GraphQLSchema):
    register_field_resolvers(schema)
    register_type_resolvers(schema)
    register_reference_resolvers(schema)


def get_field_value(source, field_name):
    return (
        source.get(field_name) if isinstance(source, Mapping) else getattr(source, field_name, None)
    )


def default_field_resolver(source, info, **args):
    """Default field resolver.

    If a resolve function is not given, then a default resolve behavior is used which
    takes the property of the source object of the same name as the field and returns
    it as the result, or if it's a function, returns the result of calling that function
    while passing along args and context.

    For dictionaries, the field names are used as keys, for all other objects they are
    used as attribute names.
    """
    # Ensure source is a value for which property access is acceptable.
    value = get_field_value(source, to_snake_case(info.field_name))
    if value is None:
        value = get_field_value(source, info.field_name)

    if callable(value):
        return value(info, **args)
    if isinstance(value, Enum):
        return value.value
    return value
