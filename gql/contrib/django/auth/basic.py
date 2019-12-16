"""
Provides various authentication policies.
"""
import base64
import binascii

from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import ugettext_lazy as _

from ..exceptions import AuthenticationError
from . import get_authorization_header, BaseAuthentication


class BasicAuthentication(BaseAuthentication):
    """
    HTTP Basic authentication against username/password.
    """

    www_authenticate_realm = 'api'

    def authenticate(self, request):
        """
        Returns a `User` if a correct username and password have been supplied
        using HTTP Basic authentication.  Otherwise returns `None`.
        """
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'basic':
            return None

        if len(auth) == 1:
            msg = _('Invalid basic header. No credentials provided.')
            raise AuthenticationError(msg)
        elif len(auth) > 2:
            msg = _('Invalid basic header. Credentials string should not contain spaces.')
            raise AuthenticationError(msg)

        try:
            auth_parts = base64.b64decode(auth[1]).decode().partition(':')
        except (TypeError, UnicodeDecodeError, binascii.Error):
            msg = _('Invalid basic header. Credentials not correctly base64 encoded.')
            raise AuthenticationError(msg)

        userid, password = auth_parts[0], auth_parts[2]
        return self.authenticate_credentials(userid, password, request)

    def authenticate_credentials(self, userid, password, request=None):
        """
        Authenticate the userid and password against username and password
        with optional request for context.
        """
        credentials = {get_user_model().USERNAME_FIELD: userid, 'password': password}
        user = authenticate(request=request, **credentials)

        if user is None:
            raise AuthenticationError(_('Invalid username/password.'))

        if not user.is_active:
            raise AuthenticationError(_('User inactive or deleted.'))

        return user, None

    def authenticate_header(self, request):
        return 'Basic realm="%s"' % self.www_authenticate_realm
