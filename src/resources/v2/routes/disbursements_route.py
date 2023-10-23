from flask import Blueprint
from src.resources.v2.controllers.disbursements_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

disbursements_v2_api = Blueprint('disbursements_v2_api', __name__)

disbursements_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
disbursements_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
disbursements_v2_api.add_url_rule('/<int:disbursements_id>', view_func=get_one, **{'methods':['GET']})
disbursements_v2_api.add_url_rule('/<int:disbursements_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
disbursements_v2_api.add_url_rule('/<int:disbursements_id>', view_func=delete, **{'methods':['DELETE']})
