import json

from flask import Blueprint as BP, render_template, request, redirect
from sqlalchemy import select, delete, update, bindparam
from sqlalchemy.dialects.postgresql import insert

from lists.db import recipes, engine, ingredients, ingredients_recipes
from lists.encoding import UUIDEncoder


blueprint = BP('recipes', __name__, url_prefix='/recipes',
               template_folder='/app/lists/templates/recipes')


@blueprint.route('/', methods=['GET'])
def list_recipes():
    return json.dumps([dict(**r)
                       for r in recipes.select().execute().fetchall()], cls=UUIDEncoder), 200


@blueprint.route('/new')
def new_recipe_form():
    with engine.connect():
        names = []
        ids = []
        for id, name in engine.execute(select(ingredients.c.id, ingredients.c.name)):
            names.append(name)
            ids.append(id)
        return render_template('new_recipe.html', names=names, ids=ids)


@blueprint.route('/<id>/edit')
def edit_recipe(id: str):
    with engine.connect() as conn:
        name = conn.execute(select(recipes.c.name).where(recipes.c.id == id)).fetchone()[0]
        sel = select(ingredients.c.name, ingredients.c.id, ingredients_recipes.c.amount)
        sel = sel.select_from(ingredients
                              .join(ingredients_recipes,
                                    ingredients_recipes.c.ingredient == ingredients.c.id)
                              .join(recipes,
                                    recipes.c.id == ingredients_recipes.c.recipe))
        sel = sel.where(recipes.c.id == id)
        rows = conn.execute(sel).fetchall()
        return render_template('edit_recipe.html',
                               name=name,
                               ingredients=[row[0] for row in rows],
                               ids=[row[1] for row in rows],
                               amounts=[row[2] for row in rows])


@blueprint.route('/new', methods=['POST'])
def insert_new_recipe():
    with engine.connect() as conn:
        recipe_id = conn.execute(insert(recipes).values(
            name=request.form.get('recipe_name')
        ).on_conflict_do_nothing().returning(recipes.c.id)).first()[0]
        new_ingredients = request.form.getlist('ingredients')
        ins = insert(ingredients_recipes).values(
            [{'recipe': recipe_id,
              'ingredient': ingredient
              } for ingredient in new_ingredients]
        ).on_conflict_do_nothing()
        conn.execute(ins)
        conn.execute(delete(ingredients_recipes).where(
            ingredients_recipes.c.ingredient.not_in(new_ingredients)
        ).where(
            ingredients_recipes.c.recipe == recipe_id
        ))

    return redirect(f'/recipes/{recipe_id}/edit')


@blueprint.route('/<id>/edit', methods=['POST'])
def update_recipe(id: str):
    with engine.connect() as conn:
        form = request.form.to_dict()
        conn.execute(update(ingredients_recipes)
                     .where(ingredients_recipes.c.recipe == bindparam('recipe_id'))
                     .where(ingredients_recipes.c.ingredient == bindparam('ing_id'))
                     .values(amount=bindparam('amount')),
                     [{
                         'recipe_id': id,
                         'ing_id': ing,
                         'amount': amount
                     } for ing, amount in form.items()])
    return redirect(f'/recipes/{id}/edit')
