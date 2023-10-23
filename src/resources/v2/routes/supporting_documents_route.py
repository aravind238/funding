from flask import Blueprint
from src.resources.v2.controllers.supporting_documents_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    presigned_url,
)

supporting_documents_v2_api = Blueprint('supporting_documents_v2_api', __name__)
get_presigned_url_v2_api = Blueprint('get_presigned_url_v2_api', __name__)

supporting_documents_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
supporting_documents_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
supporting_documents_v2_api.add_url_rule('/<int:supporting_documents_id>', view_func=get_one, **{'methods':['GET']})
supporting_documents_v2_api.add_url_rule('/<int:supporting_documents_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
supporting_documents_v2_api.add_url_rule('/<int:supporting_documents_id>', view_func=delete, **{'methods':['DELETE']})

get_presigned_url_v2_api.add_url_rule('/', view_func=presigned_url, **{'methods':['POST']})
