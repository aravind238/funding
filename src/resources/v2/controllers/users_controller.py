from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import custom_response
from flask import request


@Auth.auth_required
def get_role_permissions():
    try:
        # Default active=True, for getting all true values of user role permissions
        active = request.args.get("active", True, type=lambda v: v.lower() == "true")
        
        # user role and permissions
        get_user_role_permissions = Permissions.get_user_role_permissions(active=active)

        if get_user_role_permissions["status_code"] == 200:
            return custom_response(get_user_role_permissions["user_permissions"], 200)

        return custom_response(
            {"status": "error", "msg": str(get_user_role_permissions["msg"])},
            get_user_role_permissions["status_code"],
        )

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_users():
    try:
        # Get user role and permissions
        get_user_role_permissions = Permissions.get_user_role_permissions()

        organization_ids = []
        if get_user_role_permissions["status_code"] == 200:
            # Get organization ids
            organization_ids = get_user_role_permissions["organization_access"]

        permissions_include = [
            {
                "app_resource_name": "organization_access",
                "permissions": organization_ids,
            }
        ]

        # get users based off organization ids
        get_users = Permissions.search_users_by_permissions(
            permissions_include=permissions_include, require_all=False
        )

        if get_users["status_code"] == 200:
            return custom_response(get_users["users"], 200)

        return custom_response(
            {"status": "error", "msg": str(get_users["msg"])}, get_users["status_code"]
        )

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def check_request_update_permission():
    try:
        request_type = request.args.get("request", None, type=str)
        request_id = request.args.get("id", None, type=int)
        update_request_status = request.args.get("update_status", None, type=str)
        # request status list
        request_status_list = [
            "draft",
            "action_required",
            "rejected",
            "pending",
            "reviewed",
            "approved",
            "completed",
        ]

        if update_request_status and update_request_status not in request_status_list:
            return custom_response(
                {
                    "status": "error",
                    "msg": f"{update_request_status} is not a valid status",
                },
                404,
            )

        # checking request type is soa/reserve release
        if request_type == "soa":
            from src.models import SOA

            user_request = SOA.query.filter_by(id=request_id, is_deleted=False).first()
        elif request_type == "reserve-release":
            from src.models import ReserveRelease

            user_request = ReserveRelease.query.filter_by(
                id=request_id, is_deleted=False
            ).first()
        elif request_type == "payee":
            from src.models import Payee

            user_request = Payee.query.filter_by(
                id=request_id, is_deleted=False, is_active=True
            ).first()
        else:
            user_request = None

        if not user_request:
            return custom_response(
                {"status": "error", "msg": "Request/id is invalid"}, 404
            )
        
        # check user request permission
        if request_type == "payee":
            request_permission = Permissions.can_update_payee(
                request=user_request, update_request_status=update_request_status
            )
        else:
            request_permission = Permissions.has_request_updating_permissions(
                request=user_request, update_request_status=update_request_status
            )
        
        
        return custom_response(
            {
                "status": request_permission["status"], 
                "msg": request_permission["msg"]
            },
            request_permission["status_code"],
        )

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)
