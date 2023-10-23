from flask import json, Response
import os
from src.resources.v2.helpers.convert_datetime import utc_to_local


def custom_response(data, status_code=200):
    """
    Custom Response Function
    """
    return Response(
        mimetype="application/json",
        response=json.dumps(data),
        status=status_code,
        headers={"Current-Date": utc_to_local()},
    )


def api_response(
    payload=None, status=None, status_code=200, msg=None, path=None, source="funding"
):

    response = {"api_version": os.getenv("API_VERSION") or "v1.0.0"}

    if status:
        response["status"] = str(status)

    if msg:
        response["msg"] = msg

    if path:
        response["path"] = path

    if payload is not None or payload == [] or payload == {}:
        response["payload"] = payload

    return Response(
        mimetype="application/json",
        response=json.dumps(dict(response, source=source)),
        status=status_code,
        headers={"Current-Date": utc_to_local()},
    )
