import uvicorn

from gql import gql, query, subscribe
from gql.asgi import GraphQL

type_defs = gql(
    """
  type Subscription {
    postAdded: Post
  }

  type Query {
    posts: [Post]
  }

  type Mutation {
    addPost(author: String, comment: String): Post
  }

  type Post {
    author: String
    comment: String
  }
"""
)


@query
def posts(parent, info):
    return [{'author': 'Jack', 'comment': 'Good!'}]


@subscribe
def post_added(parent, info, *args):
    return


app = GraphQL(type_defs=type_defs)

if __name__ == '__main__':
    uvicorn.run(app, port=8080)
