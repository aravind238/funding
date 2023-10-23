from flask import Blueprint
from src.resources.v2.controllers.reserve_release_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    reserve_release_pdf,
    generate_lcra_csv,
    get_rr_details,
    get_client_settings,
    get_disclaimer,
    get_bofa_transaction_status,
    client_reserve_release_pdf,
)

reserve_release_v2_api = Blueprint('reserve_release_v2_api', __name__)
download_reserve_release_v2_api = Blueprint('download_reserve_release_v2_api', __name__)
generate_rr_lcra_csv_v2_api = Blueprint('generate_rr_lcra_csv_v2_api', __name__)
reserve_release_details_v2_api = Blueprint('reserve_release_details_v2_api', __name__)

reserve_release_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
reserve_release_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>', view_func=get_one, **{'methods':['GET']})
reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>', view_func=delete, **{'methods':['DELETE']})

download_reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>', view_func=reserve_release_pdf, **{'methods':['GET']})
generate_rr_lcra_csv_v2_api.add_url_rule('/<int:reserve_release_id>', view_func=generate_lcra_csv, **{'methods':['GET']})
reserve_release_details_v2_api.add_url_rule('/<int:reserve_release_id>', view_func=get_rr_details, **{'methods':['GET']})

reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>/client-settings', view_func=get_client_settings, **{'methods':['GET']})
reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>/disclaimer', view_func=get_disclaimer, **{'methods':['GET']})
reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>/transaction/status', view_func=get_bofa_transaction_status, **{'methods':['GET']})
reserve_release_v2_api.add_url_rule('/<int:reserve_release_id>/download/client', view_func=client_reserve_release_pdf, **{'methods':['GET']})
