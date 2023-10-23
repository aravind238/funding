from flask import request
from src.models import LCRAExport
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import LCRAExportSchema

lcra_export_schema = LCRAExportSchema()


@Auth.auth_required
def create():
    """
    Create LCRAExport Function
    """
    try:
        req_data = request.get_json()
        data, error = lcra_export_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        lcra_export = LCRAExport(data)
        lcra_export.save()

        data = lcra_export_schema.dump(lcra_export).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All LCRAExport
    """
    try:
        lcra_exports = LCRAExport.get_all_lcra_exports()
        data = lcra_export_schema.dump(lcra_exports, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(lcra_export_id):
    """
  Get A LCRAExport
  """
    try:
        lcra_export = LCRAExport.get_one_lcra_export(lcra_export_id)
        if not lcra_export:
            return custom_response({"status": "error", "msg": "lcra_export not found"}, 404)
        data = lcra_export_schema.dump(lcra_export).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(lcra_export_id):
    """
  Update A LCRAExport
  """
    try:
        req_data = request.get_json()
        lcra_export = LCRAExport.get_one_lcra_export(lcra_export_id)
        if not lcra_export:
            return custom_response({"status": "error", "msg": "lcra_export not found"}, 404)

        if req_data:
            data, error = lcra_export_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            lcra_export.update(data)

        else:
            lcra_export = LCRAExport.query.filter_by(
                id=lcra_export_id
            ).first()

        data = lcra_export_schema.dump(lcra_export).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(lcra_export_id):
    """
  Delete A LCRAExport
  """
    try:
        lcra_export = LCRAExport.get_one_lcra_export(lcra_export_id)
        if not lcra_export:
            return custom_response({"status": "error", "msg": "lcra_export not found"}, 404)

        # lcra_export.is_deleted = True
        # lcra_export.deleted_at = datetime.datetime.utcnow()

        lcra_export.delete()
        return custom_response({"status": "success", "msg": "LCRA export deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)

