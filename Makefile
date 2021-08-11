VERSION ?= latest

bump:
	sed -i -e "s/__version__.*/__version__ = '${VERSION}'/g" gql/__init__.py
	poetry version -s ${VERSION}

