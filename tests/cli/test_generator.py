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
    String! => typing.Text
    String => typing.Optional[typing.Text]
    [Character!]! => ['Character']
    [Character!] => typing.Optional['Character']
    [Character] => typing.Optional[typing.List[typing.Optional['Character']]]
    """

    def test_simple(self):
        # String! => typing.Text
        assert get_type_literal(GraphQLNonNull(GraphQLString)) == 'typing.Text'

        # String => typing.Optional[typing.Text]
        assert get_type_literal(GraphQLString) == 'typing.Optional[typing.Text]'

    def test_list(self):
        character_type = GraphQLObjectType(
            'Character',
            lambda: {
                'id': GraphQLField(
                    GraphQLNonNull(GraphQLString), description='The id of the droid.'
                ),
            },
        )

        # [Character!]! => typing.List['Character']
        type_ = GraphQLNonNull(GraphQLList(GraphQLNonNull(character_type)))
        assert get_type_literal(type_) == "typing.List['Character']"

        # [Character!] => typing.Optional[typing.List['Character']]
        type_ = GraphQLList(GraphQLNonNull(character_type))
        assert get_type_literal(type_) == "typing.Optional[typing.List['Character']]"

        # [Character] => typing.Optional[typipng.List[typing.Optional['Character']]]
        type_ = GraphQLList(character_type)
        assert (
            get_type_literal(type_) == "typing.Optional[typing.List[typing.Optional['Character']]]"
        )


class TestGetFieldDef:
    """
    id: String! => id: typing.Text

    addHuman(id: String!, name: String, homePlanet: String): Human
    =>
    addHuman(
        id: Text, name: typing.Optional[typing.Text], 
        homePlanet: typing.Optional[typing.Text]
    ): typing.Optional['Human']
    """

    def test_simple(self):
        field = GraphQLField(GraphQLNonNull(GraphQLString))
        assert FieldGenerator.output_field('id', field) == 'id: typing.Text'

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
            == "add_human(parent, info, id: typing.Text, name: typing.Optional[typing.Text], home_planet: typing.Optional[typing.Text]) -> typing.Optional['Human']"
        )


class TestTypeGenerator:
    def test_interface_type(self, sample_schema):
        character_interface = sample_schema.get_type('Character')
        expect_value = """
class Character:
    id: typing.Text
    name: typing.Optional[typing.Text]
    friends: typing.List[Character]
    appears_in: typing.Optional[typing.List[typing.Optional[Episode]]]
"""
        assert TypeGenerator().interface_type(character_interface) == expect_value

    def test_object_type(self, sample_schema):
        human_type = sample_schema.get_type('Human')
        expect_value = """
class Human(Character):
    id: typing.Text
    name: typing.Optional[typing.Text]
    friends: typing.Optional[typing.List[typing.Optional[Character]]]
    appears_in: typing.Optional[typing.List[typing.Optional[Episode]]]
    home_planet: typing.Optional[typing.Text]
"""
        assert TypeGenerator().object_type(human_type) == expect_value

    def test_enum_type(self, sample_schema):
        episode_type = sample_schema.get_type('Episode')
        expect_value = """
class Episode(Enum):
   NEWHOPE = 1
   EMPIRE = 2
   JEDI = 3
"""
        assert TypeGenerator().enum_type(episode_type) == expect_value
