import os
import datetime
from flask import json, Response, request, g, jsonify, abort
from functools import wraps
import requests
from src.middleware.authentication import Auth


class Permissions(object):

    principal = "principal"
    ae = "ae"
    bo = "bo"
    user_roles = [principal, ae, bo]

    compliance_repository = "compliance_repository"
    collection_notes = "collection_notes" # being used in controller
    credit_limit = "credit_limit"
    generic_request = "generic_request"
    reserve_release = "reserve_release"
    soa = "soa"
    verification_notes = "verification_notes"
    invoice_supporting_documents = "invoice_supporting_documents"

    @staticmethod
    def get_user_role_permissions(active=True):
        """[Get users Role Permissions]

        Args:
            active (bool, optional): [description]. Defaults to True.

        Returns:
            "status_code": status code,
            "msg": msg,
            "user_role": user role,
            "user_permissions": user permissions,
            "organization_access": organization ids,
        """
        try:
            if ("auth-token" not in request.headers) or (
                not request.headers["auth-token"]
            ):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "msg": "Auth token is invalid, please login again",
                        }
                    ),
                    401,
                )

            auth_token = request.headers["auth-token"]

            # api endpoint
            url = (
                os.getenv("AUTH_URL")
                + f'v2/permissions?app_identifier={os.getenv("APP_IDENTIFIER")}'
            )

            # will return only the permissions that are available for the user
            if active:
                url = url + f"&active=true"

            # defining a headers dict for the parameters to be sent to the API
            headers = {"auth-token": auth_token, "api-token": os.getenv("API_TOKEN")}

            # get user permissions and user role
            user_role = None
            user_permissions = {}
            organization_ids = []
            status_code = 500
            get_msg = "Get users Role Permissions- Error: Something went wrong, please login again"
            try:
                # sending get request and saving the response as response object
                result = requests.get(url=url, headers=headers)

                # extracting data in json format
                result_json = result.json()
                status_code = result.status_code

                if "msg" in result_json:
                    get_msg = result_json["msg"]

                payload = result_json["payload"] if "payload" in result_json else {}

                if payload:
                    # get app_flow(principal/ae/bo) which has value True
                    if (
                        "app_flow" in payload
                        and payload["app_flow"]
                        and isinstance(payload["app_flow"], dict)
                    ):
                        app_flow = payload["app_flow"]
                        user_role = list(app_flow.keys())[0]

                    # Get all organization ids from organization_access which have value True
                    if (
                        "organization_access" in payload
                        and payload["organization_access"]
                    ):
                        organization_access = payload["organization_access"]
                        organization_ids = (
                            [k for k, v in organization_access.items() if v == True]
                            if organization_access
                            and isinstance(organization_access, dict)
                            else []
                        )

                    user_permissions = payload

            except requests.ConnectionError as e:
                get_msg = f"Connection Error: {e}"
                status_code = 502
            except requests.HTTPError as e:
                get_msg = f"HTTP Error: {e}"
            except requests.Timeout as e:
                get_msg = f"Timeout Error: {e}"
                status_code = 408
            except Exception as e:
                get_msg = f"Get users Role Permissions- RequestException Error: {e}"

            show_requests = user_permissions.get("show_requests", {})
            show_info = user_permissions.get("show_info", {})
            create_edit_permission = user_permissions.get("create_edit_permission", {})
            return {
                "status_code": status_code,
                "msg": f"{get_msg}",
                "user_role": user_role,
                "user_permissions": user_permissions,
                "organization_access": organization_ids,
                "show_requests": show_requests,
                "show_info": show_info,
                "create_edit_permission": create_edit_permission,
            }

        except Exception as e:
            print("Exception- ", str(e))
            return jsonify({"status": "error", "msg": "Exception: " + str(e)}), 404

    @staticmethod
    def get_user_details(branding=True):
        """[Get User Profile]

        Args:
            branding (bool, optional): [description]. Defaults to True.

        Returns:
            "status_code": status code,
            "msg": msg,
            "user_uuid": user id,
            "first_name": first name,
            "last_name": last name,
            "email": email,
            "business_id": None,
            "business_name": None,
            "branding": {}
        """
        if ("auth-token" not in request.headers) or (not request.headers["auth-token"]):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Auth token is invalid, please login again",
                    }
                ),
                401,
            )

        auth_token = request.headers["auth-token"]

        # api endpoint
        auth_url = os.getenv("AUTH_URL")

        auth_api = "v2/users/profile?branding=false"
        if branding:
            auth_api = "v2/users/profile?branding=true"

        url = auth_url + auth_api

        # defining a headers dict for the parameters to be sent to the API
        headers = {"auth-token": auth_token, "api-token": os.getenv("API_TOKEN")}

        # sending get request and saving the response as response object
        profile_result = requests.get(url=url, headers=headers)

        # extracting data in json format
        profile_result_json = profile_result.json()

        user_uuid = None
        first_name = None
        last_name = None
        email = None
        business_id = None
        business_name = None
        business_branding = {}

        msg = "Something went wrong, please login again"
        if "msg" in profile_result_json:
            msg = profile_result_json["msg"]

        payload = (
            profile_result_json["payload"] if "payload" in profile_result_json else None
        )

        # get user profile details
        if payload:
            for k, v in payload.items():
                if k.lower() == "user":
                    user_uuid = v["id"]
                    first_name = v["first_name"]
                    last_name = v["last_name"]
                    email = v["email"]

                if k.lower() == "active_business":
                    business_name = v["name"]
                    business_id = v["id"]

                if k.lower() == "business_branding":
                    business_branding = v

        return {
            "status_code": profile_result.status_code,
            "msg": msg,
            "user_uuid": user_uuid,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "business_id": business_id,
            "business_name": business_name,
            "business_branding": business_branding,
        }

    @staticmethod
    def get_user_businesses(branding=True):
        """[Get User Businesses details]

        Args:
            branding (bool, optional): [description]. Defaults to True.

        Returns:
            "status_code": status code,
            "msg": msg,
            "payload": payload,
        """
        if ("auth-token" not in request.headers) or (not request.headers["auth-token"]):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Auth token is invalid, please login again",
                    }
                ),
                401,
            )

        auth_token = request.headers["auth-token"]

        # api endpoint
        auth_url = os.getenv("AUTH_URL")

        auth_api = "v2/users/businesses?branding=false"
        if branding:
            auth_api = "v2/users/businesses?branding=true"

        url = auth_url + auth_api

        # defining a headers dict for the parameters to be sent to the API
        headers = {"auth-token": auth_token, "api-token": os.getenv("API_TOKEN")}

        # sending get request and saving the response as response object
        result = requests.get(url=url, headers=headers)

        # extracting data in json format
        result_json = result.json()

        msg = "Something went wrong, please login again"
        if "msg" in result_json:
            msg = result_json["msg"]

        payload = result_json["payload"] if "payload" in result_json else None

        return {
            "status_code": result.status_code,
            "msg": msg,
            "payload": payload,
        }

    @staticmethod
    def search_users_by_permissions(
        active=True, permissions_include=None, require_all=False, permissions_exclude=None
    ):
        """[Search Users By Permissions]

        Args:
            active (bool, optional): [description]. Defaults to True.
            permissions_include ([type], optional): [description]. Defaults to None.
            require_all (bool, optional): [description]. Defaults to False.
            permissions_exclude ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code
            "msg": msg
            "users": users
            "user_emails": get user emails
        """
        try:
            if ("auth-token" not in request.headers) or (
                not request.headers["auth-token"]
            ):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "msg": "Auth token is invalid, please login again",
                        }
                    ),
                    401,
                )

            auth_token = request.headers["auth-token"]
            app_identifier = os.getenv("APP_IDENTIFIER")

            get_users = None
            user_emails = []
            if permissions_include is None:
                return {
                    "status_code": 404,
                    "msg": "Permissions is required",
                    "users": get_users,
                    "user_emails": user_emails,
                }

            # api endpoint
            auth_url = os.getenv("AUTH_URL")
            
            # get users based off param 'active'
            auth_api = f"v2/users/search/permissions?active=false"
            if active:
                auth_api = f"v2/users/search/permissions?active=true"

            url = auth_url + auth_api

            # defining a headers dict for the parameters to be sent to the API
            headers = {
                "auth-token": auth_token,
                "api-token": os.getenv("API_TOKEN"),
            }

            # defining a params dict for the parameters to be sent to the API
            params = {
                "app_identifier": app_identifier,
                "permissions": permissions_include,
                "require_all": require_all,
            }

            if permissions_exclude:
                params = {
                    "app_identifier": app_identifier,
                    "permissions": permissions_include,
                    "excludes": permissions_exclude,
                    "require_all": require_all,
                }

            # sending get request and saving the response as response object
            result = requests.post(url=url, headers=headers, json=params)

            # extracting data in json format
            result_json = result.json()

            payload = result_json["payload"] if "payload" in result_json else None

            # get users
            if payload:
                get_users = payload
                user_emails = [
                    get_result["email"] for get_result in payload if get_result["email"]
                ]

            get_msg = (
                result_json["msg"]
                if "msg" in result_json
                else "Something went wrong, please login again"
            )

            status_code = result.status_code if result.status_code else 500

            return {
                "status_code": status_code,
                "msg": f"{get_msg}",
                "users": get_users,
                "user_emails": user_emails,
            }

        except Exception as e:
            print("Exception- ", str(e))
            return jsonify({"status": "error", "msg": "Exception: " + str(e)}), 404

    @staticmethod
    def has_request_updating_permissions(request=None, update_request_status=None):
        """[Check user can update request]

        Args:
            request ([type], optional): [description]. Defaults to None.
            update_request_status ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code,
            "status": success/error,
            "msg": msg
        """
        try:
            if not request:
                # no request
                return {
                    "status_code": 404,
                    "status": "error",
                    "msg": f"Request not found.",
                }

            get_user_role_permissions = Permissions.get_user_role_permissions()
            user_cannot_update = []

            # get_user_role_permissions status != 200
            if get_user_role_permissions["status_code"] != 200:
                return {
                    "status_code": get_user_role_permissions["status_code"],
                    "status": "error",
                    "msg": f"{get_user_role_permissions['msg']}",
                }

            # user role
            user_role = get_user_role_permissions["user_role"]
            if user_role is None:
                return {
                    "status_code": 404,
                    "status": "error",
                    "msg": f"app_flow: {user_role} - User role not selected, must be {Permissions.principal}/{Permissions.ae}/{Permissions.bo}",
                }

            # for principal
            if user_role.lower() == Permissions.principal:
                user_can_update = ["draft", "action_required"]
                user_cannot_update = [
                    "principal_rejection",
                    "action_required_by_client",
                    "rejected",
                    "pending",
                    "reviewed",
                    "approved",
                    "completed",
                ]

                # remove element from user_cannot_update
                if update_request_status and request.status.value in user_can_update:
                    if (
                        update_request_status == "pending"
                        and "pending" in user_cannot_update
                    ):
                        user_cannot_update.remove("pending")

                    if (
                        update_request_status == "action_required"
                        and "action_required" not in user_cannot_update
                    ):
                        user_cannot_update.append("action_required")

            # for ae
            if user_role.lower() == Permissions.ae:
                user_can_update = ["pending", "reviewed"]
                user_cannot_update = [
                    "principal_rejection",
                    "action_required_by_client",
                    "draft",
                    "action_required",
                    "rejected",
                    "approved",
                    "completed",
                ]

                # remove element from user_cannot_update
                if update_request_status and request.status.value in user_can_update:
                    if (
                        update_request_status == "approved"
                        and "approved" in user_cannot_update
                    ):
                        user_cannot_update.remove("approved")

                    if (
                        update_request_status == "action_required"
                        and "action_required" in user_cannot_update
                    ):
                        user_cannot_update.remove("action_required")

                    if (
                        update_request_status == "rejected"
                        and "rejected" in user_cannot_update
                    ):
                        user_cannot_update.remove("rejected")

                    if (
                        update_request_status == "pending"
                        and "pending" not in user_cannot_update
                    ):
                        user_cannot_update.append("pending")

            # for bo
            if user_role.lower() == Permissions.bo:
                user_can_update = ["approved"]
                user_cannot_update = [
                    "principal_rejection",
                    "action_required_by_client",
                    "draft",
                    "action_required",
                    "rejected",
                    "pending",
                    "reviewed",
                    "completed",
                ]

                # remove element 'completed' from user_cannot_update
                if update_request_status and request.status.value in user_can_update:
                    if (
                        update_request_status == "completed"
                        and "completed" in user_cannot_update
                    ):
                        user_cannot_update.remove("completed")

                    if (
                        update_request_status == "action_required"
                        and "action_required" in user_cannot_update
                    ):
                        user_cannot_update.remove("action_required")

                    if (
                        update_request_status == "rejected"
                        and "rejected" in user_cannot_update
                    ):
                        user_cannot_update.remove("rejected")

            # for soa
            if request.object_as_string().lower() == "soa":
                request_type_string = f"{request.object_as_string()} - {request.client.ref_client_no}-SOAID{request.soa_ref_id}"

            # for reserve release
            if request.object_as_string().lower() == "reserve release":
                request_type_string = f"{request.object_as_string()} - {request.id}"

            add_msg = ""
            if update_request_status is not None:
                add_msg = f"to {update_request_status}"

            # if request status is in list(user cannot update)
            if request.status.value in user_cannot_update and not update_request_status:
                return {
                    "status_code": 403,
                    "status": "error",
                    "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value}",
                }
            # if request status is in list(user can update) and have to update status is in list(user cannot update)
            elif (
                request.status.value in user_can_update
                and update_request_status
                and update_request_status in user_cannot_update
            ):
                return {
                    "status_code": 403,
                    "status": "error",
                    "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
                }
            # if request status is not in list(user can update) and have to update status
            elif request.status.value not in user_can_update and update_request_status:
                return {
                    "status_code": 403,
                    "status": "error",
                    "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
                }
            else:
                # user can update request
                return {
                    "status_code": 200,
                    "status": "success",
                    "msg": f"{user_role} has permission for updating {request_type_string} having status {request.status.value} {add_msg}",
                }

        except Exception as e:
            print(f"Exception- {e}")
            return jsonify({"status": "error", "msg": "Exception:" f"{e}"}), 404

    @staticmethod
    def get_users_by_email(emails=[], active=True):
        """[Get Users By Email]

        Args:
            active (bool, optional): [description]. Defaults to True.
            emails (list, optional): [description]. Defaults to [].

        Returns:
            "status_code":  status code,
            "msg": msg,
            "users": get users,
            "user_emails": get user emails,
        """
        if (not emails) or (not isinstance(emails, list)):
            return {
                "status_code": 404,
                "msg": f"Emails not found.",
                "users": [],
                "user_emails": emails,
            }

        if ("auth-token" not in request.headers) or (not request.headers["auth-token"]):
            return abort(401, "Auth token is invalid, please login again")

        auth_token = request.headers["auth-token"]

        # api endpoint
        auth_url = os.getenv("AUTH_URL")
        
        # get users based off param 'active'
        auth_api = f"v2/businesses/users/search?active=false"
        if active:
            auth_api = f"v2/businesses/users/search?active=true"

        url = auth_url + auth_api

        # defining a headers dict for the parameters to be sent to the API
        headers = {"auth-token": auth_token, "api-token": os.getenv("API_TOKEN")}

        # defining a params dict for the parameters to be sent to the API
        params = {"property": "email", "values": emails}

        # sending get request and saving the response as response object
        result = requests.post(url=url, headers=headers, json=params)

        # extracting data in json format
        result_json = result.json()

        # get result
        msg = (
            result_json["msg"]
            if "msg" in result_json
            else "Something went wrong, please login again"
        )

        payload = result_json["payload"] if "payload" in result_json else []

        users = []
        if payload:
            [users.append(results["user"]) for results in payload]

        return {
            "status_code": result.status_code,
            "msg": msg,
            "users": users,
            "user_emails": emails,
        }

    @staticmethod
    def can_update_payee(request=None, update_request_status=None, user_role=None):
        """[check user can update payee]

        Args:
            request ([type], optional): [description]. Defaults to None.
            update_request_status ([type], optional): [description]. Defaults to None.
            user_role ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code,
            "status": error/success,
            "msg": msg
        """
        if not request:
            # no request
            return {"status_code": 404, "status": "error", "msg": f"Request not found."}

        if not user_role:
            get_user_role_permissions = Permissions.get_user_role_permissions()
            user_cannot_update = []

            # get_user_role_permissions status != 200
            if get_user_role_permissions["status_code"] != 200:
                return {
                    "status_code": get_user_role_permissions["status_code"],
                    "status": "error",
                    "msg": f"{get_user_role_permissions['msg']}",
                }

            # user role
            user_role = get_user_role_permissions["user_role"]

        if user_role is None:
            return {
                "status_code": 404,
                "status": "error",
                "msg": f"app_flow: {user_role} - User role not selected, must be {Permissions.principal}/{Permissions.ae}/{Permissions.bo}",
            }

        # for principal
        if user_role.lower() == Permissions.principal:
            user_can_update = ["client_submission", "draft", "action_required"]
            user_cannot_update = [
                "client_draft",
                "principal_rejection",
                "action_required_by_client",
                "rejected",
                "pending",
                "approved",
            ]

            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (
                    request.status.value == "client_submission"
                    or request.status.value == "action_required"
                ) and (
                    "draft" not in user_cannot_update
                    or update_request_status == "draft"
                ):
                    user_cannot_update.append("draft")

                if (
                    request.status.value == "draft"
                    or request.status.value == "action_required"
                ) and (
                    "client_submission" not in user_cannot_update
                    or update_request_status == "client_submission"
                ):
                    user_cannot_update.append("client_submission")

                if (
                    request.status.value == "draft"
                    or request.status.value == "client_submission"
                ) and (
                    "action_required" not in user_cannot_update
                    or update_request_status == "action_required"
                ):
                    user_cannot_update.append("action_required")

                if (
                    update_request_status == "pending"
                    and "pending" in user_cannot_update
                ):
                    user_cannot_update.remove("pending")

                if (
                    request.status.value == "client_submission"
                    and update_request_status == "action_required_by_client"
                    and "action_required_by_client" in user_cannot_update
                ):
                    user_cannot_update.remove("action_required_by_client")

                if (
                    request.status.value == "client_submission"
                    and update_request_status == "principal_rejection"
                    and "principal_rejection" in user_cannot_update
                ):
                    user_cannot_update.remove("principal_rejection")

                if (
                    update_request_status == "action_required"
                    and "action_required" not in user_cannot_update
                ):
                    user_cannot_update.append("action_required")

        # for ae(Doesn't have permissions to edit)
        if user_role.lower() == Permissions.ae:
            user_can_update = []
            user_cannot_update = [
                "client_draft",
                "client_submission",
                "principal_rejection",
                "action_required_by_client",
                "draft",
                "action_required",
                "rejected",
                "pending",
                "approved",
            ]

        # for bo
        if user_role.lower() == Permissions.bo:
            user_can_update = ["pending", "approved"]
            user_cannot_update = [
                "client_draft",
                "client_submission",
                "principal_rejection",
                "action_required_by_client",
                "draft",
                "action_required",
                "rejected",
            ]

            # remove element 'approved' from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (
                    update_request_status == "pending"
                    and "pending" not in user_cannot_update
                ):
                    user_cannot_update.append("pending")

                if (
                    update_request_status == "approved"
                    and "approved" in user_cannot_update
                ):
                    user_cannot_update.remove("approved")

                if (
                    request.status.value == "approved"
                ) and (
                    update_request_status == "approved"
                    and "approved" not in user_cannot_update
                ):
                    user_cannot_update.append("approved")

                if (
                    update_request_status == "rejected"
                    or update_request_status == "action_required"
                ) and update_request_status in user_cannot_update:
                    user_cannot_update.remove(update_request_status)

        # for payee
        if request.object_as_string().lower() == "payee":
            request_type_string = f"{request.object_as_string()} - {request.id}"

        add_msg = ""
        if update_request_status is not None:
            add_msg = f"to {update_request_status}"

        # if request status is in list(user cannot update)
        if request.status.value in user_cannot_update and not update_request_status:
            return {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value}",
            }
        # if request status is in list(user can update) and have to update status is in list(user cannot update)
        elif (
            request.status.value in user_can_update
            and update_request_status
            and update_request_status in user_cannot_update
        ):
            return {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        # if request status is not in list(user can update) and have to update status
        elif request.status.value not in user_can_update and update_request_status:
            return {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        else:
            # user can update request
            return {
                "status_code": 200,
                "status": "success",
                "msg": f"{user_role} has permission for updating {request_type_string} having status {request.status.value} {add_msg}",
            }

    @staticmethod
    def get_business_settings(business_id=None):
        """[Get Business Settings]

        Returns:
            "status_code": status code,
            "msg": msg,
            "payload": payload,
            "control_accounts": control accounts,
            "control_accounts_disclaimer": control account's disclaimer,
        """
        # if ("auth-token" not in request.headers) or (not request.headers["auth-token"]):
        #     return (
        #         jsonify(
        #             {
        #                 "status": "error",
        #                 "message": "Auth token is invalid, please login again",
        #             }
        #         ),
        #         401,
        #     )

        # auth_token = request.headers["auth-token"]

        if not business_id:
            # get business id
            business_id = Permissions.get_user_details()["business_id"]

        # api endpoint
        auth_url = (
            os.getenv("AUTH_URL") + f"v1/integrators/businesses/{business_id}/settings"
        )

        # defining a headers dict for the parameters to be sent to the API
        headers = {"api-token": os.getenv("API_TOKEN")}

        # sending get request and saving the response as response object
        result = requests.get(url=auth_url, headers=headers)

        # extracting data in json format
        result_json = result.json()

        msg = "Something went wrong, please login again"
        if "msg" in result_json:
            msg = result_json["msg"]

        payload = result_json["payload"] if "payload" in result_json else None

        control_accounts = []
        control_accounts_disclaimer = {}
        if payload:
            # import control accounts name from control accounts model
            from src.resources.v2.models.control_accounts_model import (
                ControlAccountsName,
            )

            for p in payload:
                control_accounts_dict = ControlAccountsName.__members__.items()
                p_key = p["key"] if "key" in p else None

                for k, v in control_accounts_dict:
                    # get value of k(control_accounts_dict)
                    v_value = v.value

                    # get control accounts
                    if p_key == "control_accounts":
                        control_accounts = p["value"]

                    # checking, if disclaimer control account == control account(db)
                    if p_key == k:
                        disclaimer_value = p["value"]

                        # checking, if value is null or "none"
                        if not p["value"] or p["value"] == "none":
                            disclaimer_value = None

                        # if not control_accounts:
                        #     control_accounts.append(v_value)
                        control_accounts_disclaimer.update({v_value: disclaimer_value})

        return {
            "status_code": result.status_code,
            "msg": msg,
            "payload": payload,
            "control_accounts": control_accounts,
            "control_accounts_disclaimer": control_accounts_disclaimer,
        }

    def can_update_debtor_limits(
        request=None, update_request_status=None, user_role=None
    ):
        """[check user can update debtor limits]

        Args:
            request ([type], optional): [description]. Defaults to None.
            update_request_status ([type], optional): [description]. Defaults to None.
            user_role ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code,
            "status": error/success,
            "msg": msg
        """
        if not request:
            # no request
            return {"status_code": 404, "status": "error", "msg": f"Request not found."}

        user_can_update = []
        user_cannot_update = []
        if not user_role:
            get_user_role_permissions = Permissions.get_user_role_permissions()

            # get_user_role_permissions status != 200
            if get_user_role_permissions["status_code"] != 200:
                return {
                    "status_code": get_user_role_permissions["status_code"],
                    "status": "error",
                    "msg": f"{get_user_role_permissions['msg']}",
                }

            # user role
            user_role = get_user_role_permissions["user_role"]

        if not user_role:
            return {
                "status_code": 404,
                "status": "error",
                "msg": f"app_flow: {user_role} - User role not selected, must be {Permissions.principal}/{Permissions.ae}",
            }

        # for principal
        if user_role.lower() == Permissions.principal:
            user_can_update = [
                "draft"
            ]
            user_cannot_update = [
                "client_draft",
                "client_submission",
                "submitted",
                "rejected",
                "approved",
            ]
            
            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (
                    update_request_status == "submitted"
                    and "submitted" in user_cannot_update
                ):
                    user_cannot_update.remove("submitted")

        # for ae(Doesn't have permissions to edit)
        if user_role.lower() == Permissions.ae:
            user_can_update = ["client_submission", "submitted"]
            user_cannot_update = [
                "client_draft",
                "draft",
                "rejected",
                "approved",
            ]

            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (
                    update_request_status == "rejected"
                    and "rejected" in user_cannot_update
                ):
                    user_cannot_update.remove("rejected")
                if (
                    update_request_status == "approved"
                    and "approved" in user_cannot_update
                ):
                    user_cannot_update.remove("approved")

        # for bo(Doesn't have permissions to update any status)
        if user_role.lower() == Permissions.bo:
            user_can_update = []
            user_cannot_update = [
                "client_draft",
                "client_submission",
                "draft",
                "submitted",
                "rejected",
                "approved",
            ]
            if (
                update_request_status
                and update_request_status not in user_cannot_update
            ):
                user_cannot_update.append(update_request_status)

        request_type_string = f"CL - {request.id}"

        add_msg = ""
        if update_request_status is not None:
            add_msg = f"to {update_request_status}"
        
        # if request status is in list(user cannot update)
        if request.status.value in user_cannot_update and not update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value}",
            }
        # if request status is in list(user can update) and have to update status is in list(user cannot update)
        elif (
            request.status.value in user_can_update
            and update_request_status
            and update_request_status in user_cannot_update
        ):
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        # if request status is not in list(user can update) and have to update status
        elif request.status.value not in user_can_update and update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        else:
            # user can update request
            resp_result = {
                "status_code": 200,
                "status": "success",
                "msg": f"{user_role} has permission for updating {request_type_string} having status {request.status.value} {add_msg}",
            }

        return resp_result

    def can_update_generic_request(
        request=None, update_request_status=None, user_role=None
    ):
        """[check user can update generic request]

        Args:
            request ([type], optional): [description]. Defaults to None.
            update_request_status ([type], optional): [description]. Defaults to None.
            user_role ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code,
            "status": error/success,
            "msg": msg
        """
        if not request:
            # no request
            return {"status_code": 404, "status": "error", "msg": f"Request not found."}

        user_can_update = []
        user_cannot_update = []
        if not user_role:
            get_user_role_permissions = Permissions.get_user_role_permissions()

            # get_user_role_permissions status != 200
            if get_user_role_permissions["status_code"] != 200:
                return {
                    "status_code": get_user_role_permissions["status_code"],
                    "status": "error",
                    "msg": f"{get_user_role_permissions['msg']}",
                }

            # user role
            user_role = get_user_role_permissions["user_role"]

        if not user_role:
            return {
                "status_code": 404,
                "status": "error",
                "msg": f"app_flow: {user_role} - User role not selected, must be {Permissions.principal}/{Permissions.ae}",
            }

        # for principal
        if user_role.lower() == Permissions.principal:
            user_can_update = [
                "draft"
            ]
            user_cannot_update = [
                "submitted",
                "rejected",
                "approved",
            ]
            
            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (
                    update_request_status == "submitted"
                    and "submitted" in user_cannot_update
                ):
                    user_cannot_update.remove("submitted")

        # for ae(Doesn't have permissions to edit)
        if user_role.lower() == Permissions.ae:
            user_can_update = ["submitted"]
            user_cannot_update = [
                "draft",
                "rejected",
                "approved",
            ]

            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (request.status.value == "submitted") and (
                    "submitted" not in user_cannot_update
                    or update_request_status == "submitted"
                ):
                    user_cannot_update.append("submitted")

                if (
                    update_request_status == "rejected"
                    and "rejected" in user_cannot_update
                ):
                    user_cannot_update.remove("rejected")

                if (
                    update_request_status == "approved"
                    and "approved" in user_cannot_update
                ):
                    user_cannot_update.remove("approved")

        # for bo(Doesn't have permissions to update any status)
        if user_role.lower() == Permissions.bo:
            user_can_update = []
            user_cannot_update = [
                "draft",
                "submitted",
                "rejected",
                "approved",
            ]
            if (
                update_request_status
                and update_request_status not in user_cannot_update
            ):
                user_cannot_update.append(update_request_status)

        request_type_string = f"GN - {request.id}"

        add_msg = ""
        if update_request_status is not None:
            add_msg = f"to {update_request_status}"
        
        # if request status is in list(user cannot update)
        if request.status.value in user_cannot_update and not update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value}",
            }
        # if request status is in list(user can update) and have to update status is in list(user cannot update)
        elif (
            request.status.value in user_can_update
            and update_request_status
            and update_request_status in user_cannot_update
        ):
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        # if request status is not in list(user can update) and have to update status
        elif request.status.value not in user_can_update and update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        else:
            # user can update request
            resp_result = {
                "status_code": 200,
                "status": "success",
                "msg": f"{user_role} has permission for updating {request_type_string} having status {request.status.value} {add_msg}",
            }

        return resp_result

    def can_update_compliance_repository(
        request=None, update_request_status=None, user_role=None
    ):
        """[check user can update compliance repository]

        Args:
            request ([type], optional): [description]. Defaults to None.
            update_request_status ([type], optional): [description]. Defaults to None.
            user_role ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code,
            "status": error/success,
            "msg": msg
        """
        if not request:
            # no request
            return {"status_code": 404, "status": "error", "msg": f"Request not found."}

        user_can_update = []
        user_cannot_update = []
        if not user_role:
            get_user_role_permissions = Permissions.get_user_role_permissions()

            # get_user_role_permissions status != 200
            if get_user_role_permissions["status_code"] != 200:
                return {
                    "status_code": get_user_role_permissions["status_code"],
                    "status": "error",
                    "msg": f"{get_user_role_permissions['msg']}",
                }

            # user role
            user_role = get_user_role_permissions["user_role"]

        if not user_role:
            return {
                "status_code": 404,
                "status": "error",
                "msg": f"app_flow: {user_role} - User role not selected, must be {Permissions.principal}",
            }

        # for principal
        if user_role.lower() == Permissions.principal:
            user_can_update = [
                "draft",
                "client_submission",
                "submitted"
            ]
            user_cannot_update = [
                "client_draft",
                "principal_rejection",
                "submitted",
                "approved",
            ]
            
            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if request.status.value == update_request_status:
                    user_cannot_update.append(update_request_status)
                    
                if (
                    request.status.value == "client_submission"
                ) and (
                    "draft" not in user_cannot_update
                    or update_request_status == "draft"
                ):
                    user_cannot_update.append("draft")

                if (
                    request.status.value == "client_submission"
                ) and (
                    update_request_status == "principal_rejection"
                    and "principal_rejection" in user_cannot_update
                ):
                    user_cannot_update.remove("principal_rejection")

                if (
                    update_request_status == "approved"
                    and "approved" in user_cannot_update
                ):
                    user_cannot_update.remove("approved")

                if (
                    request.status.value == "draft"
                ) and (
                    update_request_status == "client_submission"
                    or "client_submission" not in user_cannot_update
                ):
                    user_cannot_update.append("client_submission")

                if (
                    request.status.value == "draft"
                ) and (
                    update_request_status == "submitted"
                    and "submitted" in user_cannot_update
                ):
                    user_cannot_update.remove("submitted")

        # LC-2084: for ae/bo(Doesn't have permissions to create/update)
        if user_role.lower() in [Permissions.ae, Permissions.bo]:
            user_can_update = []
            user_cannot_update = [
                "draft",
                "client_draft",
                "client_submission",
                "principal_rejection",
                "submitted",
                "approved",
            ]

            if (
                update_request_status
                and update_request_status not in user_cannot_update
            ):
                user_cannot_update.append(update_request_status)

        request_type_string = f"CR - {request.id}"

        add_msg = ""
        if update_request_status is not None:
            add_msg = f"to {update_request_status}"
        
        # if request status is in list(user cannot update)
        if request.status.value in user_cannot_update and not update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value}",
            }
        # if request status is in list(user can update) and have to update status is in list(user cannot update)
        elif (
            request.status.value in user_can_update
            and update_request_status
            and update_request_status in user_cannot_update
        ):
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        # if request status is not in list(user can update) and have to update status
        elif request.status.value not in user_can_update and update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        else:
            # user can update request
            resp_result = {
                "status_code": 200,
                "status": "success",
                "msg": f"{user_role} has permission for updating {request_type_string} having status {request.status.value} {add_msg}",
            }

        return resp_result


    def can_update_collection_notes(
        request=None, update_request_status=None, user_role=None
    ):
        """[check user can update collection_notes]

        Args:
            request ([type], optional): [description]. Defaults to None.
            update_request_status ([type], optional): [description]. Defaults to None.
            user_role ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code,
            "status": error/success,
            "msg": msg
        """
        if not request:
            # no request
            return {"status_code": 404, "status": "error", "msg": f"Request not found."}

        user_can_update = []
        user_cannot_update = []
        if not user_role:
            get_user_role_permissions = Permissions.get_user_role_permissions()

            # get_user_role_permissions status != 200
            if get_user_role_permissions["status_code"] != 200:
                return {
                    "status_code": get_user_role_permissions["status_code"],
                    "status": "error",
                    "msg": f"{get_user_role_permissions['msg']}",
                }

            # user role
            user_role = get_user_role_permissions["user_role"]

        if not user_role:
            return {
                "status_code": 404,
                "status": "error",
                "msg": f"app_flow: {user_role} - User role not selected, must be {Permissions.principal}",
            }

        # for principal
        if user_role.lower() == Permissions.principal:
            user_can_update = [
                "draft",
                "client_submission",
            ]
            user_cannot_update = [
                "client_draft",
                "client_submission",
                "submitted",
            ]
            
            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (
                    request.status.value == "client_submission"
                ) and (
                    "draft" not in user_cannot_update
                    or update_request_status == "draft"
                ):
                    user_cannot_update.append("draft")

                if (
                    request.status.value == "draft"
                ) and (
                    update_request_status == "submitted"
                    and "submitted" in user_cannot_update
                ):
                    user_cannot_update.remove("submitted")

        # for ae/bo(Doesn't have permissions to edit)
        if user_role.lower() in [Permissions.ae, Permissions.bo]:
            user_can_update = []
            user_cannot_update = [
                "draft",
                "client_draft",
                "client_submission",
                "submitted",
            ]

            if (
                update_request_status
                and update_request_status not in user_cannot_update
            ):
                user_cannot_update.append(update_request_status)

        request_type_string = f"CN - {request.id}"

        add_msg = ""
        if update_request_status is not None:
            add_msg = f"to {update_request_status}"
        
        # if request status is in list(user cannot update)
        if request.status.value in user_cannot_update and not update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value}",
            }
        # if request status is in list(user can update) and have to update status is in list(user cannot update)
        elif (
            request.status.value in user_can_update
            and update_request_status
            and update_request_status in user_cannot_update
        ):
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        # if request status is not in list(user can update) and have to update status
        elif request.status.value not in user_can_update and update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        else:
            # user can update request
            resp_result = {
                "status_code": 200,
                "status": "success",
                "msg": f"{user_role} has permission for updating {request_type_string} having status {request.status.value} {add_msg}",
            }

        return resp_result

    
    def can_update_verification_notes(
        request=None, update_request_status=None, user_role=None
    ):
        """[check user can update verification_notes]

        Args:
            request ([type], optional): [description]. Defaults to None.
            update_request_status ([type], optional): [description]. Defaults to None.
            user_role ([type], optional): [description]. Defaults to None.

        Returns:
            "status_code": status code,
            "status": error/success,
            "msg": msg
        """
        if not request:
            # no request
            return {"status_code": 404, "status": "error", "msg": f"Request not found."}

        user_can_update = []
        user_cannot_update = []
        if not user_role:
            get_user_role_permissions = Permissions.get_user_role_permissions()

            # get_user_role_permissions status != 200
            if get_user_role_permissions["status_code"] != 200:
                return {
                    "status_code": get_user_role_permissions["status_code"],
                    "status": "error",
                    "msg": f"{get_user_role_permissions['msg']}",
                }

            # user role
            user_role = get_user_role_permissions["user_role"]

        if not user_role:
            return {
                "status_code": 404,
                "status": "error",
                "msg": f"app_flow: {user_role} - User role not selected, must be {Permissions.principal}",
            }

        # for principal
        if user_role.lower() == Permissions.principal:
            user_can_update = [
                "draft",
                "client_submission",
            ]
            user_cannot_update = [
                "client_draft",
                "client_submission",
                "submitted",
            ]
            
            # remove element from user_cannot_update
            if update_request_status and request.status.value in user_can_update:
                if (
                    request.status.value == "client_submission"
                ) and (
                    "draft" not in user_cannot_update
                    or update_request_status == "draft"
                ):
                    user_cannot_update.append("draft")

                if (
                    request.status.value == "draft"
                ) and (
                    update_request_status == "submitted"
                    and "submitted" in user_cannot_update
                ):
                    user_cannot_update.remove("submitted")

        # for ae/bo(Doesn't have permissions to edit)
        if user_role.lower() in [Permissions.ae, Permissions.bo]:
            user_can_update = []
            user_cannot_update = [
                "draft",
                "client_draft",
                "client_submission",
                "submitted",
            ]

            if (
                update_request_status
                and update_request_status not in user_cannot_update
            ):
                user_cannot_update.append(update_request_status)

        request_type_string = f"VN - {request.id}"

        add_msg = ""
        if update_request_status is not None:
            add_msg = f"to {update_request_status}"
        
        # if request status is in list(user cannot update)
        if request.status.value in user_cannot_update and not update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value}",
            }
        # if request status is in list(user can update) and have to update status is in list(user cannot update)
        elif (
            request.status.value in user_can_update
            and update_request_status
            and update_request_status in user_cannot_update
        ):
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        # if request status is not in list(user can update) and have to update status
        elif request.status.value not in user_can_update and update_request_status:
            resp_result = {
                "status_code": 403,
                "status": "error",
                "msg": f"{user_role} doesn't has permission for updating {request_type_string} having status {request.status.value} to {update_request_status}",
            }
        else:
            # user can update request
            resp_result = {
                "status_code": 200,
                "status": "success",
                "msg": f"{user_role} has permission for updating {request_type_string} having status {request.status.value} {add_msg}",
            }

        return resp_result
