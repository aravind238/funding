from flask import Blueprint
from src.resources.v2.controllers.soa_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    soa_pdf,
    generate_lcra_csv,
    get_soa_details,
    get_client_settings,
    get_disclaimer,
    get_bofa_transaction_status,
    client_soa_pdf,
    get_verification_notes,
    get_vn_approval_history,
    get_invoice_supporting_documents,
)

soa_v2_api = Blueprint('soa_v2_api', __name__)
download_soa_v2_api = Blueprint('download_soa_v2_api', __name__)
generate_lcra_csv_v2_api = Blueprint('generate_lcra_csv_v2_api', __name__)
get_soa_details_v2_api = Blueprint('get_soa_details_v2_api', __name__)

soa_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
soa_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>', view_func=get_one, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
soa_v2_api.add_url_rule('/<int:soa_id>', view_func=delete, **{'methods':['DELETE']})

download_soa_v2_api.add_url_rule('/<int:soa_id>', view_func=soa_pdf, **{'methods':['GET']})
generate_lcra_csv_v2_api.add_url_rule('/<int:soa_id>', view_func=generate_lcra_csv, **{'methods':['GET']})
get_soa_details_v2_api.add_url_rule('/<int:soa_id>', view_func=get_soa_details, **{'methods':['GET']})

soa_v2_api.add_url_rule('/<int:soa_id>/client-settings', view_func=get_client_settings, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>/disclaimer', view_func=get_disclaimer, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>/transaction/status', view_func=get_bofa_transaction_status, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>/download/client', view_func=client_soa_pdf, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>/verification-notes', view_func=get_verification_notes, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>/approval-history/verification-notes', view_func=get_vn_approval_history, **{'methods':['GET']})
soa_v2_api.add_url_rule('/<int:soa_id>/invoice-supporting-documents', view_func=get_invoice_supporting_documents, **{'methods':['GET']})
