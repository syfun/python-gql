import uvicorn

from gql import GraphQL, resolver, build_schema_from_file


@resolver('Query')
async def hello(parent, info, name: str) -> str:
    return name


schema = build_schema_from_file('./schema.gql')

app = GraphQL(schema)

if __name__ == '__main__':
    uvicorn.run(app)
