from flask import Blueprint
from src.resources.v2.controllers.lcra_export_controller import (
    create,
    get_all,
    get_one,
    update,
    delete,
)

lcra_export_v2_api = Blueprint('lcra_export_v2_api', __name__)

lcra_export_v2_api.add_url_rule('/', view_func=create, **{'methods':['POST']})
lcra_export_v2_api.add_url_rule('/', view_func=get_all, **{'methods':['GET']})
lcra_export_v2_api.add_url_rule('/<int:lcra_export_id>', view_func=get_one, **{'methods':['GET']})
lcra_export_v2_api.add_url_rule('/<int:lcra_export_id>', view_func=update, **{'methods':['PUT', 'PATCH']})
lcra_export_v2_api.add_url_rule('/<int:lcra_export_id>', view_func=delete, **{'methods':['DELETE']})
