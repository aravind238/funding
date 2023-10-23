from flask import Blueprint
from src.resources.v2.controllers.reserve_release_disbursements_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

reserve_release_disbursements_v2_api = Blueprint('reserve_release_disbursements_v2_api', __name__)

reserve_release_disbursements_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
reserve_release_disbursements_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
reserve_release_disbursements_v2_api.add_url_rule('/<int:reserve_release_disbursements_id>', view_func=get_one, **{'methods':['GET']})
reserve_release_disbursements_v2_api.add_url_rule('/<int:reserve_release_disbursements_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
reserve_release_disbursements_v2_api.add_url_rule('/<int:reserve_release_disbursements_id>', view_func=delete, **{'methods':['DELETE']})
