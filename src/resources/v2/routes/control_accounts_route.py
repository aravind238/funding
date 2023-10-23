from flask import Blueprint
from src.resources.v2.controllers.control_accounts_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

control_accounts_v2_api = Blueprint('control_accounts_v2_api', __name__)

control_accounts_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
control_accounts_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
control_accounts_v2_api.add_url_rule('/<int:control_account_id>', view_func=get_one, **{'methods':['GET']})
control_accounts_v2_api.add_url_rule('/<int:control_account_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
control_accounts_v2_api.add_url_rule('/<int:control_account_id>', view_func=delete, **{'methods':['DELETE']})
