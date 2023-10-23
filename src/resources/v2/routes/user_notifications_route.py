from flask import Blueprint
from src.resources.v2.controllers.user_notifications_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    get_user_notifications,
)

user_notifications_v2_api = Blueprint('user_notifications_v2_api', __name__)
get_user_notifications_v2_api = Blueprint('get_user_notifications_v2_api', __name__)

user_notifications_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
user_notifications_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
user_notifications_v2_api.add_url_rule('/<int:user_notifications_id>', view_func=get_one, **{'methods':['GET']})
user_notifications_v2_api.add_url_rule('/<int:user_notifications_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
user_notifications_v2_api.add_url_rule('/<int:user_notifications_id>', view_func=delete, **{'methods':['DELETE']})


get_user_notifications_v2_api.add_url_rule('/', view_func=get_user_notifications, **{'methods':['POST']})
