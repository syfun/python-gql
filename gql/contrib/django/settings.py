"""
Settings for python-graphql django contrib are all namespaced in the GRAPHQL setting.
For example your project's `settings.py` file might look like this:

GRAPHQL = {
    'SCHEMA': 'config.schema.schema'
}

This module provides the `api_setting` object, that is used to access
REST framework settings, checking for user settings first, then falling
back to the defaults.
"""
from importlib import import_module

from django.conf import settings
from django.test.signals import setting_changed

DEFAULTS = {
    'SCHEMA': None,
    'AUTHENTICATION_CLASSES': ('gql.contrib.django.auth.basic.BasicAuthentication',),
    'DATETIME_CONVERT_TIMESTAMP': True,
    'USER_CACHE_SETTER': 'gql.contrib.django.utils.set_user_to_cache',
    'USER_CACHE_GETTER': 'gql.contrib.django.utils.get_user_from_cache',
    'ENABLE_PLAYGROUND': False,
}

# List of settings that may be in string import notation.
IMPORT_STRINGS = ('SCHEMA', 'AUTHENTICATION_CLASSES', 'USER_CACHE_SETTER', 'USER_CACHE_GETTER')

# List of settings that have been removed
REMOVED_SETTINGS = ()


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    elif isinstance(val, str):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        # Nod to tastypie's use of importlib.
        module_path, class_name = val.rsplit('.', 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        msg = "Could not import '%s' for API setting '%s'. %s: %s." % (val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


class APISettings:
    """
    A settings object, that allows API settings to be accessed as properties.
    For example:

        from graphql.contrib.django.settings import api_settings
        print(api_settings.SCHEMA)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """

    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        if user_settings:
            self._user_settings = self.__check_user_settings(user_settings)
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(settings, 'GRAPHQL', {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid API setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def __check_user_settings(self, user_settings):
        SETTINGS_DOC = "http://github.com/teletraan/python-graphql"
        for setting in REMOVED_SETTINGS:
            if setting in user_settings:
                raise RuntimeError(
                    "The '%s' setting has been removed. Please refer to '%s' for available settings."
                    % (setting, SETTINGS_DOC)
                )
        return user_settings

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, '_user_settings'):
            delattr(self, '_user_settings')


api_settings = APISettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_api_settings(*args, **kwargs):
    setting = kwargs['setting']
    if setting == 'GRAPHQL':
        api_settings.reload()


setting_changed.connect(reload_api_settings)
