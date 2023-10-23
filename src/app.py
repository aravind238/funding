# src/app.py

from flask import Flask, jsonify, request
from .config import app_config
from .extensions import db
from .models import *
import os

# logs_schema = LogsSchema()


def create_app(env_name):
    """
    Create app
    """

    # app initiliazation
    app = Flask(__name__)

    # # SAVE LOGS
    # @app.after_request
    # def after(response):
    #     # response
    #     get_response = response.get_json()

    #     # We need to ignore OPTIONS, unwanted interactions with CORS.
    #     if request.method != "OPTIONS":
    #         # request
    #         get_request = {
    #             "method": request.method,
    #             "url": request.url,
    #             "headers": dict(request.headers),
    #             "params": dict(request.args),
    #         }

    #         # get Auth-Token
    #         auth_token = request.headers.get("auth-token", "None")

    #         # store to db
    #         data = {
    #             "response": get_response,
    #             "status_code": response.status,
    #             "request": get_request,
    #             "token": str(auth_token),
    #         }
            
    #         from src.resources.v2.helpers.logs import Logs

    #         logs = Logs(data=data)
    #         logs.save_logs()

    #     #     data, error = logs_schema.load(data)
    #     #     if error:
    #     #         return jsonify(error, 400)
    #     #     logs = Logs(data)
    #     #     logs.save()

    #     return response

    # END OF LOGS REQUEST

    app.config.from_object(app_config[env_name])
    app.url_map.strict_slashes = False

    # Flask.jsonify orders output alphabetically by default, set it to False
    app.config["JSON_SORT_KEYS"] = False

    # set the default value for all static files
    # app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Register extensions
    from .extensions import register_extensions
    register_extensions(app)

    # initializing db
    db.init_app(app)

    # Register blueprints
    from .route import register_v2_blueprints
    register_v2_blueprints(app)

    # Register Exception Handler
    from .exceptions import error_handler, catch_all
    app.register_error_handler(Exception, error_handler)

    # Wrong URL Response
    app.add_url_rule("/<path:path>", view_func=catch_all)

    # Root API Response
    app.add_url_rule(
        "/", view_func=lambda: {"msg": "Congratulations! Your endpoint is working fine"}
    )

    return app
