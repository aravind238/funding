from flask import request
from src.models import ApprovalsHistory
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ApprovalsHistorySchema

approvals_history_schema = ApprovalsHistorySchema()

@Auth.auth_required
def create():
  """
  Create ApprovalsHistory Function
  """
  try:
    request_data = request.get_json()
    data, error = approvals_history_schema.load(request_data)
    if error:
      return custom_response(error, 400)

    approvals_history = ApprovalsHistory(data)
    approvals_history.save()
    data = approvals_history_schema.dump(approvals_history).data
    return custom_response(data, 201)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)

@Auth.auth_required
def get_all():
  """
  Get All ApprovalsHistory
  """
  try:
    approvals_history = ApprovalsHistory.get_all_approvals_history()
    data = approvals_history_schema.dump(approvals_history, many=True).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)

@Auth.auth_required
def get_one(approvals_history_id):
  """
  Get A ApprovalsHistory
  """
  try:
    approvals_history = ApprovalsHistory.get_one_approval_history(approvals_history_id)
    if not approvals_history:
      return custom_response({'status': 'error', 'msg': 'approvals history not found'}, 404)
    
    data = approvals_history_schema.dump(approvals_history).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)

@Auth.auth_required
def update(approvals_history_id):
  """
  Update A ApprovalsHistory
  """
  try:
    request_data = request.get_json()
    approvals_history = ApprovalsHistory.get_one_approval_history(approvals_history_id)
    if not approvals_history:
      return custom_response({'status': 'error', 'msg': 'approvals history not found'}, 404)
    
    if request_data:
      data, error = approvals_history_schema.load(request_data, partial=True)
      if error:
        return custom_response(error, 400)
      approvals_history.update(data)

    else:
      approvals_history = ApprovalsHistory.query.filter_by(is_deleted=False, id=approvals_history_id).first()
    
    data = approvals_history_schema.dump(approvals_history).data
    return custom_response(data, 200)
  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)

@Auth.auth_required
def delete(approvals_history_id):
  """
  Delete A ApprovalsHistory
  """
  try:
    approvals_history = ApprovalsHistory.get_one_approval_history(approvals_history_id)
    if not approvals_history:
      return custom_response({'status': 'error', 'msg': 'approvals history not found'}, 404)

    # approvals_history.is_deleted = True
    # approvals_history.deleted_at = datetime.datetime.utcnow()

    approvals_history.delete()
    return custom_response({'status': 'success', 'msg': 'Approvals history deleted'}, 202)

  except Exception as e:
    return custom_response({'status': 'error', 'msg': 'Exception: ' + str(e)}, 404)

