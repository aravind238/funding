from flask import Blueprint
from src.resources.v2.controllers.reasons_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

reasons_v2_api = Blueprint('reasons_v2_api', __name__)

reasons_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
reasons_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
reasons_v2_api.add_url_rule('/<int:reasons_id>', view_func=get_one, **{'methods':['GET']})
reasons_v2_api.add_url_rule('/<int:reasons_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
reasons_v2_api.add_url_rule('/<int:reasons_id>', view_func=delete, **{'methods':['DELETE']})
