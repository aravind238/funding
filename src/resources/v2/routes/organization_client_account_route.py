from flask import Blueprint
from src.resources.v2.controllers.organization_client_account_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

organization_client_account_v2_api = Blueprint('organization_client_account_v2_api', __name__)

organization_client_account_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
organization_client_account_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
organization_client_account_v2_api.add_url_rule('/<int:organization_client_account_id>', view_func=get_one, **{'methods':['GET']})
organization_client_account_v2_api.add_url_rule('/<int:organization_client_account_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
organization_client_account_v2_api.add_url_rule('/<int:organization_client_account_id>', view_func=delete, **{'methods':['DELETE']})
