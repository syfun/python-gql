import re


# Adapted from this response in Stackoverflow
# http://stackoverflow.com/a/19053800/1072990
def to_camel_case(snake_str):
    components = snake_str.split("_")
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    return components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])


# From this response in Stackoverflow
# http://stackoverflow.com/a/1176023/1072990
def to_snake_case(name):
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def recursive_to_snake_case(d):
    if isinstance(d, list):
        return [recursive_to_snake_case(v) for v in d]
    if not isinstance(d, dict):
        return d

    _d = {}
    for k, v in d.items():
        _d[to_snake_case(k)] = recursive_to_snake_case(v)
    return _d


def to_const(string):
    return re.sub(r"[\W|^]+", "_", string).upper()
