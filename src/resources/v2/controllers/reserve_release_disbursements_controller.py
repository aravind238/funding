from flask import request
from src.models import *
import datetime
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ReserveReleaseDisbursementsSchema

reserve_release_disbursements_schema = ReserveReleaseDisbursementsSchema()


 
@Auth.auth_required
def create():
    """
    Create a ReserveReleaseDisbursements
    """
    try:
        request_data = request.get_json()
        data, error = reserve_release_disbursements_schema.load(request_data)
        if error:
            return custom_response(error, 400)
        
        disbursements_id = request_data['disbursements_id']
        disbursements = Disbursements.query.filter_by(id=disbursements_id, is_deleted=False, soa_id=None).first()
        if not disbursements:
            return custom_response({"status": "error", "msg": "Disbursements not found"}, 404)

        reserve_release_id = request_data['reserve_release_id']
        reserve_release = ReserveRelease.query.filter_by(id=reserve_release_id, is_deleted=False).first()
        if not reserve_release:
            return custom_response({"status": "error", "msg": "Reserve Release not found"}, 404)

        reserve_release_disbursements = ReserveReleaseDisbursements(data)
        
        # save
        reserve_release_disbursements.save()

        # Already exists
        if reserve_release_disbursements.id is None:
            reserve_release_disbursements = ReserveReleaseDisbursements.query.filter_by(disbursements_id=disbursements_id, reserve_release_id=reserve_release_id, is_deleted=False).first()

        data = reserve_release_disbursements_schema.dump(reserve_release_disbursements).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All ReserveReleaseDisbursements
    """
    try:
        reserve_release_disbursements = ReserveReleaseDisbursements.query.filter_by(is_deleted=False)
        data = reserve_release_disbursements_schema.dump(reserve_release_disbursements, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(reserve_release_disbursements_id):
    """
    Get A ReserveReleaseDisbursements
    """
    try:
        reserve_release_disbursements = ReserveReleaseDisbursements.query.filter_by(id=reserve_release_disbursements_id, is_deleted=False).first()
        if not reserve_release_disbursements:
            return custom_response({"status": "error", "msg": "reserve_release_disbursements not found"}, 404)

        data = reserve_release_disbursements_schema.dump(reserve_release_disbursements).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(reserve_release_disbursements_id):
    """
    Update A ReserveReleaseDisbursements
    """
    try:
        request_data = request.get_json()
        reserve_release_disbursements = ReserveReleaseDisbursements.query.filter_by(id=reserve_release_disbursements_id, is_deleted=False).first()
        if not reserve_release_disbursements:
            return custom_response({"status": "error", "msg": "reserve_release_disbursements not found"}, 404)

        if request_data:
            data, error = reserve_release_disbursements_schema.load(request_data, partial=True)
            if error:
                return custom_response(error, 400)
            reserve_release_disbursements.update(data)
        
        data = reserve_release_disbursements_schema.dump(reserve_release_disbursements).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(reserve_release_disbursements_id):
    """
    Delete A ReserveReleaseDisbursements
    """
    try:
        reserve_release_disbursements = ReserveReleaseDisbursements.query.filter_by(id=reserve_release_disbursements_id, is_deleted=False).first()
        if not reserve_release_disbursements:
            return custom_response({"status": "error", "msg": "reserve_release_disbursements not found"}, 404)
        
        reserve_release_disbursements.delete()
        return custom_response({"status": "success", "msg": "Reserve release disbursement deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)
        