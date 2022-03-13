import json

from flask import Flask, redirect, render_template, request
from sqlalchemy import Table, text, select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

import lists.ingredients
import lists.recipes
from lists.db import (
    engine, ingredients, ingredients_recipes, recipes
)

app = Flask(__name__)
app.debug = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

app.register_blueprint(lists.ingredients.blueprint)
app.register_blueprint(lists.recipes.blueprint)


@app.before_first_request
def startup():
    app.logger.info('Registered URL rules')
    app.logger.info(app.url_map)


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
