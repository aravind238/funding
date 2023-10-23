from flask import Blueprint
from src.resources.v2.controllers.client_funds_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    calculate_fee_advance,
)

client_funds_v2_api = Blueprint('client_funds_v2_api', __name__)
calculate_fee_advance_v2_api = Blueprint('calculate_fee_advance_v2_api', __name__)

client_funds_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
client_funds_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
client_funds_v2_api.add_url_rule('/<int:client_funds_id>', view_func=get_one, **{'methods':['GET']})
client_funds_v2_api.add_url_rule('/<int:client_funds_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
client_funds_v2_api.add_url_rule('/<int:client_funds_id>', view_func=delete, **{'methods':['DELETE']})

calculate_fee_advance_v2_api.add_url_rule('/', view_func=calculate_fee_advance, **{'methods':['GET']})
