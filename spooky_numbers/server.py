import flask

from spooky_numbers import db, numbers


def create_app():
    app = flask.Flask(__name__)

    db.init_app(app)
    
    app.register_blueprint(numbers.blueprint)

    return app

