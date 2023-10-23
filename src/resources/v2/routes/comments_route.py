from flask import Blueprint
from src.resources.v2.controllers.comments_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

comments_v2_api = Blueprint('comments_v2_api', __name__)

comments_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
comments_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
comments_v2_api.add_url_rule('/<int:comment_id>', view_func=get_one, **{'methods':['GET']})
comments_v2_api.add_url_rule('/<int:comment_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
comments_v2_api.add_url_rule('/<int:comment_id>', view_func=delete, **{'methods':['DELETE']})
