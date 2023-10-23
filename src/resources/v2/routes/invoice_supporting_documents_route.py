from flask import Blueprint
from src.resources.v2.controllers.invoice_supporting_documents_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

invoice_supporting_documents_v2_api = Blueprint('invoice_supporting_documents_v2_api', __name__)

invoice_supporting_documents_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
invoice_supporting_documents_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
invoice_supporting_documents_v2_api.add_url_rule('/<int:id>', view_func=get_one, **{'methods':['GET']})
invoice_supporting_documents_v2_api.add_url_rule('/<int:id>', view_func=update, **{'methods':['PUT', 'PATCH']})
invoice_supporting_documents_v2_api.add_url_rule('/<int:id>', view_func=delete, **{'methods':['DELETE']})
