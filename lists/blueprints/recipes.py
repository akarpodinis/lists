import json

from flask import Blueprint as BP, render_template, request, redirect
from sqlalchemy import select, literal_column, delete, update, bindparam
from sqlalchemy.dialects.postgresql import insert

from lists.db import recipes, engine, ingredient_names, ingredients_recipes


blueprint = BP('recipes', __name__, url_prefix='/recipes',
               template_folder='/app/lists/templates/recipes')


@blueprint.route('/', methods=['GET'])
def list_recipes():
    return json.dumps([dict(**r) for r in recipes.select().execute().fetchall()]), 200


@blueprint.route('/new')
def new_recipe_form():
    with engine.connect():
        return render_template('new_recipe.html', ingredients=ingredient_names())


@blueprint.route('/<name>/edit')
def edit_recipe(name: str):
    with engine.connect() as conn:
        rows = conn.execute(select(ingredients_recipes.c.ingredient,
                                   ingredients_recipes.c.amount)
                            .where(ingredients_recipes.c.recipe == name)).fetchall()
        return render_template('edit_recipe.html',
                               name=name,
                               ingredients=[row[0] for row in rows],
                               amounts=[row[1] for row in rows])


@blueprint.route('/new', methods=['POST'])
def insert_new_recipe():
    with engine.connect() as conn:
        recipe_name = request.form.get('recipe_name')
        conn.execute(insert(recipes).values(
            name=recipe_name
        ).on_conflict_do_nothing().returning(literal_column('*')))
        new_ingredients = request.form.getlist('ingredients')
        conn.execute(insert(ingredients_recipes).values(
            [{'recipe': recipe_name,
                'ingredient': ingredient
              } for ingredient in new_ingredients]
        ).on_conflict_do_nothing())
        conn.execute(delete(ingredients_recipes).where(
            ingredients_recipes.c.ingredient.not_in(new_ingredients)
        ).where(
            ingredients_recipes.c.recipe == recipe_name
        ))

    return redirect(f'{recipe_name}/edit')


@blueprint.route('/<name>/edit', methods=['POST'])
def update_recipe(name: str):
    with engine.connect() as conn:
        form = request.form.to_dict()
        recipe_name = form.pop('recipe_name')
        conn.execute(update(ingredients_recipes)
                     .where(ingredients_recipes.c.recipe == bindparam('recipe_name'))
                     .where(ingredients_recipes.c.ingredient == bindparam('ing_name'))
                     .values(amount=bindparam('amount')),
                     [{
                         'recipe_name': recipe_name,
                         'ing_name': ing,
                         'amount': amount
                     } for ing, amount in form.items()])
    return redirect(f'/recipes/{name}/edit')
