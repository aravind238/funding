from flask import Blueprint
from src.resources.v2.controllers.disclaimers_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    get_different_disclaimers,
)

disclaimers_v2_api = Blueprint('disclaimers_v2_api', __name__)
get_different_disclaimers_v2_api = Blueprint('get_different_disclaimers_v2_api', __name__)

disclaimers_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
disclaimers_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
disclaimers_v2_api.add_url_rule('/<int:disclaimer_id>', view_func=get_one, **{'methods':['GET']})
disclaimers_v2_api.add_url_rule('/<int:disclaimer_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
disclaimers_v2_api.add_url_rule('/<int:disclaimer_id>', view_func=delete, **{'methods':['DELETE']})

get_different_disclaimers_v2_api.add_url_rule('/', view_func=get_different_disclaimers, **{'methods':['GET']})
