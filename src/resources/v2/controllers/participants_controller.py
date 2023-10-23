from flask import request
from src.models import *
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ParticipantSchema

participants_schema = ParticipantSchema()


@Auth.auth_required
def create():
    """
    Create Participant Function
    """
    try:
        req_data = request.get_json()
        data, error = participants_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        participants = Participant(data)
        participants.save()

        data = participants_schema.dump(participants).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Participant
    """
    try:
        client_id = request.args.get("client_id", None, type=int)
        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        search = request.args.get("search", None, type=str)
        ordering = request.args.get("ordering", None, type=str)

        if page > 0:
            data = ParticipantsListing.get_paginated_participants(
                client_id=client_id,
                page=page,
                rpp=rpp,
                search=search,
                ordering=ordering,
            )
        else:
            data = ParticipantsListing.get_all(client_id=client_id)

        if data is None:
            data = []

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(participant_id):
    """
    Get A Participant
    """
    try:
        participants = Participant.get_one_participants(participant_id)
        if not participants:
            return custom_response({"status": "error", "msg": "participants not found"}, 404)
        data = participants_schema.dump(participants).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(participant_id):
    """
    Update A Participant
    """
    try:
        req_data = request.get_json()
        participants = Participant.get_one_participants(participant_id)
        if not participants:
            return custom_response({"status": "error", "msg": "participants not found"}, 404)

        if req_data:
            data, error = participants_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            participants.update(data)

        else:
            participants = Participant.query.filter_by(
                is_deleted=False, id=participant_id
            ).first()

        data = participants_schema.dump(participants).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(participant_id):
    """
    Delete A Participant
    """
    try:
        participants = Participant.get_one_participants(participant_id)
        if not participants:
            return custom_response({"status": "error", "msg": "participants not found"}, 404)

        # participants.is_deleted = True
        # participants.deleted_at = datetime.datetime.utcnow()

        participants.delete()
        return custom_response({"status": "success", "msg": "Participant deleted"}, 202)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)

