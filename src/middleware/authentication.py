import os
import datetime
from flask import json, Response, request, g, jsonify
from functools import wraps
import requests

class Auth():
    @staticmethod
    def auth_required(func):
        """
        Auth decorator
        """
        @wraps(func)
        def decorated_auth(*args, **kwargs):
            if "auth-token" not in request.headers or request.headers["auth-token"] == "":
                return Response(
                    mimetype="application/json",
                    response=json.dumps(
                        {
                            "status": "error",
                            "msg": "Auth token is not available, please login to get one",
                        }
                    ),
                    status=401,
                )
            auth_token = request.headers["auth-token"]
            
            # validate user
            app_identifier = os.getenv("APP_IDENTIFIER")
            url = os.getenv("AUTH_URL") + "v2/auth/verify"
            headers = {"auth-token": auth_token, "api-token": os.getenv("API_TOKEN")}
            params = {"app_identifier": app_identifier}

            msg = "auth/verify Error: Something went wrong, please login again"
            status_code = 401
            try:
                get_request = requests.get(url=url, headers=headers, params=params)

                # extracting data in json format
                data = get_request.json()
                status_code = get_request.status_code
                if "msg" in data:
                    msg = data["msg"]

            except requests.ConnectionError as e:
                msg = f"Connection Error: {e}"
                status_code = 502
            except requests.HTTPError as e:
                msg = f"HTTP Error: {e}"
                status_code = 400
            except requests.Timeout as e:
                msg = f"Timeout Error: {e}"
                status_code = 408
            except Exception as e:
                msg = f"auth/verify RequestException Error: {e}"
                status_code = 400

            if status_code != 200:
                return Response(
                    mimetype="application/json",
                    response=json.dumps({"status": "error", "msg": str(msg)}),
                    status=status_code,
                )

            return func(*args, **kwargs)
        return decorated_auth


    def has_request_permission(**req_args):
        """
        Decorator for checking Request create/view/edit/delete permission
        """
        def decorator(func):
            @wraps(func)
            def decorated_function(*args, **kwargs):
                # request_type: credit_limit/soa/reserve_release/compliance_repository/collection_notes
                request_type = req_args.get("request_type", None)
                msg = "You don’t have permission."
                has_permission = False

                # get show_requests from auth api
                from src.middleware.permissions import Permissions
                get_user_role_permissions = Permissions.get_user_role_permissions()
                # show requests
                show_requests = get_user_role_permissions["show_requests"]
                # user role
                user_role = get_user_role_permissions["user_role"]

                # checking, if has request_type in show_requests getting from auth api
                if (
                    show_requests
                    and request_type in list(show_requests.keys())
                    and show_requests[request_type]
                ):
                    has_permission = True

                # compliance repository: AE/BO can only view access(LC-2084)
                # collection_notes: AE/BO can only view access
                if (
                    request_type 
                    and request_type in [Permissions.compliance_repository, Permissions.collection_notes]
                    and user_role in [Permissions.ae, Permissions.bo]
                    and has_permission
                    and request.method not in ["GET"]
                ):
                    has_permission = False

                if request.method == "GET":
                    msg = f"You don’t have permission to view the request."
                if request.method == "POST":
                    msg = f"You don’t have permission to create the request."
                if request.method in ["PATCH", "PUT"]:
                    msg = f"You don’t have permission to edit the request."
                if request.method == "DELETE":
                    msg = f"You don’t have permission to delete the request."

                if req_args.get("msg"):
                    msg = req_args.get("msg")

                # show error, if don't have permission
                if not has_permission:
                    return Response(
                        mimetype="application/json",
                        response=json.dumps({"status": "error", "msg": f"{msg}"}),
                        status=403,
                    )
                return func(*args, **kwargs)
            return decorated_function
        return decorator
