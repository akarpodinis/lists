import json

from flask import Flask, redirect, render_template, request
from sqlalchemy import String, Table, text, literal_column, delete, select, update, bindparam, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from lists.db import (
    engine, metadata, ingredients, ingredients_recipes, recipes, OnOffEnum, ingredient_names
)

app = Flask(__name__)
app.debug = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.before_request
def access_logging():
    app.logger.info('Request log =====')
    app.logger.info('Path: %s', request.path)
    app.logger.info('Method: %s', request.method)
    app.logger.info('Query: %s', request.query_string)
    app.logger.info('Form: %s', request.form)


@app.after_request
def response_logging(response):
    app.logger.info('Response log =====')
    app.logger.info('Data: %s', response.data)
    app.logger.info('Code: %d', response.status_code)
    return response


@app.errorhandler(IntegrityError)
def error_handler(exc: Exception):
    app.logger.exception(exc)
    return 'Already exists', 409


def get_handler(table: Table):
    app.logger.info('Getting all for %s', table)
    if not request.query_string:
        return json.dumps(
            [dict(**r) for r in table.select().execute().fetchall()]), 200

    recipes = request.args.getlist('recipe')

    return f'Found {recipes}', 200


def post_handler(table: Table):
    column_names = {c.name for c in table.columns}
    fixed = {k: v for k, v in request.form.items() if k in (request.form.keys() & column_names)}

    op = insert(table).values(**fixed).on_conflict_do_nothing() \
        .returning(text('(xmax = 0) as inserted')).execute().first()

    app.logger.info('Inserted' if getattr(op, 'inserted', False) else 'Updated')

    return redirect(f'/{table}/{"edit" if table == recipes else ""}')


def delete_handler(table: Table):
    table.delete().where(table.c.name == request.form['name']).execute()

    return 'Deleted', 200


method_map = {
    'GET': get_handler,
    'POST': post_handler,
    'DELETE': delete_handler
}


@app.route(rule='/<resource>/', methods=[k for k in method_map.keys()])
def handle_list(resource: str):
    if 'favicon' in resource:
        return '', 200
    return method_map[request.method](metadata.tables[resource])


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


@app.route(rule='/ingredients/new')
def new_ingredient():
    columns = list(ingredients.c)

    return render_template('input.html',
                           fields=[column.key for column in columns],
                           types=[type_for_column(column) for column in columns],
                           required=[required_for_column(column) for column in columns],
                           table=ingredients.name)


@app.route(rule='/recipes/<op>/', methods=['GET', 'POST'])
@app.route(rule='/recipes/<op>/<name>', methods=['GET', 'POST'])
def recipe_operation(op: str, name: str = None):
    if request.method == 'GET':
        if 'new' in op:
            with engine.connect():
                return render_template('new_recipe.html', ingredients=ingredient_names())

        with engine.connect() as conn:
            rows = conn.execute(select(ingredients_recipes.c.ingredient,
                                       ingredients_recipes.c.amount)
                                .where(ingredients_recipes.c.recipe == (name or op))).fetchall()
            return render_template('edit_recipe.html',
                                   name=name or op,
                                   ingredients=[row[0] for row in rows],
                                   amounts=[row[1] for row in rows])
    else:
        if 'edit' in op:
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
            return redirect(f'/recipes/{name}')

        if 'new' in op:
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

            return redirect(f'/recipes/edit/{recipe_name}')


@app.route('/lists/', methods=['GET', 'POST'])
def build_shopping_list():
    if request.method == 'GET':
        with engine.connect() as conn:
            rows = conn.execute(select(recipes)).fetchall()
            return render_template('choose_for_list.html',
                                   recipes=[row[0] for row in rows])

    with engine.connect() as conn:
        sel = select(ingredients.c.aisle, ingredients.c.name,
                     func.sum(ingredients_recipes.c.amount))
        sel = sel.select_from(ingredients
                              .join(ingredients_recipes,
                                    ingredients_recipes.c.ingredient == ingredients.c.name))
        sel = sel.where(ingredients_recipes.c.recipe.in_(request.form.getlist('recipes_for_list')))
        sel = sel.where(~ingredients.c.stocked)
        sel = sel.group_by(ingredients.c.name, ingredients.c.aisle)
        sel = sel.order_by(ingredients.c.aisle.asc())
        rows = conn.execute(sel)

        # Preprocess into aisle -> {'thing': amount} mappings
        aisles = {}
        for result in rows.fetchall():
            if result[0] not in aisles:
                aisles[result[0]] = []
            aisles[result[0]].append({result[1]: result[2]})
        return render_template('shopping_list.html',
                               aisles=aisles)
