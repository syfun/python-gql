import re
from functools import wraps
from inspect import isawaitable
from typing import Any, Callable, List

from graphql import parse


def gql(value: str) -> str:
    parse(value)
    return value


# Adapted from this response in Stackoverflow
# http://stackoverflow.com/a/19053800/1072990
def to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    # We capitalize the first letter of each component except the first one
    # with the 'capitalize' method and join them together.
    return components[0] + "".join(x.capitalize() if x else "_" for x in components[1:])


def snake_argument(func: Callable) -> Callable:
    @wraps(func)
    async def wrap(*args, **kwargs):
        kwargs = {to_snake_case(k): v for k, v in kwargs.items()}
        return await func(*args, **kwargs)

    return wrap


def recursive_to_camel_case(d: Any) -> Any:
    if isinstance(d, list):
        return [recursive_to_camel_case(v) for v in d]
    if not isinstance(d, dict):
        return d

    _d = {}
    for k, v in d.items():
        _d[to_camel_case(k)] = recursive_to_camel_case(v)
    return _d


# From this response in Stackoverflow
# http://stackoverflow.com/a/1176023/1072990
def to_snake_case(name: str) -> str:
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def recursive_to_snake_case(d: Any) -> Any:
    if isinstance(d, list):
        return [recursive_to_snake_case(v) for v in d]
    if not isinstance(d, dict):
        return d

    _d = {}
    for k, v in d.items():
        _d[to_snake_case(k)] = recursive_to_snake_case(v)
    return _d


def to_const(string: str) -> str:
    return re.sub(r'[\W|^]+', '_', string).upper()


def add_file_to_operations(operations, file_obj, path):
    """Handles the recursive algorithm for adding a file to the operations
    object"""
    if not path:
        if operations is not None:
            raise ValueError('Path in map does not lead to a null value')
        return file_obj
    if isinstance(operations, dict):
        key = path[0]
        sub_dict = add_file_to_operations(operations[key], file_obj, path[1:])
        return new_merged_dict(operations, {key: sub_dict})
    if isinstance(operations, list):
        index = int(path[0])
        sub_item = add_file_to_operations(operations[index], file_obj, path[1:])
        return new_list_with_replaced_item(operations, index, sub_item)
    raise TypeError('Operations must be a dict or a list of dicts')


def new_merged_dict(*dicts):
    """Merges dictionaries into a new dictionary. Necessary for python2 and
    python34 since neither have PEP448 implemented."""
    # Necessary for python2 support
    output = {}
    for d in dicts:
        output.update(d)
    return output


def new_list_with_replaced_item(input_list, index, new_value):
    """Creates new list with replaced item at specified index"""
    output = [i for i in input_list]
    output[index] = new_value
    return output


def place_files_in_operations(operations, files_map, form):
    """Replaces None placeholders in operations with file objects in the files
    dictionary, by following the files_map logic as specified within the 'map'
    request parameter in the multipart request spec"""
    path_to_key_iter = (
        (value.split('.'), key) for (key, values) in files_map.items() for value in values
    )
    # Since add_files_to_operations returns a new dict/list, first define
    # output to be operations itself
    output = operations
    for path, key in path_to_key_iter:
        file_obj = form.get(key)
        output = add_file_to_operations(output, file_obj, path)
    return output


async def execute_async_function(func, *args, **kwargs):
    result = func(*args, **kwargs)
    if isawaitable(result):
        result = await result
    return result


def join_type_defs(type_defs: List[str]) -> str:
    return "\n\n".join(t.strip() for t in type_defs)
