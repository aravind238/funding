from flask import Blueprint
from src.resources.v2.controllers.compliance_repository_controller import (
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

compliance_repository_v2_api = Blueprint('compliance_repository_v2_api', __name__)

compliance_repository_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
compliance_repository_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
compliance_repository_v2_api.add_url_rule('/<int:id>', view_func=get_one, **{'methods':['GET']})
compliance_repository_v2_api.add_url_rule('/<int:id>', view_func=update, **{'methods':['PUT', 'PATCH']})
compliance_repository_v2_api.add_url_rule('/<int:id>', view_func=delete, **{'methods':['DELETE']})

compliance_repository_v2_api.add_url_rule('/<int:id>/approval-history', view_func=get_approval_history, **{'methods':['GET']})
compliance_repository_v2_api.add_url_rule('/<int:id>/comments', view_func=get_comments, **{'methods':['GET']})
compliance_repository_v2_api.add_url_rule('/<int:id>/supporting-documents', view_func=get_supporting_documents, **{'methods':['GET']})
compliance_repository_v2_api.add_url_rule('/<int:id>/reasons', view_func=get_reasons, **{'methods':['GET']})
