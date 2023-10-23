from flask import request
from src.models import ClientPayee
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ClientPayeeSchema

client_payee_schema = ClientPayeeSchema()


@Auth.auth_required
def create():
  """
  Create ClientPayee Function
  """
  try:
    req_data = request.get_json()
    data, error = client_payee_schema.load(req_data)
    if error:
      return custom_response(error, 400)

    client_payee = ClientPayee(data)
    client_payee.save()

    data = client_payee_schema.dump(client_payee).data
    return custom_response(data, 201)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_all():
  """
  Get All ClientPayee
  """
  try:
    client_payees = ClientPayee.get_all_client_payees()
    data = client_payee_schema.dump(client_payees, many=True).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_one(client_payees_id):
  """
  Get A ClientPayee
  """
  try:
    client_payee = ClientPayee.get_one_client_payee(client_payees_id)
    if not client_payee:
      return custom_response({'status': 'error', 'msg': 'client_payee not found'}, 404)
    data = client_payee_schema.dump(client_payee).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def update(client_payees_id):
  """
  Update A ClientPayee
  """
  try:
    req_data = request.get_json()
    client_payee = ClientPayee.get_one_client_payee(client_payees_id)
    if not client_payee:
      return custom_response({'status': 'error', 'msg': 'client_payee not found'}, 404)

    if req_data:
      data, error = client_payee_schema.load(req_data, partial=True)
      if error:
        return custom_response(error, 400)
      client_payee.update(data)
      
    else:
      client_payee = ClientPayee.query.filter_by(is_deleted=False, id=client_payees_id).first()
    
    data = client_payee_schema.dump(client_payee).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def delete(client_payees_id):
  """
  Delete A ClientPayee
  """
  try:
    client_payee = ClientPayee.get_one_client_payee(client_payees_id)
    if not client_payee:
      return custom_response({'status': 'error', 'msg': 'client_payee not found'}, 404)
    
    # client_payee.is_deleted = True
    # client_payee.deleted_at = datetime.datetime.utcnow()

    client_payee.delete()
    return custom_response({'status': 'success', 'msg': 'Clients payee deleted'}, 202)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)

