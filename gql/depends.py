from typing import Any, Callable

from graphql import GraphQLResolveInfo


class ResolverDepends:
    def __init__(self, dependency: Callable[..., Any]) -> None:
        self.dependency = dependency

    def get_parameters(self, parent: Any, info: GraphQLResolveInfo) -> tuple:
        """
        Get parameters from parent and info.
        """
        return ()

    def execute(self, parent: Any, info: GraphQLResolveInfo):
        """
        Execute depends to get real value.
        """
        return self.dependency(*self.get_parameters(parent, info))


class InfoDepends(ResolverDepends):
    def get_parameters(self, parent: Any, info: GraphQLResolveInfo):
        return (info,)


class ContextDepends(ResolverDepends):
    def get_parameters(self, parent: Any, info: GraphQLResolveInfo):
        return (info.context,)


class RequestDepends(ResolverDepends):
    def get_parameters(self, parent: Any, info: GraphQLResolveInfo):
        return (info.context.get('request'),)
