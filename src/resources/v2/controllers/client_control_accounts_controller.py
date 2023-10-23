from flask import request
from src.models import ClientControlAccounts
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ClientControlAccountsSchema

client_control_account_schema = ClientControlAccountsSchema()


@Auth.auth_required
def create():
  """
  Create ClientControlAccounts Function
  """
  try:
    req_data = request.get_json()
    data, error = client_control_account_schema.load(req_data)
    if error:
      return custom_response(error, 400)

    client_control_account = ClientControlAccounts(data)
    client_control_account.save()

    data = client_control_account_schema.dump(client_control_account).data
    return custom_response(data, 201)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_all():
  """
  Get All ClientControlAccounts
  """
  try:
    client_control_accounts = ClientControlAccounts.get_all_client_control_accounts()
    data = client_control_account_schema.dump(client_control_accounts, many=True).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def get_one(client_control_account_id):
  """
  Get A ClientControlAccounts
  """
  try:
    client_control_account = ClientControlAccounts.get_one_client_control_account(client_control_account_id)
    if not client_control_account:
      return custom_response({'status': 'error', 'msg': 'client_control_account not found'}, 404)
    data = client_control_account_schema.dump(client_control_account).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def update(client_control_account_id):
  """
  Update A ClientControlAccounts
  """
  try:
    req_data = request.get_json()
    client_control_account = ClientControlAccounts.get_one_client_control_account(client_control_account_id)
    if not client_control_account:
      return custom_response({'status': 'error', 'msg': 'client_control_account not found'}, 404)
    
    if req_data:
      data, error = client_control_account_schema.load(req_data, partial=True)
      if error:
        return custom_response(error, 400)
      client_control_account.update(data)
    
    else:
      client_control_account = ClientControlAccounts.query.filter_by(is_deleted=False, id=client_control_account_id).first()

    data = client_control_account_schema.dump(client_control_account).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)


@Auth.auth_required
def delete(client_control_account_id):
  """
  Delete A ClientControlAccounts
  """
  try:
    client_control_account = ClientControlAccounts.get_one_client_control_account(client_control_account_id)
    if not client_control_account:
      return custom_response({'status': 'error', 'msg': 'client_control_account not found'}, 404)

    # client_control_account.is_deleted = True
    # client_control_account.deleted_at = datetime.datetime.utcnow()

    client_control_account.delete()
    return custom_response({'status': 'success', 'msg': 'Clients control account deleted'}, 202)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)
