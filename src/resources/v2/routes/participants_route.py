from flask import Blueprint
from src.resources.v2.controllers.participants_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

participants_v2_api = Blueprint('participants_v2_api', __name__)

participants_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
participants_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
participants_v2_api.add_url_rule('/<int:participant_id>', view_func=get_one, **{'methods':['GET']})
participants_v2_api.add_url_rule('/<int:participant_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
participants_v2_api.add_url_rule('/<int:participant_id>', view_func=delete, **{'methods':['DELETE']})
