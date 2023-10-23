from flask import request
from src.models import Logs
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import LogsSchema

logs_schema = LogsSchema()


@Auth.auth_required
def create():
    """
    Create Logs Function
    """
    try:
        req_data = request.get_json()
        data, error = logs_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        log = Logs(data)
        log.save()

        data = logs_schema.dump(log).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Logs
    """
    try:
        logs = Logs.get_all_logs()
        data = logs_schema.dump(logs, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(log_id):
    """
    Get A Logs
    """
    try:
        log = Logs.get_one_log(log_id)
        if not log:
            return custom_response({"status": "error", "msg": "log not found"}, 404)
        data = logs_schema.dump(log).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(log_id):
    """
    Update A Logs
    """
    try:
        req_data = request.get_json(silent=True)

        log = Logs.get_one_log(log_id)
        if not log:
            return custom_response({"status": "error", "msg": "log not found"}, 404)

        if req_data:
            data, error = logs_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            log.update(data)

        data = logs_schema.dump(log).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(log_id):
    """
  Delete A Logs
  """
    try:
        log = Logs.get_one_log(log_id)
        if not log:
            return custom_response({"status": "error", "msg": "log not found"}, 404)

        # log.is_deleted = True
        # log.deleted_at = datetime.datetime.utcnow()

        log.delete()
        return custom_response({"status": "success", "msg": "Log deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)

