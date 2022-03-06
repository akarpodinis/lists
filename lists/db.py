from os import environ

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Integer, String, Table, UniqueConstraint

engine = sa.create_engine(environ['DATABASE_URL'])

metadata = sa.MetaData()
metadata.bind = engine

ingredients = Table(
    'ingredients',
    metadata,
    Column('name', String, primary_key=True),
    Column('aisle', String),
    Column('stocked', Boolean)
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
    Column('amount', Integer, default=0),
    UniqueConstraint('recipe', 'ingredient', name='recipe_ingredient_key')
)
