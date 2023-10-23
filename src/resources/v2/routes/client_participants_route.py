from flask import Blueprint
from src.resources.v2.controllers.client_participants_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

client_participants_v2_api = Blueprint('client_participants_v2_api', __name__)

client_participants_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
client_participants_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
client_participants_v2_api.add_url_rule('/<int:client_participants_id>', view_func=get_one, **{'methods':['GET']})
client_participants_v2_api.add_url_rule('/<int:client_participants_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
client_participants_v2_api.add_url_rule('/<int:client_participants_id>', view_func=delete, **{'methods':['DELETE']})
