from graphql import GraphQLNonNull, GraphQLString, GraphQLObjectType, GraphQLList, GraphQLField

from gql.utils.functions import get_type_literal


class Test_get_type_literal:
    """
    name: String! => name: Text
    name: String => Optional[Text]
    friends: [Character!]! => List['Character']
    friends: [Character!] => Optional[List['Character']]
    friends: [Character] => Optional[List[Optional['Character']]]
    """
    def test_simple(self):
        # String! => Text
        assert get_type_literal(GraphQLNonNull(GraphQLString)) == 'Text'

        # String => Optional[Text]
        assert get_type_literal(GraphQLString) == 'Optional[Text]'

    def test_list(self):
        character_type = GraphQLObjectType('Character', lambda: {
            'id': GraphQLField(
                GraphQLNonNull(GraphQLString),
                description='The id of the droid.'),
        })

        # [Character!]! => List['Character']
        type_ = GraphQLNonNull(GraphQLList(GraphQLNonNull(character_type)))
        assert get_type_literal(type_) == "List['Character']"

        # [Character!] => Optional[List['Character']]
        type_ = GraphQLList(GraphQLNonNull(character_type))
        assert get_type_literal(type_) == "Optional[List['Character']]"

        # [Character] => Optional[List[Optional['Character']]]
        type_ = GraphQLList(character_type)
        assert get_type_literal(type_) == "Optional[List[Optional['Character']]]"
