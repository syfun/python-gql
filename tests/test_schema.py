from gql.schema import make_schema_from_files

from pathlib import Path


def test_make_schema_from_files():
    assert make_schema_from_files([]) is None

    current_dir = Path(__file__).parent
    files = [
        str(current_dir / 'schema1.graphql'),
        str(current_dir / 'schema2.graphql')
    ]
    schema = make_schema_from_files(files)
    assert set(schema.query_type.fields.keys()) == {'me', 'addresses'}
    assert set(schema.mutation_type.fields.keys()) == {'createAddress'}