from flask import Blueprint
from src.resources.v2.controllers.collection_notes_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    get_approval_history,
)

collection_notes_v2_api = Blueprint('collection_notes_v2_api', __name__)

collection_notes_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
collection_notes_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
collection_notes_v2_api.add_url_rule('/<int:id>', view_func=get_one, **{'methods':['GET']})
collection_notes_v2_api.add_url_rule('/<int:id>', view_func=update, **{'methods':['PUT', 'PATCH']})
collection_notes_v2_api.add_url_rule('/<int:id>', view_func=delete, **{'methods':['DELETE']})

collection_notes_v2_api.add_url_rule('/<int:id>/approval-history', view_func=get_approval_history, **{'methods':['GET']})
