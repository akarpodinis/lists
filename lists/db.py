from os import environ

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Float, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

url = environ['DATABASE_URL']
if 'postgres://' in url:
    url = url.replace("://", "ql://", 1)

engine = sa.create_engine(url)

metadata = sa.MetaData()
metadata.bind = engine

new_uuid = sa.text('uuid_generate_v4()')


def type_for_column(column):
    if isinstance(column.type, String):
        return 'text'
    elif isinstance(column.type, OnOffEnum):
        return 'checkbox'
    else:
        raise NotImplementedError(f'No html input mapping for {column.type}')


def required_for_column(column):
    if isinstance(column.type, String):
        return 'required'
    elif isinstance(column.type, OnOffEnum):
        return ''
    else:
        raise NotImplementedError(f'No html input mapping for {column.type}')


class OnOffEnum(sa.types.TypeDecorator):
    impl = Boolean

    def process_bind_param(self, value, dialect):
        if isinstance(value, bool):
            return value

        if 'on' in value.lower():
            return True
        elif 'off' in value.lower():
            return False
        else:
            super().process_bind_param(value, dialect)


ingredients = Table(
    'ingredients',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', String, unique=True, nullable=False),
    Column('aisle', String, nullable=False),
    Column('stocked', OnOffEnum(), default=False)
)

recipes = Table(
    'recipes',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', String, unique=True, nullable=False)
)

ingredients_recipes = Table(
    'ingredients_recipes',
    metadata,
    Column('recipe', UUID(as_uuid=True), nullable=False),
    Column('ingredient', UUID(as_uuid=True), nullable=False),
    Column('amount', Float, default=0),
    UniqueConstraint('recipe', 'ingredient', name='recipe_ingredient_key')
)


def ingredient_names():
    with engine.connect() as conn:
        rows = conn.execute(sa.select(ingredients.c.name)).fetchall()
        return [row[0] for row in rows]
