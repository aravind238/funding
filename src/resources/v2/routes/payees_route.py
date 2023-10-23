from flask import Blueprint
from src.resources.v2.controllers.payees_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    import_payees,
    get_approval_history,
    get_comments,
    get_supporting_documents,
    get_reasons,
)

payees_v2_api = Blueprint('payees_v2_api', __name__)
import_payees_v2_api = Blueprint('import_payees_v2_api', __name__)

payees_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
payees_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
payees_v2_api.add_url_rule('/<int:payee_id>', view_func=get_one, **{'methods':['GET']})
payees_v2_api.add_url_rule('/<int:payee_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
payees_v2_api.add_url_rule('/<int:payee_id>', view_func=delete, **{'methods':['DELETE']})
payees_v2_api.add_url_rule('/<int:payee_id>/reasons', view_func=get_reasons, **{'methods':['GET']})

import_payees_v2_api.add_url_rule('/', view_func=import_payees, **{'methods':['GET']})


payees_v2_api.add_url_rule('/<int:payee_id>/approval-history', view_func=get_approval_history, **{'methods':['GET']})
payees_v2_api.add_url_rule('/<int:payee_id>/comments', view_func=get_comments, **{'methods':['GET']})
payees_v2_api.add_url_rule('/<int:payee_id>/supporting-documents', view_func=get_supporting_documents, **{'methods':['GET']})
