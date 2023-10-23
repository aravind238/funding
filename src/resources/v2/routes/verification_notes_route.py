from flask import Blueprint
from src.resources.v2.controllers.verification_notes_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
    get_approval_history,
)

verification_notes_v2_api = Blueprint('verification_notes_v2_api', __name__)

verification_notes_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
verification_notes_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
verification_notes_v2_api.add_url_rule('/<int:id>', view_func=get_one, **{'methods':['GET']})
verification_notes_v2_api.add_url_rule('/<int:id>', view_func=update, **{'methods':['PUT', 'PATCH']})
verification_notes_v2_api.add_url_rule('/<int:id>', view_func=delete, **{'methods':['DELETE']})

verification_notes_v2_api.add_url_rule('/<int:id>/approval-history', view_func=get_approval_history, **{'methods':['GET']})
