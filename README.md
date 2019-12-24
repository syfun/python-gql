# python-gql

Schema-first python graphql library.

# Usage

## Use asgi

```python
# app.py
from gql import GraphQL, query, gql

type_defs = gql("""
type Query {
    hello(name: String!): String!
}
""")


@query
async def hello(parent, info, name: str) -> str:
    return name


app = GraphQL(type_defs=type_defs)
```

Use [uvicorn](https://www.uvicorn.org) to run app.

`uvicorn app:app --reload`

## Use `gqlgen` command.

### generate types

`gqlgen ./schema.graphql types --kind=dataclass`

### generator resolver

`gqlgen ./schema.graphql resolver Query hello`

### help info

For more info about `gqlgen`, please use `gqlgen -h`

## Upload File

```python
import uvicorn
from gql import gql, mutate, GraphQL

type_defs = gql("""
 scalar Upload
 
 type File {
    filename: String!
  }

  type Query {
    uploads: [File]
  }

  type Mutation {
    singleUpload(file: Upload!): File!
    multiUpload(files: [Upload!]!): [File!]!
  }
""")


@mutate
def single_upload(parent, info, file):
    return file


@mutate
def multi_upload(parent, info, files):
    return files


app = GraphQL(type_defs=type_defs)


if __name__ == '__main__':
    uvicorn.run(app, port=8080)

```