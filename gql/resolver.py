from collections import defaultdict
from enum import Enum
from functools import partial, wraps
from inspect import isawaitable, isclass
from typing import Dict, Type

from graphql import (
    GraphQLEnumValue,
    GraphQLFieldResolver,
    GraphQLSchema,
    GraphQLTypeResolver,
    assert_enum_type,
    assert_interface_type,
    assert_object_type,
    assert_union_type,
    is_enum_type,
    is_interface_type,
    is_object_type,
    is_union_type,
)

from .utils import recursive_to_camel_case, to_camel_case

FieldResolverMap = Dict[str, Dict[str, GraphQLFieldResolver]]
TypeResolverMap = Dict[str, GraphQLTypeResolver]
EnumResolverMap = Dict[str, Type[Enum]]

field_resolver_map: FieldResolverMap = defaultdict(dict)
type_resolver_map: TypeResolverMap = {}
enum_resolver_map: EnumResolverMap = {}


def type_resolver(type_name: str):
    def wrap(func):
        type_resolver_map[type_name] = func
        return func

    return wrap


def async_field_resolver(
    _func, *, type_name: str = '', field_name: str = '', to_camel: bool = True
):
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
        field_resolver_map[type_name][name] = _resolver
        return _resolver

    if _func is None:
        return wrap
    return wrap(_func)


def field_resolver(_func, *, type_name: str = '', field_name: str = '', to_camel: bool = True):
    def wrap(func: GraphQLFieldResolver):
        @wraps(func)
        def _resolver(*args, **kwargs):
            result = func(*args, **kwargs)
            if to_camel:
                result = recursive_to_camel_case(result)
            return result

        name = to_camel_case(field_name or func.__name__)
        field_resolver_map[type_name][name] = _resolver
        return _resolver

    if _func is None:
        return wrap
    return wrap(_func)


def enum_resolver(_cls):
    # if _cls is a class, use _cls name.
    if isclass(_cls):
        enum_resolver_map[_cls.__name__] = _cls
        return _cls

    # if not, _cls is type name.
    def wrap(cls):
        if isinstance(cls, Enum):
            raise Exception('enum_resolver must resolve a Enum class.')
        enum_resolver_map[_cls] = cls
        return cls

    return wrap


mutate = partial(field_resolver, type_name='Mutation')
query = partial(field_resolver, type_name='Query')
subscribe = partial(field_resolver, type_name='Subscription')

async_mutate = partial(async_field_resolver, type_name='Mutation')
async_query = partial(async_field_resolver, type_name='Query')
async_subscribe = partial(async_field_resolver, type_name='Subscription')


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


def register_enum_resolvers(schema: GraphQLSchema):
    for type_name, type_ in schema.type_map.items():
        if not is_enum_type(type_):
            continue

        type_ = assert_enum_type(type_)
        enum_type = enum_resolver_map.get(type_name)
        if not enum_type:
            _enum_type = {value: GraphQLEnumValue(value) for value in type_.values}
        else:
            _enum_type = {value.name: GraphQLEnumValue(value.value) for value in enum_type}
        type_.values = _enum_type


def register_resolvers(schema: GraphQLSchema):
    register_field_resolvers(schema)
    register_type_resolvers(schema)
    register_enum_resolvers(schema)
