import json

from flask import Blueprint as BP, render_template, current_app, redirect, request
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from lists.db import ingredients, type_for_column, required_for_column


blueprint = BP('ingredients', __name__, url_prefix='/ingredients',
               template_folder='/app/lists/templates/ingredients')


@blueprint.route('/')
def list_ingredients():
    return json.dumps(
            [dict(**r) for r in ingredients.select().execute().fetchall()]), 200


@blueprint.route('/new', methods=['GET'])
def new_ingredient_form():
    columns = list(ingredients.c)

    return render_template('new_ingredient.html',
                           fields=[column.key for column in columns],
                           types=[type_for_column(column) for column in columns],
                           required=[required_for_column(column) for column in columns])


@blueprint.route('/new', methods=['POST'])
def insert_new_ingredient():
    column_names = {c.name for c in ingredients.columns}
    fixed = {k: v for k, v in request.form.items() if k in (request.form.keys() & column_names)}

    op = insert(ingredients).values(**fixed).on_conflict_do_nothing() \
        .returning(text('(xmax = 0) as inserted')).execute().first()

    current_app.logger.info('Inserted' if getattr(op, 'inserted', False) else 'Updated')

    return redirect('/ingredients')
