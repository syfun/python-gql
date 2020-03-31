# flake8: noqa
from graphql import (
    GraphQLArgument,
    GraphQLField,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLString,
)

from gql.cli.generator import FieldGenerator, TypeGenerator, get_type_literal


class TestGetTypeLiteral:
    """
    String! => Text
    String => Optional[Text]
    [Character!]! => ['Character']
    [Character!] => Optional['Character']
    [Character] => Optional[List[Optional['Character']]]
    """

    def test_simple(self):
        # String! => Text
        assert get_type_literal(GraphQLNonNull(GraphQLString)) == 'Text'

        # String => Optional[Text]
        assert get_type_literal(GraphQLString) == 'Optional[Text]'

    def test_list(self):
        character_type = GraphQLObjectType(
            'Character',
            lambda: {
                'id': GraphQLField(
                    GraphQLNonNull(GraphQLString), description='The id of the droid.'
                ),
            },
        )

        # [Character!]! => List['Character']
        type_ = GraphQLNonNull(GraphQLList(GraphQLNonNull(character_type)))
        assert get_type_literal(type_) == "List['Character']"

        # [Character!] => Optional[List['Character']]
        type_ = GraphQLList(GraphQLNonNull(character_type))
        assert get_type_literal(type_) == "Optional[List['Character']]"

        # [Character] => Optional[typipng.List[Optional['Character']]]
        type_ = GraphQLList(character_type)
        assert get_type_literal(type_) == "Optional[List[Optional['Character']]]"


class TestGetFieldDef:
    """
    id: String! => id: Text

    addHuman(id: String!, name: String, homePlanet: String): Human
    =>
    addHuman(
        id: Text, name: Optional[Text], 
        homePlanet: Optional[Text]
    ): Optional['Human']
    """

    def test_simple(self):
        field = GraphQLField(GraphQLNonNull(GraphQLString))
        assert FieldGenerator.output_field('id', field) == 'id: Text'

    def test_args_field(self):
        human_type = GraphQLObjectType(
            'Human',
            lambda: {
                'id': GraphQLField(
                    GraphQLNonNull(GraphQLString), description='The id of the human.'
                ),
            },
        )
        field = GraphQLField(
            human_type,
            args={
                'id': GraphQLArgument(GraphQLNonNull(GraphQLString)),
                'name': GraphQLArgument(GraphQLString),
                'homePlanet': GraphQLArgument(GraphQLString),
            },
        )
        assert (
            FieldGenerator.output_field('addHuman', field)
            == "add_human(parent, info, id: Text, name: Optional[Text], home_planet: Optional[Text]) -> Optional['Human']"
        )


class TestTypeGenerator:
    def test_interface_type(self, sample_schema):
        character_interface = sample_schema.get_type('Character')
        expect_value = """
class Character:
    id: Text
    name: Optional[Text]
    friends: List[Character]
    appears_in: Optional[List[Optional[Episode]]]
"""
        assert TypeGenerator().interface_type(character_interface) == expect_value

    def test_object_type(self, sample_schema):
        human_type = sample_schema.get_type('Human')
        expect_value = """
class Human(Character):
    id: Text
    name: Optional[Text]
    friends: Optional[List[Optional[Character]]]
    appears_in: Optional[List[Optional[Episode]]]
    home_planet: Optional[Text]
"""
        assert TypeGenerator().object_type(human_type) == expect_value

    def test_enum_type(self, sample_schema):
        episode_type = sample_schema.get_type('Episode')
        expect_value = """
@enum_resolver
class Episode(Enum):
   NEWHOPE = 1
   EMPIRE = 2
   JEDI = 3
"""
        assert TypeGenerator().enum_type(episode_type) == expect_value
