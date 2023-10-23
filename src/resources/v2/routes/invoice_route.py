from flask import Blueprint
from src.resources.v2.controllers.invoice_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    add_invoices,
    update_invoices,
    update_invoice_status,
    generate_invoice_csv,
    get_nonfactored_and_deleted_invoices,
    upload_invoices,
    validate_uploading_invoices,
    get_collection_notes,
    get_cn_approval_history,
    get_verification_notes,
    get_vn_approval_history,
    get_invoice_supporting_documents,
)

invoice_v2_api = Blueprint('invoice_v2_api', __name__)
generate_invoice_csv_v2_api = Blueprint('generate_invoice_csv_v2_api', __name__)
nonfactored_deleted_invoices_v2_api = Blueprint('nonfactored_deleted_invoices_v2_api', __name__)
upload_invoices_v2_api = Blueprint('upload_invoices_v2_api', __name__)

invoice_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
invoice_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
invoice_v2_api.add_url_rule('/<int:invoice_id>', view_func=get_one, **{'methods':['GET']})
invoice_v2_api.add_url_rule('/<int:invoice_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
invoice_v2_api.add_url_rule('/<int:invoice_id>', view_func=delete, **{'methods':['DELETE']})
invoice_v2_api.add_url_rule('/status/update', view_func=update_invoice_status, **{'methods':['POST']})
invoice_v2_api.add_url_rule('/add_invoices', view_func=add_invoices, **{'methods':['POST']})
invoice_v2_api.add_url_rule('/<int:invoice_id>/collection-notes', view_func=get_collection_notes, **{'methods':['GET']})
invoice_v2_api.add_url_rule('/<int:invoice_id>/approval-history/collection-notes', view_func=get_cn_approval_history, **{'methods':['GET']})
invoice_v2_api.add_url_rule('/<int:invoice_id>/verification-notes', view_func=get_verification_notes, **{'methods':['GET']})
invoice_v2_api.add_url_rule('/<int:invoice_id>/approval-history/verification-notes', view_func=get_vn_approval_history, **{'methods':['GET']})
invoice_v2_api.add_url_rule('/<int:invoice_id>/supporting-documents', view_func=get_invoice_supporting_documents, **{'methods':['GET']})

generate_invoice_csv_v2_api.add_url_rule('/', view_func=generate_invoice_csv, **{'methods':['POST']})

nonfactored_deleted_invoices_v2_api.add_url_rule('/<int:soa_id>', view_func=get_nonfactored_and_deleted_invoices, **{'methods':['GET']})

upload_invoices_v2_api.add_url_rule('/', view_func=upload_invoices, **{'methods':['POST']})
upload_invoices_v2_api.add_url_rule('/validate', view_func=validate_uploading_invoices, **{'methods':['POST']})
