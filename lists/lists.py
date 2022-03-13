from flask import Flask, request
from sqlalchemy.exc import IntegrityError

import lists.blueprints.ingredients
import lists.blueprints.lists
import lists.blueprints.recipes

app = Flask(__name__)
app.debug = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

app.register_blueprint(lists.blueprints.ingredients.blueprint)
app.register_blueprint(lists.blueprints.lists.blueprint)
app.register_blueprint(lists.blueprints.recipes.blueprint)


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
