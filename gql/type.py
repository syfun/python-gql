import dataclasses
from functools import partial
from typing import TypeVar, Union

from graphql import GraphQLInputObjectType, GraphQLInterfaceType, GraphQLObjectType
from graphql.utilities.schema_printer import print_type

from .constants import IS_GRAPHQL_FIELD, IS_GRAPHQL_INPUT, IS_GRAPHQL_INTERFACE
from .field import field, gql_field, asdict, pop_empty_dict
from .type_converter import REGISTRY
from .utils.str_converters import to_camel_case


def _get_resolver(cls, field_name):
    class_field = getattr(cls, field_name, None)

    if class_field and getattr(class_field, "resolver", None):
        return class_field.resolver

    def _resolver(root, info):
        field_resolver = getattr(root or cls(), field_name, None)

        if getattr(field_resolver, IS_GRAPHQL_FIELD, False):
            return field_resolver(root, info)

        elif field_resolver.__class__ is gql_field:
            # TODO: support default values
            return None

        return field_resolver

    return _resolver


def _get_resolve_type(cls):
    def _resolve_type(instance, info, source):
        return instance.field

    return getattr(cls, 'resolve_type', None) or _resolve_type


ObjectType = TypeVar('ObjectType')
Interface = TypeVar('Interface')
Input = TypeVar('Input')

GQLType = Union[ObjectType, Interface, Input]


def _process_type(
    cls, *, is_input=False, is_interface=False, name=None, description=None
) -> GQLType:
    name = name or cls.__name__
    REGISTRY[name] = cls

    def repr_(self):
        return print_type(self.field)

    setattr(cls, "_print_type", repr_)

    def pop_empty(self, recursive=True) -> dict:
        return pop_empty_dict(asdict(self, recursive=recursive))

    setattr(cls, "pop_empty", pop_empty)

    def _get_fields(wrapped):
        class_fields = dataclasses.fields(wrapped)

        fields = {}

        for class_field in class_fields:
            field_name = getattr(class_field, "field_name", None) or to_camel_case(class_field.name)
            description = getattr(class_field, "field_description", None)

            resolver = getattr(class_field, "field_resolver", None) or _get_resolver(cls, class_field.name)
            resolver.__annotations__["return"] = class_field.type

            fields[field_name] = field(resolver, is_input=is_input, description=description).field

        gql_fields = {}
        for klass in cls.__mro__[1:-1]:
            if getattr(klass, IS_GRAPHQL_INTERFACE, False):
                continue
            for key, value in klass.__dict__.items():
                if getattr(value, IS_GRAPHQL_FIELD, False):
                    gql_fields[key] = value
        gql_fields.update(
            {key: value for key, value in cls.__dict__.items() if getattr(value, IS_GRAPHQL_FIELD, False)}
        )

        for key, value in gql_fields.items():
            name = getattr(value, "field_name", None) or to_camel_case(key)

            fields[name] = value.field

        return fields

    if is_input:
        setattr(cls, IS_GRAPHQL_INPUT, True)
    elif is_interface:
        setattr(cls, IS_GRAPHQL_INTERFACE, True)

    extra_kwargs = {"description": description or cls.__doc__}

    if is_input:
        TypeClass = GraphQLInputObjectType
    elif is_interface:
        TypeClass = GraphQLInterfaceType
        extra_kwargs['resolve_type'] = _get_resolve_type(cls)
    else:
        TypeClass = GraphQLObjectType

        extra_kwargs["interfaces"] = [
            klass.field for klass in cls.__bases__ if getattr(klass, IS_GRAPHQL_INTERFACE, False)
        ]

    wrapped = dataclasses.dataclass(cls)
    wrapped.field = TypeClass(name, lambda: _get_fields(wrapped), **extra_kwargs)

    return wrapped


def type(_cls=None, *, is_input=False, is_interface=False, name=None, description=None):
    """Annotates a class as a GraphQL type.

    Example usage:

    >>> @gql.type:
    >>> class X:
    >>>     field_abc: str = "ABC"
    """

    def wrap(cls) -> GQLType:
        return _process_type(
            cls,
            is_input=is_input,
            is_interface=is_interface,
            name=name,
            description=description,
        )

    if _cls is None:
        return wrap

    return wrap(_cls)


input = partial(type, is_input=True)
interface = partial(type, is_interface=True)
