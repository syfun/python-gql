from dataclasses import is_dataclass, MISSING

from gql.utils.typing import is_optional, is_list, get_list_annotation, get_optional_annotation


def get_default_value(field):
    default = field.default
    default_factory = field.default_factory
    if default is MISSING and default_factory is MISSING:
        return None

    if default is not MISSING:
        return default
    if default_factory is not MISSING:
        return default_factory()


def value_to_type(value, cls):
    if is_optional(cls):
        inner = get_optional_annotation(cls)
        return value_to_type(value, inner)

    if is_list(cls):
        if not value:
            return []
        inner = get_list_annotation(cls)
        return [value_to_type(d, inner) for d in value]

    if not is_dataclass(cls):
        return value

    if not value:
        return None

    fields = cls.__dataclass_fields__

    kwargs = {}

    for name, field in fields.items():
        if name not in value:
            kwargs[name] = get_default_value(field)
            continue

        _type = field.type
        if is_dataclass(_type) or is_optional(_type):
            kwargs[name] = value_to_type(value.get(name, {}), _type)
        elif is_list(_type):
            kwargs[name] = value_to_type(value.get(name, []), _type)
        else:
            kwargs[name] = value.get(name)

    return cls(**kwargs)
