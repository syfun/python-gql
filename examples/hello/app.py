import uvicorn

from gql import GraphQL, resolver

from starlette.config import Config
from fastapi import FastAPI


@resolver('Query')
async def hello(parent, info, name: str) -> str:
    return name


app = GraphQL(schema_file='./schema.gql')

if __name__ == '__main__':
    uvicorn.run(app)
