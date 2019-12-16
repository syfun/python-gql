from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from graphql import GraphQLResolveInfo

import gql
from gql.contrib.django.exceptions import AuthenticationError, UserInputError
from .settings import api_settings

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class Mutation:
    @gql.field
    @transaction.atomic()
    def login(self, info: GraphQLResolveInfo, username: str, password: str) -> str:
        credentials = {get_user_model().USERNAME_FIELD: username, 'password': password}
        user = authenticate(info.context, **credentials)
        if not user:
            raise UserInputError(_('Incorrect username or password.'))
        if not user.is_active:
            raise AuthenticationError(_('User account is disabled.'))

        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        return token
