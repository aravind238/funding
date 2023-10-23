from flask import Blueprint
from src.resources.v2.controllers.dashboard_controller import (
    get_time_remaining,
    get_dashboard,
    get_soa_total,
    total_soa_amount,
    get_principal_fees,
)

calculate_time_remaining_v2_api = Blueprint('calculate_time_remaining_v2_api', __name__)
dashboard_v2_api = Blueprint('dashboard_v2_api', __name__)
get_soa_total_v2_api = Blueprint('get_soa_total_v2_api', __name__)
total_soa_amount_v2_api = Blueprint('total_soa_amount_v2_api', __name__)
principal_fees_v2_api = Blueprint('principal_fees_v2_api', __name__)

calculate_time_remaining_v2_api.add_url_rule('/', view_func=get_time_remaining, **{'methods':['GET']})
dashboard_v2_api.add_url_rule('/', view_func=get_dashboard, **{'methods':['GET']})
get_soa_total_v2_api.add_url_rule('/', view_func=get_soa_total, **{'methods':['GET']})
total_soa_amount_v2_api.add_url_rule('/', view_func=total_soa_amount, **{'methods':['GET']})
principal_fees_v2_api.add_url_rule('/', view_func=get_principal_fees, **{'methods':['GET']})
