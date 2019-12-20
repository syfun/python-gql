from graphql import (GraphQLArgument, GraphQLField, GraphQLList,
                     GraphQLNonNull, GraphQLObjectType, GraphQLString)

from gql.cli.generator import (get_enum_def, get_field_def, get_interface_def,
                               get_object_def, get_type_literal)


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
        character_type = GraphQLObjectType('Character', lambda: {
            'id': GraphQLField(
                GraphQLNonNull(GraphQLString),
                description='The id of the droid.'),
        })

        # [Character!]! => typing.List['Character']
        type_ = GraphQLNonNull(GraphQLList(GraphQLNonNull(character_type)))
        assert get_type_literal(type_) == "typing.List['Character']"

        # [Character!] => typing.Optional[typing.List['Character']]
        type_ = GraphQLList(GraphQLNonNull(character_type))
        assert get_type_literal(type_) == "typing.Optional[typing.List['Character']]"

        # [Character] => typing.Optional[typipng.List[typing.Optional['Character']]]
        type_ = GraphQLList(character_type)
        assert get_type_literal(type_) == "typing.Optional[typing.List[typing.Optional['Character']]]"


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
        assert get_field_def('id', field) == 'id: typing.Text'

    def test_args_field(self):
        human_type = GraphQLObjectType('Human', lambda: {
            'id': GraphQLField(
                GraphQLNonNull(GraphQLString),
                description='The id of the human.'),
        })
        field = GraphQLField(
            human_type,
            args={
                'id': GraphQLArgument(GraphQLNonNull(GraphQLString)),
                'name': GraphQLArgument(GraphQLString),
                'homePlanet': GraphQLArgument(GraphQLString)
            }
        )
        assert get_field_def('addHuman',
                             field) == "addHuman(id: typing.Text, name: typing.Optional[typing.Text], homePlanet: typing.Optional[typing.Text]): typing.Optional['Human']"


def test_get_interface_def(sample_schema):
    character_interface = sample_schema.get_type('Character')
    expect_value = """
class Character:
    id: typing.Text
    name: typing.Optional[typing.Text]
    friends: typing.List[Character]
    appearsIn: typing.Optional[typing.List[typing.Optional[Episode]]]
"""
    assert get_interface_def(character_interface) == expect_value


def test_get_object_def(sample_schema):
    human_type = sample_schema.get_type('Human')
    expect_value = """
class Human(Character):
    id: typing.Text
    name: typing.Optional[typing.Text]
    friends: typing.Optional[typing.List[typing.Optional[Character]]]
    appearsIn: typing.Optional[typing.List[typing.Optional[Episode]]]
    homePlanet: typing.Optional[typing.Text]
"""
    assert get_object_def(human_type) == expect_value


def test_get_enum_def(sample_schema):
    episode_type = sample_schema.get_type('Episode')
    expect_value = """
class Episode(Enum):
   NEWHOPE = 1
   EMPIRE = 2
   JEDI = 3
"""
    assert get_enum_def(episode_type) == expect_value
