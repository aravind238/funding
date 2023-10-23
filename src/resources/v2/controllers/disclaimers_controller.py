from flask import request
import datetime
from src.models import Disclaimers
from src.middleware.authentication import Auth
from src import db
import os
import requests
from src.resources.v2.schemas import DisclaimersSchema, DisclaimerOnlySchema
from src.resources.v2.helpers import custom_response

disclaimers_schema = DisclaimersSchema()
disclaimer_only_schema = DisclaimerOnlySchema()

 
@Auth.auth_required
def create():
    """
    Create Disclaimers
    """
    try:
        request_data = request.get_json()
        data, error = disclaimers_schema.load(request_data)
        if error:
            return custom_response(error, 400)

        disclaimers = Disclaimers(data)
        disclaimers.save()

        data = disclaimers_schema.dump(disclaimers).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Disclaimers
    """
    try:
        disclaimer_type = request.args.get("disclaimer_type", None, type=str)

        disclaimers = Disclaimers.query.filter_by(is_deleted=False)
        if disclaimer_type:
            disclaimers = disclaimers.filter(
                Disclaimers.disclaimer_type == disclaimer_type
            )

        data = disclaimers_schema.dump(disclaimers, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(disclaimer_id):
    """
    Get A Disclaimer
    """
    try:
        disclaimer = Disclaimers.query.filter_by(
            id=disclaimer_id, is_deleted=False
        ).first()
        if not disclaimer:
            return custom_response({"status": "error", "msg": "Disclaimer not found"}, 404)

        data = disclaimers_schema.dump(disclaimer).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(disclaimer_id):
    """
    Update A Disclaimer
    """
    try:
        request_data = request.get_json()
        disclaimer = Disclaimers.query.filter_by(
            id=disclaimer_id, is_deleted=False
        ).first()
        if not disclaimer:
            return custom_response({"status": "error", "msg": "Disclaimer not found"}, 404)

        if request_data:
            data, error = disclaimers_schema.load(request_data, partial=True)
            if error:
                return custom_response(error, 400)
            disclaimer.update(data)

        data = disclaimers_schema.dump(disclaimer).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(disclaimer_id):
    """
    Delete A Disclaimer
    """
    try:
        disclaimer = Disclaimers.query.filter_by(
            id=disclaimer_id, is_deleted=False
        ).first()
        if not disclaimer:
            return custom_response({"status": "error", "msg": "Disclaimer not found"}, 404)

        disclaimer.delete()
        return custom_response({"status": "success", "msg": "Disclaimer deleted"}, 202)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_different_disclaimers():
    try:
        disclaimer_type = request.args.get('disclaimer_type', None, type=str)

        disclaimers = Disclaimers.query.filter_by(is_deleted=False)
        if disclaimer_type:
            disclaimers = disclaimers.filter(Disclaimers.disclaimer_type == disclaimer_type)

        disclaimers_data = disclaimer_only_schema.dump(disclaimers, many=True).data

        if not disclaimers_data:
            return custom_response({"status": "error", "msg": "Disclaimers not found"}, 404)

        return custom_response(disclaimers_data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)
