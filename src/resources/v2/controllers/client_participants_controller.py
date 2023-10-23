from flask import request
from src.models import ClientParticipant
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ClientParticipantSchema

client_participants_schema = ClientParticipantSchema()


@Auth.auth_required
def create():
  """
  Create ClientParticipant Function
  """
  try:
    req_data = request.get_json()
    data, error = client_participants_schema.load(req_data)
    if error:
      return custom_response(error, 400)

    client_participant = ClientParticipant(data)
    client_participant.save()

    data = client_participants_schema.dump(client_participant).data
    return custom_response(data, 201)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_all():
  """
  Get All ClientParticipant
  """
  try:
    client_participants = ClientParticipant.get_all_client_participants()
    data = client_participants_schema.dump(client_participants, many=True).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_one(client_participants_id):
  """
  Get A ClientParticipant
  """
  try:
    client_participant = ClientParticipant.get_one_client_participant(client_participants_id)
    if not client_participant:
      return custom_response({'status': 'error', 'msg': 'client_participant not found'}, 404)

    data = client_participants_schema.dump(client_participant).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def update(client_participants_id):
  """
  Update A ClientParticipant
  """
  try:
    req_data = request.get_json()
    client_participant = ClientParticipant.get_one_client_participant(client_participants_id)
    if not client_participant:
      return custom_response({'status': 'error', 'msg': 'client_participant not found'}, 404)
    
    if req_data:
      data, error = client_participants_schema.load(req_data, partial=True)
      if error:
        return custom_response(error, 400)
      client_participant.update(data)
    
    else:
      client_participant = ClientParticipant.query.filter_by(is_deleted=False, id=client_participants_id).first()
    
    data = client_participants_schema.dump(client_participant).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def delete(client_participants_id):
  """
  Delete A ClientParticipant
  """
  try:
    client_participant = ClientParticipant.get_one_client_participant(client_participants_id)
    if not client_participant:
      return custom_response({'status': 'error', 'msg': 'client_participant not found'}, 404)
    
    # client_participant.is_deleted = True
    # client_participant.deleted_at = datetime.datetime.utcnow()

    client_participant.delete()
    return custom_response({'status': 'success', 'msg': 'Clients participant deleted'}, 202)

  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)
