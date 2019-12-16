from django.core.exceptions import MultipleObjectsReturned

from .exceptions import UserInputError


def get_object(qs, quiet=False, **kwargs):
    exc = None
    try:
        return qs.get(**kwargs)
    except qs.model.DoesNotExist:
        exc = UserInputError('Not found.')
    except MultipleObjectsReturned:
        exc = UserInputError('More than one object found.')

    if quiet:
        return None
    if exc:
        raise exc
