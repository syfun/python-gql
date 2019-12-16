from typing import Any

from django.utils.translation import ugettext_lazy as _
from graphql import GraphQLError


class GraphQLExtensionError(GraphQLError):
    code = 'APOLLO_ERROR'
    message = 'apollo error'

    def __init__(self, message: str = None, **kwargs: Any):
        message = message or self.message
        extensions = {'code': self.code}
        if kwargs:
            extensions['exception'] = kwargs
        super().__init__(message=message, extensions=extensions)


class AuthenticationError(GraphQLExtensionError):
    code = 'AUTHENTICATION_ERROR'
    message = _('authentication error')


class ForbiddenError(GraphQLExtensionError):
    code = 'FORBIDDEN_ERROR'
    message = _('forbidden error')


class UserInputError(GraphQLExtensionError):
    code = 'USER_INPUT_ERROR'
    message = _('user input error')


class MethodNotAllowedError(GraphQLExtensionError):
    code = 'METHOD_NOT_ALLOWED'
    message = _('method not allowed, only accept ["GET", "POST"]')
