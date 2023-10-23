import os
from flask import request
from src.models import *
from datetime import date, datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response, SendMails
from src.resources.v2.schemas import *
from src.middleware.permissions import Permissions
from src.resources.v2.helpers.convert_datetime import utc_to_local

generic_request_schema = GenericRequestSchema()
generic_request_ref_schema = GenericRequestRefSchema()
comments_schema = CommentsSchema()
supporting_documents_schema = SupportingDocumentsSchema()
reasons_schema = ReasonsSchema()


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def create():
    """
    Create GenericRequest
    """
    req_data = request.get_json()

    # update for now, this needs to be change later
    if "client_id" not in req_data:
        return custom_response(
            {"status": "error", "msg": "client_id is required"}, 404
        )
    
    client = Client.get_one_based_off_control_accounts(req_data["client_id"])
    if not client:
        return custom_response({"status": "error", "msg": "client not found"}, 404)
    if client.is_active == False:
            return custom_response({"status": "error", "msg": "Client is Inactive"}, 404)
    
    data, error = generic_request_schema.load(req_data)
    if error:
        return custom_response(error, 400)
    
    data["status"] = "draft"
    data["last_processed_at"] = datetime.utcnow()
    
    generic_request = GenericRequest(data)
    generic_request.save()

    user_email = Permissions.get_user_details()["email"]

    data = generic_request_schema.dump(generic_request).data

    approvals_history_data = {
        "key": "created_at",
        "value": datetime.utcnow(),
        "user": user_email,
        "attribute": data,
        "generic_request_id": generic_request.id,
    }
    approvals_history = GenericRequestApprovalsHistory(approvals_history_data)
    approvals_history.save()

    return custom_response(data, 201)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def get_all():
    """
    Get All GenericRequest
    """
    page = request.args.get("page", 0, type=int)
    rpp = request.args.get("rpp", 20, type=int)
    search = request.args.get("search", None, type=str)
    ordering = request.args.get("ordering", None, type=str)
    start_date = request.args.get("start_date", None, type=str)
    end_date = request.args.get("end_date", None, type=str)
    stage = request.args.get("stage", None, type=str)
    control_account = request.args.get("control_account", None, type=str)
    
    if start_date is not None:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")

    if end_date is not None:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    if start_date and end_date and start_date > end_date:
        return custom_response(
            {"status": "error", "msg": "end_date must be greater than start_date."},
            400,
        )

    if page > 0:
        data = GenericRequestListing.get_paginated(
            page=page,
            rpp=rpp,
            search=search,
            start_date=start_date,
            end_date=end_date,
            ordering=ordering,
            stage=stage,
            control_account=control_account,
        )
    else:
        data = GenericRequestListing.get_all()

    if data is None:
        data = []

    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def get_one(id):
    """
    Get A GenericRequest
    """
    generic_request = GenericRequest.get_one_based_off_control_accounts(id)
    if not generic_request:
        return custom_response({"status": "error", "msg": "generic_request not found"}, 404)
    data = generic_request_ref_schema.dump(generic_request).data
    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def update(id):
    """
    Update A GenericRequest
    """
    req_data = request.get_json()    
    update_request_status = req_data.get("status", None)
    approvals_history_data = {}

    generic_request = GenericRequest.get_one_based_off_control_accounts(id, active_client=True)
    if not generic_request:
        return custom_response({"status": "error", "msg": "generic_request not found"}, 404)

    # update_request_status = None: if generic_request.status.value == update_request_status
    if (
        update_request_status
        and generic_request.status.value == update_request_status
    ):
        update_request_status = None

    # user role
    get_user_role = Permissions.get_user_role_permissions()
    user_role = get_user_role["user_role"]

    # user role not assigned to user
    if not user_role:
        return custom_response(
            {"status": "error", "msg": f"user role not found, please assign role"}, 403
        )

    # checking, for bo which don't have permission to edit
    if user_role.lower() in ["bo"]:
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to edit",
            },
            403,
        )

    # check, if request can be updated
    validated_request_status = Permissions.can_update_generic_request(
        request=generic_request,
        update_request_status=update_request_status,
        user_role=user_role,
    )
    print("generic_request", validated_request_status)
    if validated_request_status and validated_request_status["status_code"] in [
        401,
        403,
    ]:
        return custom_response(
            {
                "status": validated_request_status["status"],
                "msg": validated_request_status["msg"],
            },
            validated_request_status["status_code"],
        )

    if req_data:
        data, error = GenericRequestSchema(
            exclude=["client_id", "last_processed_at"]
        ).load(req_data, partial=True)
        if error:
            return custom_response(error, 400)

        # on status update, update last_processed_at
        if update_request_status:
            data["last_processed_at"] = datetime.utcnow()

            # user email
            user_email = Permissions.get_user_details()["email"]

            # submitted/approved
            approvals_history_key = f'{req_data["status"]}_at'

            approvals_history_data = {
                "user": user_email,
                "key": approvals_history_key,
                "value": datetime.utcnow(),
                "generic_request_id": id,
            }

        generic_request.update(data)

    data = generic_request_schema.dump(generic_request).data

    if approvals_history_data:
        approvals_history_data.update({"attribute": data})
        approvals_history = GenericRequestApprovalsHistory(approvals_history_data)
        approvals_history.save()

    # generic request notifications
    if update_request_status:
        request_type = generic_request
        
        # Get organization ids
        organization_client_account = OrganizationClientAccount.query.filter_by(
            lcra_client_account_id=generic_request.client.lcra_client_accounts_id
        ).first()

        organization_id = None
        if organization_client_account:
            organization_id = organization_client_account.organization_id

        # category
        category = request_type.category.value

        # get client_id
        client_id = request_type.client_id

        # request submitted: send mail to AE
        if update_request_status == "submitted":
            # Mail to AE
            template_name = os.environ.get("REQUEST_SUBMITTED_TO_ACCOUNT_EXECUTIVE_MAIL")
            recipient_role_name = "AE"
            send_mails = SendMails(
                category=category,
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()
            
        # request approved: send mail to principal
        if update_request_status == "approved":
            # Mail to Principal
            template_name = os.environ.get("CREDIT_LIMIT_APPROVED_OR_REJECTED_BY_AE_MAIL")
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name="Principal",
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()

    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def delete(id):
    """
    Delete A GenericRequest
    """
    generic_request = GenericRequest.get_one_based_off_control_accounts(id)
    if not generic_request:
        return custom_response(
            {"status": "error", "msg": "generic_request not found"}, 404
        )

    generic_request.deleted_at = datetime.utcnow()
    generic_request.save()

    return custom_response(
        {"status": "success", "msg": "generic_request deleted"}, 202
    )


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def get_approval_history(id):
    generic_request = GenericRequest.get_one_based_off_control_accounts(id)
    if not generic_request:
        return custom_response(
            {"status": "error", "msg": "generic_request not found"}, 404
        )

    generic_request_approvals_history = generic_request.gn_approvals_history()
    return custom_response(generic_request_approvals_history, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def get_comments(id):
    generic_request = GenericRequest.get_one_based_off_control_accounts(id)
    if not generic_request:
        return custom_response(
            {"status": "error", "msg": "generic_request not found"}, 404
        )

    generic_request_comments = generic_request.comments()
    if not generic_request_comments:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    comments = comments_schema.dump(generic_request_comments, many=True).data
    return custom_response(comments, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def get_supporting_documents(id):
    generic_request = GenericRequest.get_one_based_off_control_accounts(id)
    if not generic_request:
        return custom_response(
            {"status": "error", "msg": "generic_request not found"}, 404
        )

    get_supporting_documents = generic_request.supporting_documents()
    if not get_supporting_documents:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    supporting_documents = supporting_documents_schema.dump(
        get_supporting_documents, many=True
    ).data

    return custom_response(supporting_documents, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.generic_request)
def get_reasons(id):
    generic_request = GenericRequest.get_one_based_off_control_accounts(id)
    if not generic_request:
        return custom_response(
            {"status": "error", "msg": "generic_request not found"}, 404
        )

    get_generic_request_reasons = generic_request.reasons()
    if not get_generic_request_reasons:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    generic_request_reasons = []
    for generic_request_reason in get_generic_request_reasons:
        attribute = generic_request_reason.attribute

        each_reason = {
            "id": attribute["id"] if "id" in attribute else None,
            "user": generic_request_reason.user,
            "generic_request_id": generic_request_reason.generic_request_id,
            "notes": attribute["notes"] if "notes" in attribute else None,
            "status": attribute["status"] if "status" in attribute else None,
            "created_at": utc_to_local(dt=generic_request_reason.created_at.isoformat()),
            "updated_at": utc_to_local(dt=generic_request_reason.updated_at.isoformat()),
        }
        generic_request_reasons.append(each_reason)

    return custom_response(generic_request_reasons, 200)
