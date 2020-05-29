from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Union

import graphql

from .utils import to_snake_case

GraphQLNode = Union[graphql.FieldNode, graphql.FragmentDefinitionNode]


@dataclass
class FieldMeta:
    name: str
    depth: int
    sections: List[str] = field(default_factory=list)
    sub_fields: Dict[str, 'FieldMeta'] = field(default_factory=dict)
    fragments: Set[str] = field(default_factory=set)
    inline_fragments: Dict[str, 'FieldMeta'] = field(default_factory=dict)

    def get_sub_field(self, name) -> Optional['FieldMeta']:
        return self.sub_fields.get(name)

    def add_section_or_sub_field(self, field_: 'FieldMeta') -> None:
        if not field_:
            return None

        if field_.sections or field_.sub_fields or field_.fragments:
            self.sub_fields[field_.name] = field_
        else:
            self.sections.append(field_.name)

    def replace_fragments(self, fragments: Dict[str, 'FieldMeta']) -> None:
        if not self.fragments and not self.sub_fields:
            return None

        for name in self.fragments:
            # In the real case, name in fragments surely.
            fragment = fragments[name]
            if fragment.fragments:
                fragment.replace_fragments(fragments)
            self.sections.extend(fragment.sections)

            for field_name, field_ in fragment.sub_fields.items():
                if field_.fragments:
                    field_.replace_fragments(fragments)
                self.sub_fields[field_name] = field_
        if self.depth > 1:
            for sub_field in self.sub_fields.values():
                if sub_field.fragments:
                    sub_field.replace_fragments(fragments)
        else:
            # clear sub fields if depth less than 1
            self.sub_fields = {}

        self.fragments = set()


def parse_fragment_nodes(nodes: Dict[str, graphql.FragmentDefinitionNode]) -> Dict[str, FieldMeta]:
    fragments = {name: parse_node(node, depth=2) for name, node in nodes.items()}
    for fragment in fragments.values():
        if fragment.fragments:
            fragment.replace_fragments(fragments)
    return fragments


def parse_node(node: GraphQLNode, depth: int = 2) -> Optional[FieldMeta]:
    if depth == 0:
        return None

    if isinstance(node, graphql.InlineFragmentNode):
        name = node.type_condition.name.value
    else:
        name = to_snake_case(node.name.value)
    field_meta = FieldMeta(name=name, depth=depth)
    if not node.selection_set:
        return field_meta

    depth -= 1
    for field_node in node.selection_set.selections:
        if isinstance(field_node, graphql.FragmentSpreadNode):
            field_meta.fragments.add(to_snake_case(field_node.name.value))
            continue

        if isinstance(field_node, graphql.InlineFragmentNode):
            meta = parse_node(field_node, depth=depth + 1)
            field_meta.inline_fragments[meta.name] = meta
            continue

        if not field_node.selection_set:
            name = field_node.name.value
            if not name.startswith('__'):
                field_meta.sections.append(to_snake_case(name))
            continue

        if depth == 0:
            continue

        field_meta.add_section_or_sub_field(parse_node(field_node, depth=depth))

    return field_meta


def parse_info(info: graphql.GraphQLResolveInfo, depth: int = 2, index: int = 0) -> 'FieldMeta':
    if 'fragments' not in info.context:
        fragments = parse_fragment_nodes(info.fragments)
        info.context['fragments'] = fragments
    else:
        fragments = info.context['fragments']

    field_metas = info.context.get('field_metas') or {}
    if index not in field_metas:
        field_meta = parse_node(info.field_nodes[index], depth=depth)
        field_meta.replace_fragments(fragments)
        field_metas[index] = field_meta

    return field_metas[index]


def fake_info(query) -> graphql.GraphQLResolveInfo:
    from unittest.mock import MagicMock

    doc = graphql.parse(query)
    return MagicMock(
        context={},
        field_nodes=doc.definitions[0].selection_set.selections,
        fragments={node.name.value: node for node in doc.definitions[1:]},
    )
