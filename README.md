# python-gql

Schema-first python graphql library.

## Usage

```python
# app.py
from gql import GraphQL, resolver, gql, build_schema

type_defs = gql("""
type Query {
    hello(name: String!): String!
}
""")


@resolver('Query')
async def hello(parent, info, name: str) -> str:
    return name


app = GraphQL(build_schema(type_defs))
```

Use [uvicorn](https://www.uvicorn.org) to run app.

`uvicorn app:app --reload`

## TODO

- [ ] add cli doc
- [ ] do more about resolver args
- [ ] database support
- [ ] authenticate support