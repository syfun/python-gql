from dataclasses import dataclass, field, fields, is_dataclass
from enum import IntEnum
from typing import Any, Dict, List, Tuple, Union, Callable

import graphql
from django.core.exceptions import FieldDoesNotExist
from django.db.models import (
    ForeignKey,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    OneToOneField,
    OneToOneRel,
    Prefetch,
    QuerySet,
    Count,
)

from gql.utils.str_converters import to_snake_case
from .paginator import ListResponse, get_page, Page


class FieldKind(IntEnum):
    NORMAL = 1
    ONE = 2
    MANY = 3


@dataclass
class FieldCollection:
    model: Any
    has_count: bool = False
    has_data: bool = False
    kind: FieldKind = FieldKind.NORMAL
    fields: List['str'] = field(default_factory=list)
    extra_fields: List['str'] = field(default_factory=list)
    additional_only_keys: List['str'] = field(default_factory=list)
    related_collections: Dict[str, 'FieldCollection'] = field(default_factory=dict)
    annotations: Dict[str, Any] = field(default_factory=dict)

    fragments: dict = None

    def get_relation(self) -> Tuple[List['str'], List['str'], List[Prefetch]]:
        only_keys = list({f for f in self.fields}.union({f for f in self.additional_only_keys}))
        select_related = []
        prefetch_related = []
        for key, coll in self.related_collections.items():
            if coll.kind == FieldKind.NORMAL:
                continue

            _only_keys, _select_related, _prefetch_related = coll.get_relation()
            if coll.kind == FieldKind.ONE:
                only_keys += [f'{key}__{k}' for k in _only_keys]
                for p in _prefetch_related:
                    p.add_prefix(key)
                _select_related = [f'{key}__{k}' for k in _select_related] or [key]

                select_related += _select_related
                prefetch_related += _prefetch_related
            elif coll.kind == FieldKind.MANY:
                qs = coll.model.objects.all()
                if coll.annotations:
                    qs = qs.annotate(**coll.annotations)
                if _select_related:
                    qs = qs.select_related(*_select_related)
                if _prefetch_related:
                    qs = qs.prefetch_related(*_prefetch_related)
                if _only_keys:
                    qs = qs.only(*_only_keys)
                prefetch_related.append(Prefetch(key, queryset=qs))
        return only_keys, select_related, prefetch_related

    def fill(self, section: graphql.FieldNode, model: Any):
        if section.kind == 'inline_fragment':
            for _section in section.selection_set.selections:
                self.fill(_section, model)
            return
        elif section.kind == 'fragment_spread' and self.fragments and section.name.value in self.fragments:
            for _section in self.fragments[section.name.value].selection_set.selections:
                self.fill(_section, model)
            return

        key = to_snake_case(section.name.value)
        field_map = getattr(model, 'FIELD_MAP', {})
        key = field_map.get(key, None) or key
        try:
            model_field = model._meta.get_field(key)
        except FieldDoesNotExist:
            custom_relation_map = getattr(model, 'CUSTOM_RELATION_MAP', {})
            annotation_map = getattr(model, 'ANNOTATION_MAP', {})
            if key in custom_relation_map:
                model_field = custom_relation_map[key]
                self.related_collections[key] = build_collection(
                    section, model_field, FieldKind.NORMAL, fragments=self.fragments
                )
            elif key in annotation_map:
                self.annotations[key] = annotation_map[key]
            else:
                self.extra_fields.append(key)
            return

        if isinstance(model_field, (OneToOneField, OneToOneRel, ForeignKey)):
            self.related_collections[key] = build_collection(
                section, model_field.related_model, FieldKind.ONE, fragments=self.fragments
            )
        elif isinstance(model_field, ManyToManyField):
            self.related_collections[key] = build_collection(
                section, model_field.related_model, FieldKind.MANY, fragments=self.fragments
            )
        elif isinstance(model_field, (ManyToOneRel, ManyToManyRel)):
            coll = build_collection(section, model_field.related_model, FieldKind.MANY, fragments=self.fragments)
            coll.additional_only_keys.append(model_field.field.column)
            self.related_collections[key] = coll
        else:
            self.fields.append(key)


def build_collection(
    field_node: graphql.FieldNode,
    model: Any,
    kind: FieldKind = FieldKind.NORMAL,
    has_count: bool = False,
    fragments: dict = None,
) -> FieldCollection:
    assert field_node.selection_set is not None

    collection = FieldCollection(
        model=model, kind=kind, additional_only_keys=getattr(model, 'ADDITIONAL_ONLY_KEYS', []), fragments=fragments
    )
    if not has_count:
        for section in field_node.selection_set.selections:
            collection.fill(section, model)
    else:
        for section in field_node.selection_set.selections:
            key = to_snake_case(section.name.value)
            if key == 'count':
                collection.has_count = True
            elif key == 'data':
                collection.has_data = True
                for _section in section.selection_set.selections:
                    collection.fill(_section, model)

    return collection


CastMethod = Callable[[Any, FieldCollection], Any]


class QueryOptimizer:
    collection: FieldCollection = None

    def __init__(self, info: graphql.GraphQLResolveInfo, queryset: QuerySet, has_count: bool = False):
        self.info = info
        self.has_count = has_count
        self.queryset = queryset

    def optimize(self):
        collection = build_collection(
            self.info.field_nodes[0], self.queryset.model, has_count=self.has_count, fragments=self.info.fragments
        )
        if collection.annotations:
            self.queryset = self.queryset.annotate(**collection.annotations)

        only_keys, select_related, prefetch_related = collection.get_relation()
        if select_related:
            self.queryset = self.queryset.select_related(*select_related)
        if prefetch_related:
            self.queryset = self.queryset.prefetch_related(*prefetch_related)
        if only_keys:
            self.queryset = self.queryset.only(*only_keys)

        self.collection = collection

    def get_list_data(self, page: Page = None, cast_method: CastMethod = None) -> Union[ListResponse, List[Any]]:
        self.optimize()
        instances, count = get_page(self.queryset, page, self.collection.has_count)
        cast_method = cast_method or self.queryset.model.to_entity
        if self.collection.has_count:
            return ListResponse(
                count=count,
                data=[cast_method(i, self.collection) for i in instances] if self.collection.has_data else [],
            )
        return [cast_method(i, self.collection) for i in instances]


def to_entity_dict(instance, entity_class, collection: FieldCollection):
    kwargs = {f: getattr(instance, f, None) for f in collection.fields}
    if collection.annotations:
        kwargs.update({f: getattr(instance, f, None) for f in collection.annotations})
    field_map = getattr(instance, 'FIELD_MAP', {})
    reverse_field_map = {v: k for k, v in field_map.items()} if field_map else field_map
    for key, coll in collection.related_collections.items():
        entity_key = reverse_field_map.get(key, None) or key
        if coll.kind == FieldKind.ONE:
            val = getattr(instance, key)
            kwargs[entity_key] = val.to_entity(coll) if val else None
        elif coll.kind == FieldKind.MANY:
            kwargs[entity_key] = [f.to_entity(coll) for f in getattr(instance, key).all()]
    kwargs.update({f.name: None for f in fields(entity_class) if f.name not in kwargs})
    return kwargs


def to_entity(instance, entity_class, collection: FieldCollection):
    kwargs = to_entity_dict(instance, entity_class, collection)
    return entity_class(**kwargs)


def bind_entity(entity_class, field_map=None, additional_only_keys=None, annotation_map=None, custom_relation_map=None):
    """
    annotation_map only support first level, cannot support select_related.
    """
    if not is_dataclass(entity_class):
        raise Exception(f'{entity_class.__name__} not a dataclass.')

    def _bind_entity(cls):
        def _to_entity(self, collection: FieldCollection):
            return to_entity(self, entity_class, collection)

        def _to_entity_dict(self, collection: FieldCollection):
            return to_entity_dict(self, entity_class, collection)

        if not hasattr(cls, 'to_entity'):
            cls.to_entity = _to_entity
        if not hasattr(cls, 'to_entity_dict'):
            cls.to_entity_dict = _to_entity_dict
        cls.FIELD_MAP = field_map or {}
        cls.ADDITIONAL_ONLY_KEYS = additional_only_keys or []
        cls.ANNOTATION_MAP = annotation_map or {}
        cls.CUSTOM_RELATION_MAP = custom_relation_map or {}
        return cls

    return _bind_entity
