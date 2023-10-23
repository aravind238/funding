from flask import Blueprint
from src.resources.v2.controllers.logs_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

logs_v2_api = Blueprint('logs_v2_api', __name__)

logs_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
logs_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
logs_v2_api.add_url_rule('/<int:log_id>', view_func=get_one, **{'methods':['GET']})
logs_v2_api.add_url_rule('/<int:log_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
logs_v2_api.add_url_rule('/<int:log_id>', view_func=delete, **{'methods':['DELETE']})
