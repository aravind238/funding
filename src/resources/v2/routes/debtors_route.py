from flask import Blueprint
from src.resources.v2.controllers.debtors_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    get_requests_by_debtor,
    get_debtor_limits,
    # get_invoice_aging_by_debtor,
    get_duplicate_debtors,
    merge_duplicate_debtors,
    get_approval_history,
    get_collection_notes,
    get_cn_approval_history,
)

debtors_v2_api = Blueprint('debtors_v2_api', __name__)
get_debtor_limits_v2_api = Blueprint('get_debtor_limits_v2_api', __name__)
# get_invoice_aging_by_debtor_v2_api = Blueprint('get_invoice_aging_by_debtor_v2_api', __name__, url_prefix='/api/v2/get-invoice-aging-by-debtor')

debtors_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
debtors_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
debtors_v2_api.add_url_rule('/<int:debtor_id>', view_func=get_one, **{'methods':['GET']})
debtors_v2_api.add_url_rule('/<int:debtor_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
debtors_v2_api.add_url_rule('/<int:debtor_id>', view_func=delete, **{'methods':['DELETE']})

debtors_v2_api.add_url_rule('/<int:debtor_id>/soa-requests', view_func=get_requests_by_debtor, **{'methods':['GET']})

get_debtor_limits_v2_api.add_url_rule('/', view_func=get_debtor_limits, **{'methods':['GET']})
# get_invoice_aging_by_debtor_v2_api.add_url_rule('/', view_func=get_invoice_aging_by_debtor, **{'methods':['GET']})

debtors_v2_api.add_url_rule('/<int:debtor_id>/duplicate', view_func=get_duplicate_debtors, **{'methods':['GET']})
debtors_v2_api.add_url_rule('/<int:debtor_id>/duplicate/merge', view_func=merge_duplicate_debtors, **{'methods':['POST']})

debtors_v2_api.add_url_rule('/<int:debtor_id>/approval-history', view_func=get_approval_history, **{'methods':['GET']})
debtors_v2_api.add_url_rule('/<int:debtor_id>/collection-notes', view_func=get_collection_notes, **{'methods':['GET']})
debtors_v2_api.add_url_rule('/<int:debtor_id>/approval-history/collection-notes', view_func=get_cn_approval_history, **{'methods':['GET']})