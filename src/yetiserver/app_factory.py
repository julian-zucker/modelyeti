"""The application factory, which produces application servers. See
http://flask.pocoo.org/docs/1.0/patterns/appfactories
for more details."""

from flask import Flask


def create_app(database_credentials_file):
    """Creates a flask application.

    :param database_credentials_file: the name of the file with database credentials.
    :return: the app
    """
    app = Flask(__name__)

    from yetiserver.database import database_connection_from_file
    app.db = database_connection_from_file(database_credentials_file)

    from yetiserver.authentication import UserManager
    app.auth = UserManager.from_redis_connection(app.db)

    from yetiserver.api import api_blueprint
    app.register_blueprint(api_blueprint)

    return app