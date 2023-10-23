from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from .import db

from src.resources.v2.helpers.response import api_response


def error_handler(e):
  if isinstance(e, HTTPException):
    return api_response(status="error", msg=e.description, status_code=e.code)

  if isinstance(e, ValidationError):
    if type(e.messages) == dict and e.messages.get("_schema"):
      e = e.messages.get("_schema")
    else:
      e = e.messages
    return api_response(status="error", msg=e, status_code=404)

  if isinstance(e, SQLAlchemyError):
    if hasattr(e, "orig") and hasattr(e.orig, "args"):
      e = e.orig.args
    else:
      e = str(e)
    db.session.rollback()
    return api_response(status="error", msg=e, status_code=404)

  return api_response(status="error", msg=str(e), status_code=404)


def catch_all(path):
  return api_response(
    status="error",
    path=path,
    msg="The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
    status_code=404,
  )
