from flask import Blueprint
from src.resources.v2.controllers.users_controller import (
    get_role_permissions,
    get_users,
    check_request_update_permission,
)

user_v2_api = Blueprint('user_v2_api', __name__)
users_v2_api = Blueprint('users_v2_api', __name__)

user_v2_api.add_url_rule('/roles/permissions', view_func=get_role_permissions, **{'methods':['GET']})
users_v2_api.add_url_rule('/', view_func=get_users, **{'methods':['GET']})
users_v2_api.add_url_rule('/request/permission', view_func=check_request_update_permission, **{'methods':['GET']})
