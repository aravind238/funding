from flask import Blueprint
from src.resources.v2.controllers.clients_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    get_clients_control_account,
    get_client_details,
    calculate_client_balances,
    get_debtors,
    export_debtors,
    get_client_settings,
    get_client_disclaimers,
)

clients_v2_api = Blueprint('clients_v2_api', __name__)
client_details_v2_api = Blueprint('client_details_v2_api', __name__)
calculate_client_balances_v2_api = Blueprint('calculate_client_balances_v2_api', __name__)

clients_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
clients_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
clients_v2_api.add_url_rule('/<int:client_id>', view_func=get_one, **{'methods':['GET']})
clients_v2_api.add_url_rule('/<int:client_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
clients_v2_api.add_url_rule('/<int:client_id>', view_func=delete, **{'methods':['DELETE']})

clients_v2_api.add_url_rule('/<int:client_id>/control-account', view_func=get_clients_control_account, **{'methods':['GET']})

client_details_v2_api.add_url_rule('/<int:client_id>', view_func=get_client_details, **{'methods':['GET']})

calculate_client_balances_v2_api.add_url_rule('/', view_func=calculate_client_balances, **{'methods':['GET']})

clients_v2_api.add_url_rule('/<int:client_id>/debtors', view_func=get_debtors, **{'methods':['GET']})
clients_v2_api.add_url_rule('/<int:client_id>/debtors/export', view_func=export_debtors, **{'methods':['GET']})
clients_v2_api.add_url_rule('/<int:client_id>/settings', view_func=get_client_settings, **{'methods':['GET']})
clients_v2_api.add_url_rule('/<int:client_id>/disclaimer',
                            view_func=get_client_disclaimers, **{'methods': ['GET']})
