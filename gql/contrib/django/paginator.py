from typing import Optional, Tuple, Any, List

from django.core.paginator import Paginator as DjangoPaginator, InvalidPage
from django.db.models import QuerySet
from django.utils.translation import ugettext_lazy as _

import gql
from .exceptions import UserInputError


@gql.interface
class IDNode:
    """`IDNode` only have a id field."""

    id: gql.ID


@gql.type
class ListResponse:
    """`ListResponse` represent response with count and data."""

    count: int
    data: List[IDNode]


@gql.input
class Page:
    """`Page` represent page input.
    If `noPage` is true, will no pagination.
    """

    page: Optional[int] = 1
    page_size: Optional[int] = 10
    no_page: Optional[bool] = False


def get_page(queryset: QuerySet, page_conf: Page, count: bool = True) -> Tuple[Any, int]:
    if not page_conf or page_conf.no_page:
        return queryset, queryset.count() if count else 0

    page_size = page_conf.page_size if page_conf.page_size else 10
    page_number = page_conf.page if page_conf.page else 1
    paginator = DjangoPaginator(queryset, page_size)
    try:
        page = paginator.page(page_number)
    except InvalidPage:
        raise UserInputError(_('Invalid page or page_size.'))

    return page, page.paginator.count if count else 0
