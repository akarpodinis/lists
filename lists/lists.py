import json

from flask import Flask, redirect, render_template, request
from sqlalchemy import Boolean, String, Table, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from db import metadata

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


def find(table: Table):
    app.logger.info('Getting all for %s', table)
    if not request.query_string:
        return json.dumps(
            [dict(**r) for r in table.select().execute().fetchall()]), 200

    recipes = request.args.getlist('recipe')

    return f'Found {recipes}', 200


def post(table: Table):
    column_names = {c.name for c in table.columns}
    fixed = {k: v for k, v in request.form.items() if k in (request.form.keys() & column_names)}

    op = insert(table).values(**fixed).on_conflict_do_nothing() \
        .returning(text('(xmax = 0) as inserted')).execute().first()

    app.logger.info('Inserted' if getattr(op, 'inserted', False) else 'Updated')

    return redirect(f'/{table}/')


def delete(table: Table):
    table.delete().where(table.c.name == request.form['name']).execute()

    return 'Deleted', 200


method_map = {
    'GET': find,
    'POST': post,
    'DELETE': delete
}


@app.route(rule='/<resource>/', methods=[k for k in method_map.keys()])
def handle_list(resource: str):
    return method_map[request.method](metadata.tables[resource])


def type_for_column(column):
    if isinstance(column.type, String):
        return 'text'
    elif isinstance(column.type, Boolean):
        return 'checkbox'
    else:
        raise NotImplementedError(f'No html input mapping for {column.type}')


@app.route(rule='/<resource>/edit')
def edit_resource(resource: str):
    table = metadata.tables[resource]

    columns = list(table.c)

    return render_template('input.html',
                           fields=[column.key for column in columns],
                           types=[type_for_column(column) for column in columns],
                           table=table.name)
