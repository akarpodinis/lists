from os import environ

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Float, String, Table, UniqueConstraint

url = environ['DATABASE_URL']
if 'postgres://' in url:
    url = url.replace("://", "ql://", 1)

engine = sa.create_engine(url)


metadata = sa.MetaData()
metadata.bind = engine


class OnOffEnum(sa.types.TypeDecorator):
    impl = Boolean

    def __init__(self, enumtype, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._enumtype = enumtype

    # # Alembic requires that `__repr__` return a constructor for this type that can be passed into
    # # `eval()`.  The default implementation for `__repr__` does not do this well for custom types.
    # def __repr__(self):
    #     return f'{__name__}({__name__}.{bool})'

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
    Column('name', String, primary_key=True),
    Column('aisle', String),
    Column('stocked', OnOffEnum(Boolean), default=False)
)

recipes = Table(
    'recipes',
    metadata,
    Column('name', String, primary_key=True)
)

ingredients_recipes = Table(
    'ingredients_recipes',
    metadata,
    Column('recipe', String),
    Column('ingredient', String),
    Column('amount', Float, default=0),
    UniqueConstraint('recipe', 'ingredient', name='recipe_ingredient_key')
)


def ingredient_names():
    with engine.connect() as conn:
        rows = conn.execute(sa.select(ingredients.c.name)).fetchall()
        return [row[0] for row in rows]
