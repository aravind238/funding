from flask import request
from src.models import ClientDebtor
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ClientDebtorSchema

client_debtor_schema = ClientDebtorSchema()


@Auth.auth_required
def create():
  """
  Create ClientDebtor Function 
  """
  try:
    req_data = request.get_json()
    data, error = client_debtor_schema.load(req_data)
    if error:
      return custom_response(error, 400)

    client_debtor = ClientDebtor(data)
    client_debtor.save()

    data = client_debtor_schema.dump(client_debtor).data
    return custom_response(data, 201)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_all():
  """
  Get All ClientDebtor
  """
  try:
    client_debtors = ClientDebtor.get_all_client_debtors()
    data = client_debtor_schema.dump(client_debtors, many=True).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_one(client_debtors_id):
  """
  Get A ClientDebtor
  """
  try:
    client_debtor = ClientDebtor.get_one_client_debtor(client_debtors_id)
    if not client_debtor:
      return custom_response({'status': 'error', 'msg': 'client_debtor not found'}, 404)
      
    data = client_debtor_schema.dump(client_debtor).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def update(client_debtors_id):
  """
  Update A ClientDebtor
  """
  try:
    req_data = request.get_json()
    client_debtor = ClientDebtor.get_one_client_debtor(client_debtors_id)
    if not client_debtor:
      return custom_response({'status': 'error', 'msg': 'client_debtor not found'}, 404)
    
    if req_data:
      data, error = client_debtor_schema.load(req_data, partial=True)
      if error:
        return custom_response(error, 400)
      client_debtor.update(data)
    else:
      client_debtor = ClientDebtor.query.filter_by(is_deleted=False, id=client_debtors_id).first()

    data = client_debtor_schema.dump(client_debtor).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def delete(client_debtors_id):
  """
  Delete A ClientDebtor
  """
  try:
    client_debtor = ClientDebtor.get_one_client_debtor(client_debtors_id)
    if not client_debtor:
      return custom_response({'status': 'error', 'msg': 'client_debtor not found'}, 404)
    
    client_debtor.is_deleted = True
    client_debtor.deleted_at = datetime.datetime.utcnow()

    client_debtor.save()
    return custom_response({'status': 'success', 'msg': 'Client debtor deleted'}, 202)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)
