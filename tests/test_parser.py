from gql.parser import fake_info, parse_info


def test_inline_fragment():
    query = """
query {
    search(text: "an") {
        __typename
        ... on Character {
            name
        }
        ... on Human {
            height
        }
        ... on Droid {
            primaryFunction
        }
        ... on Starship {
            name
            length
        }
    }
}

    """
    info = fake_info(query)
    meta = parse_info(info)
    assert meta.name == 'search'
    assert meta.sections == []
