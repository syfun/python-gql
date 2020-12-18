from gql.schema import make_schema_from_path

from pathlib import Path


def test_make_schema_from_path():
    schema = make_schema_from_path(str(Path(__file__).parent / 'schema'))
    assert set(schema.query_type.fields.keys()) == {'me', 'addresses'}
    assert set(schema.mutation_type.fields.keys()) == {'createAddress'}
