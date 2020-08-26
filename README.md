# python-gql

Python schema-first GraphQL library based on GraphQL-core.


## Requirements

Python 3.7+

## Installation

`pip install python-gql`

## Getting start

```python
import graphql
from gql import gql, make_schema, query, mutate

type_defs = gql("""
type Query {
    hello(name: String!): String!
}

type Post {
    author: String!
    comment: String!
}
type Mutation {
    addPost(author: String, comment: String): Post!
}
""")


@query
def hello(parent, info, name: str) -> str:
    return name


@mutate
def add_post(parent, info, author: str = None, comment: str = None) -> dict:
    return {'author': author, 'comment': comment}


schema = make_schema(type_defs)

q = """
query {
    hello(name: "graphql")
}
"""
result = graphql.graphql_sync(schema, q)
print(result.data)

# result: {'hello': 'graphql'}

q = """
mutation {
    addPost(author: "syfun", comment: "This is a good library.") {
        author
        comment
    }
}
"""
result = graphql.graphql_sync(schema, q)
print(result.data)

# result: {'addPost': {'author': 'syfun', 'comment': 'This is a good library.'}}
```

## Build schema

This library is `schema-first`, so you must build a schema explicitly.

Here, we have two methods to build a schema, by `a type definitions` or `a schema file`.

```python
from gql import gql, make_schema

type_defs = gql("""
type Query {
    hello(name: String!): String!
}
""")

schema = make_schema(type_defs)
```

> `gql` function will check your type definitions syntax.

```python
from gql import make_schema_from_file

schema = make_schema_from_file('./schema.graphql')
```

## Resolver decorators

> In Python, `decorator` is my favorite function, it save my life!

We can use `query`, `mutation`, `subscribe` to bind functions to GraphQL resolvers.

```python
@query
def hello(parent, info, name: str) -> str:
    return name
```

These decorators will auto convert the snake function to camel one.

```python
# add_port => addPost
@mutate
def add_post(parent, info, author: str = None, comment: str = None) -> dict:
    return {'author': author, 'comment': comment}
```

When the funcation name different from the resolver name, you can give a name argument to these decorators.

```python
@query('hello')
def hello_function(parent, info, name: str) -> str:
    return name
```

About `subscribe`, please see [gql-subscriptions](gql-subscriptions).

## Enum type decorator

Use `enum_type` decorator with a python Enum class.

```python
from enum import Enum

from gql import enum_type


@enum_type
class Gender(Enum):
    MALE = 1
    FEMALE = 2
```

## Custom Scalar

Use `scalar_type` decorator with a python class.

```python
from gql import scalar_type


@scalar_type
class JSONString:
    description = "The `JSONString` represents a json string."

    @staticmethod
    def serialize(value: Any) -> str:
        return json.dumps(value)

    @staticmethod
    def parse_value(value: Any) -> dict:
        if not isinstance(value, str):
            raise TypeError(f'JSONString cannot represent non string value: {inspect(value)}')
        return json.loads(value)

    @staticmethod
    def parse_literal(ast, _variables=None):
        if isinstance(ast, StringValueNode):
            return json.loads(ast.value)

        return INVALID

```


## Apollo Federation

[Example](https://github.com/syfun/starlette-graphql/tree/master/examples/federation)

[Apollo Federation](https://www.apollographql.com/docs/apollo-server/federation/introduction/)

Thanks to [Ariadne](https://ariadnegraphql.org/docs/apollo-federation)


## Framework support

- [Starlette GraphQL](https://github.com/syfun/starlette-graphql)
- [Django GraphQL](https://github.com/syfun/django-graphql)
