from flask import Blueprint
from src.resources.v2.controllers.debtor_limit_approvals_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    get_approval_history,
    get_comments,
    get_supporting_documents,
    get_reasons,
)

debtor_limit_approvals_v2_api = Blueprint('debtor_limit_approvals_v2_api', __name__)

debtor_limit_approvals_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
debtor_limit_approvals_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
debtor_limit_approvals_v2_api.add_url_rule('/<int:id>', view_func=get_one, **{'methods':['GET']})
debtor_limit_approvals_v2_api.add_url_rule('/<int:id>', view_func=update, **{'methods':['PUT', 'PATCH']})
debtor_limit_approvals_v2_api.add_url_rule('/<int:id>', view_func=delete, **{'methods':['DELETE']})

debtor_limit_approvals_v2_api.add_url_rule('/<int:id>/approval-history', view_func=get_approval_history, **{'methods':['GET']})
debtor_limit_approvals_v2_api.add_url_rule('/<int:id>/comments', view_func=get_comments, **{'methods':['GET']})
debtor_limit_approvals_v2_api.add_url_rule('/<int:id>/supporting-documents', view_func=get_supporting_documents, **{'methods':['GET']})
debtor_limit_approvals_v2_api.add_url_rule('/<int:id>/reasons', view_func=get_reasons, **{'methods':['GET']})
