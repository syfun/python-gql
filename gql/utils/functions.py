import time
from functools import wraps
from typing import cast

from graphql import GraphQLType, is_non_null_type, is_list_type, GraphQLWrappingType, is_wrapping_type, get_named_type, is_leaf_type


def spent(name):
    def _spent(func):
        @wraps(func)
        def __spent(*args, **kwargs):
            start = time.time()
            r = func(*args, **kwargs)
            end = time.time()
            print(f'{name} spent millisecond ...', int((end - start) * 1000))
            return r

        return __spent

    return _spent


def construct_request(query, variables=None, operation=''):
    return {'operationName': operation, 'query': query, 'variables': variables or {}}


SCALAR_MAP = {
    'String': 'Text',
    'Int': 'int',
    'Float': 'float',
    'Boolean': 'bool'
}


def get_type_literal(type_: GraphQLType):
    """
    String! => Text
    String => Optional[Text]
    [Character!]! => ['Character']
    [Character!] => Optional['Character']
    [Character] => Optional[List[Optional['Character']]]
    """
    is_null = False
    if is_non_null_type(type_):
        type_ = cast(GraphQLWrappingType, type_).of_type
    else:
        is_null = True

    if is_wrapping_type(type_):
        type_ = cast(GraphQLWrappingType, type_)
        value = get_type_literal(type_.of_type)
        if is_list_type(type_):
            value = f'List[{value}]'
    else:
        type_ = get_named_type(type_)
        value = SCALAR_MAP.get(type_.name) or type_.name
        value = value if is_leaf_type(type_) else f"'{value}'"

    if is_null:
        value = f'Optional[{value}]'

    return value
