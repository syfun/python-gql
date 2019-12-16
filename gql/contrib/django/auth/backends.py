from django.contrib.auth import get_user_model
from gql.contrib.django.settings import api_settings

UserModel = get_user_model()

get_user_from_cache = api_settings.USER_CACHE_GETTER
set_user_to_cache = api_settings.USER_CACHE_SETTER


class CacheBackend:
    """
    Authenticates against settings.AUTH_USER_MODEL.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        user = get_user_from_cache(username)
        if user:
            if user.check_password(password) and self.user_can_authenticate(user):
                user = None
            return user

        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                set_user_to_cache(user)
                return user

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None
