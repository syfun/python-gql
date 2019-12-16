import json
import traceback

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from graphql import ExecutionResult, GraphQLError

import gql
from .exceptions import GraphQLExtensionError, UserInputError, MethodNotAllowedError, AuthenticationError
from .playground import PLAYGROUND_HTML
from .response import Response
from .settings import api_settings
from .utils import place_files_in_operations


class GraphQLView(View):
    # pretty: bool = False
    batch: bool = False
    authenticators = []

    schema: gql.Schema = None

    def __init__(self, **kwargs):
        self.schema = api_settings.SCHEMA
        self.authenticators = [auth() for auth in api_settings.AUTHENTICATION_CLASSES]
        super().__init__(**kwargs)

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return csrf_exempt(view)

    def authenticate(self, request):
        for auth in self.authenticators:
            user_token = auth.authenticate(request)
            if user_token is not None:
                return user_token[0]
        return None

    def perform_authentication(self, request: HttpRequest):
        """
        Perform authentication on the incoming request.

        Note that if you override this and simply 'pass', then authentication
        will instead be performed lazily, the first time either
        `request.user` or `request.auth` is accessed.
        """
        request.user = self.authenticate(request)

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            method = request.method.lower()
            if method == 'get' and api_settings.ENABLE_PLAYGROUND:
                return HttpResponse(PLAYGROUND_HTML)

            if method != 'post':
                raise MethodNotAllowedError()

            self.perform_authentication(request)

            data = self.parse_body(request)
            return self.get_response(request, data)
        except AuthenticationError as e:
            return Response(data={'errors': [e.formatted]}, status=401)
        except GraphQLExtensionError as e:
            return Response(data={'errors': [e.formatted]})

    def format_error(self, error: GraphQLError):
        if not error:
            raise ValueError("Received null or undefined error.")
        formatted = dict(  # noqa: E701 (pycqa/flake8#394)
            message=error.message or "An unknown error occurred.",
            locations=[l._asdict() for l in error.locations] if error.locations else None,
            path=error.path,
        )
        if settings.DEBUG and error.original_error:
            original_error = error.original_error
            exception = error.extensions.get('exception', {})
            exception['traceback'] = traceback.format_exception(
                type(original_error), original_error, original_error.__traceback__
            )
            error.extensions['exception'] = exception
        if error.extensions:
            formatted.update(extensions=error.extensions)
        return formatted

    def get_response(self, request: HttpRequest, data: dict) -> Response:
        query, variables, operation_name, id = self.get_graphql_params(request, data)

        execution_result = self.execute_graphql_request(request, query, variables, operation_name)

        data = {}
        if not execution_result:
            return Response(data)

        if execution_result.errors:
            data['errors'] = [self.format_error(e) for e in execution_result.errors]
        data['data'] = execution_result.data

        if self.batch:
            data['id'] = id

        return Response(data)

    def parse_body(self, request: HttpRequest) -> dict:
        content_type = self.get_content_type(request)

        if content_type == 'application/graphql':
            return {'query': request.body.decode()}

        elif content_type == 'application/json':
            try:
                body = request.body.decode()
            except Exception as e:
                raise UserInputError(str(e))

            try:
                request_json = json.loads(body)
                if self.batch:
                    assert isinstance(request_json, list), (
                        'Batch requests should receive a list, but received {}.'
                    ).format(repr(request_json))
                    assert len(request_json) > 0, 'Received an empty list in the batch request.'
                else:
                    assert isinstance(request_json, dict), 'The received data is not a valid JSON query.'
                return request_json
            except AssertionError as e:
                raise UserInputError(str(e))
            except (TypeError, ValueError):
                raise UserInputError(_('POST body sent invalid JSON.'))

        elif content_type == 'multipart/form-data':
            body = request.POST
            try:
                operations = json.loads(body.get('operations', '{}'))
                files_map = json.loads(body.get('map', '{}'))
            except (TypeError, ValueError):
                raise UserInputError(_('operations or map sent invalid JSON.'))
            if not files_map and not operations:
                return body
            return place_files_in_operations(operations, files_map, request.FILES)

        elif content_type == 'application/x-www-form-urlencoded':
            return request.POST

        return {}

    def execute_graphql_request(self, request, query, variables, operation_name) -> ExecutionResult:
        if not query:
            raise UserInputError(_('Must provide query string.'))

        return self.schema.execute(
            query, variable_values=variables, context_value=request, operation_name=operation_name
        )

    @staticmethod
    def json_encode(d):
        return json.dumps(d, separators=(',', ':'))

    # def json_encode(self, request, d, pretty=False):
    #     if not (self.pretty or pretty) and not request.GET.get('pretty'):
    #         return json.dumps(d, separators=(',', ':'))
    #
    #     return json.dumps(d, sort_keys=True, indent=2, separators=(',', ': '))

    @staticmethod
    def get_graphql_params(request, data):
        query = request.GET.get('query') or data.get('query')
        variables = request.GET.get('variables') or data.get('variables')
        id = request.GET.get('id') or data.get('id')

        if variables and isinstance(variables, str):
            try:
                variables = json.loads(variables)
            except Exception:
                raise UserInputError(_('Variables are invalid JSON.'))

        operation_name = request.GET.get('operationName') or data.get('operationName')
        if operation_name == 'null':
            operation_name = None

        return query, variables, operation_name, id

    @staticmethod
    def get_content_type(request):
        meta = request.META
        content_type = meta.get('CONTENT_TYPE', meta.get('HTTP_CONTENT_TYPE', ''))
        return content_type.split(';', 1)[0].lower()
