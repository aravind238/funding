from flask import Blueprint
from src.resources.v2.controllers.client_debtors_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

client_debtors_v2_api = Blueprint('client_debtors_v2_api', __name__)

client_debtors_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
client_debtors_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
client_debtors_v2_api.add_url_rule('/<int:client_debtors_id>', view_func=get_one, **{'methods':['GET']})
client_debtors_v2_api.add_url_rule('/<int:client_debtors_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
client_debtors_v2_api.add_url_rule('/<int:client_debtors_id>', view_func=delete, **{'methods':['DELETE']})
