from flask import Blueprint
from src.resources.v2.controllers.approvals_history_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

approvals_history_v2_api = Blueprint('approvals_history_v2_api', __name__)

approvals_history_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
approvals_history_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
approvals_history_v2_api.add_url_rule('/<int:approvals_history_id>', view_func=get_one, **{'methods':['GET']})
approvals_history_v2_api.add_url_rule('/<int:approvals_history_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
approvals_history_v2_api.add_url_rule('/<int:approvals_history_id>', view_func=delete, **{'methods':['DELETE']})
