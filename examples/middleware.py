import asyncio

from graphql import graphql

from gql import ExecutionContext, MiddlewareManager, make_schema, mutate, query

type_defs = """
type User {
  id: ID!
  name: String!
}

type Query {
  user(id: ID!): User!
}

type Mutation {
  createUser(name: String!): User!
}
"""


@query
async def user(parent, info, id: str):
    return {'id': id, 'name': 'Jack'}


@mutate
async def create_user(parent, info, name: str):
    return {'id': 1, 'name': 'Jack'}


async def log_middleware(resolve, parent, info, **kwargs):
    print('log here')
    return await resolve(parent, info, **kwargs)


schema = make_schema(type_defs)


async def main():
    source = """
    mutation {
      createUser(name: "Jack") {
        id
        name
      }
    }
    """
    r = await graphql(
        schema,
        source,
        execution_context_class=ExecutionContext,
        middleware=MiddlewareManager({'Mutation': [log_middleware]}),
    )
    print(r)


if __name__ == '__main__':
    asyncio.run(main())
