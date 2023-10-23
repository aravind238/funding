import os
from flask import request
from src.models import *
from datetime import date, datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response, SendMails
from src.resources.v2.schemas import *
from src.middleware.permissions import Permissions
from src.resources.v2.helpers.convert_datetime import utc_to_local

debtor_limit_approvals_schema = DebtorLimitApprovalsSchema()
debtor_limit_approvals_ref_schema = DebtorLimitApprovalsRefSchema() # for previous_credit_limit display
comments_schema = CommentsSchema()
supporting_documents_schema = SupportingDocumentsSchema()
reasons_schema = ReasonsSchema()


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def create():
    """
    Create DebtorLimitApprovals
    """
    req_data = request.get_json()

    if req_data.get("client_id") and req_data.get("debtor_id"):
        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        # added validation for not creating credit limit with inactive clients LC-2188
        client = Client.get_one_based_off_control_accounts(req_data["client_id"])
        if not client:
            return custom_response({"status": "error", "msg": "Client not found"}, 404)
        if client.is_active == False:
            return custom_response({"status": "error", "msg": "Client is Inactive"}, 404)

        # added validation for not creating credit limit with inactive debtors LC-2187
        debtor = Debtor.get_one_based_off_control_accounts(req_data["debtor_id"])
        if not debtor:
            return custom_response({"status": "error", "msg": "Debtor not found"}, 404)
        if debtor.is_active == False:
            return custom_response({"status": "error", "msg": "Debtor is Inactive"}, 404)
        
        client_debtor = ClientDebtor.query.filter(
            ClientDebtor.is_deleted == False,
            ClientDebtor.client_id == req_data.get("client_id"),
            ClientDebtor.debtor_id == req_data.get("debtor_id"),
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            ControlAccount.name.in_(business_control_accounts),
        ).first()
        if not client_debtor:
            return custom_response(
                {"status": "error", "msg": "client_debtor not found"}, 404
            )

    data, error = debtor_limit_approvals_schema.load(req_data)
    if error:
        return custom_response(error, 400)

    data["status"] = "draft"
    data["last_processed_at"] = datetime.utcnow()

    debtor_limit_approvals = DebtorLimitApprovals(data)
    debtor_limit_approvals.save()

    schema_data = debtor_limit_approvals_schema.dump(debtor_limit_approvals).data

    # get logged user email
    user_email = Permissions.get_user_details()["email"]

    dlah_data = schema_data.copy()
    dlah_data["previous_credit_limit"] = (
        float(client_debtor.credit_limit) if client_debtor else float(0)
    )

    # save debtor limit approvals history
    approvals_history_data = {
        "key": "created_at",
        "value": datetime.utcnow(),
        "user": user_email,
        "attribute": dlah_data,
        "debtor_limit_approvals_id": debtor_limit_approvals.id,
    }
    approvals_history = DebtorLimitApprovalsHistory(approvals_history_data)
    approvals_history.save()

    return custom_response(schema_data, 201)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def get_all():
    """
    Get All DebtorLimitApprovals
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
        data = DebtorLimitApprovalsListing.get_paginated(
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
        data = DebtorLimitApprovalsListing.get_all()

    if not data:
        data = []

    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def get_one(id):
    """
    Get A DebtorLimitApprovals
    """
    debtor_limit_approvals = DebtorLimitApprovals.get_one_based_off_control_accounts(id)
    if not debtor_limit_approvals:
        return custom_response(
            {"status": "error", "msg": "debtor_limit_approvals not found"}, 404
        )

    data = debtor_limit_approvals_ref_schema.dump(debtor_limit_approvals).data
    data["client_name"] = debtor_limit_approvals.client.name
    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def update(id):
    """
    Update A DebtorLimitApprovals
    """
    req_data = request.get_json()
    update_request_status = req_data.get("status", None)
    approvals_history_data = {}

    debtor_limit_approvals = DebtorLimitApprovals.get_one_based_off_control_accounts(id, active_client=True)
    if not debtor_limit_approvals:
        return custom_response(
            {"status": "error", "msg": "debtor_limit_approvals not found"}, 404
        )

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
    validated_request_status = Permissions.can_update_debtor_limits(
        request=debtor_limit_approvals,
        update_request_status=update_request_status,
        user_role=user_role,
    )
    print("debtor_limit_approvals", validated_request_status)
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
        data, error = DebtorLimitApprovalsSchema(
            exclude=["client_id", "debtor_id", "last_processed_at"]
        ).load(req_data, partial=True)
        if error:
            return custom_response(error, 400)

        # checking, when ae approves request if credit_limit_approved == 0
        if update_request_status == "approved" and (
            (
                float(debtor_limit_approvals.credit_limit_approved) <= float(0)
                and "credit_limit_approved" not in data
            )
            or (
                "credit_limit_approved" in data
                and float(data["credit_limit_approved"]) <= float(0)
            )
        ):
            return custom_response(
                {
                    "status": "error",
                    "msg": f"credit_limit_approved must be greater than 0",
                },
                400,
            )

        # on status update, update last_processed_at
        if update_request_status:
            data["last_processed_at"] = datetime.utcnow()

            # user email
            user_email = Permissions.get_user_details()["email"]

            # approved/rejected
            approvals_history_key = f'{req_data["status"]}_at'

            approvals_history_data = {
                "user": user_email,
                "key": approvals_history_key,
                "value": datetime.utcnow(),
                "debtor_limit_approvals_id": debtor_limit_approvals.id,
            }
        debtor_limit_approvals.update(data)

    schema_data = debtor_limit_approvals_schema.dump(debtor_limit_approvals).data

    if approvals_history_data:        
        dlah_data = schema_data.copy()

        client_debtor = ClientDebtor.query.filter(
            ClientDebtor.is_deleted == False,
            ClientDebtor.client_id == debtor_limit_approvals.client_id,
            ClientDebtor.debtor_id == debtor_limit_approvals.debtor_id,
        ).first()

        dlah_data["previous_credit_limit"] = (
            float(client_debtor.credit_limit) if client_debtor else float(0)
        )
        
        approvals_history_data.update({"attribute": dlah_data})
        approvals_history = DebtorLimitApprovalsHistory(approvals_history_data)
        approvals_history.save()

    # on AE approving new credit limit, update credit limit in client_debtor table
    if (
        user_role.lower() == "ae"
        and "status" in req_data
        and req_data["status"] == "approved"
    ):
        debtor_limit_approvals.update_client_debtor_credit_limit()
    
    # debtor_limit_approvals notifications
    if update_request_status:
        request_type = debtor_limit_approvals
        
        # Get organization ids
        organization_client_account = OrganizationClientAccount.query.filter_by(
            lcra_client_account_id=debtor_limit_approvals.client.lcra_client_accounts_id
        ).first()

        organization_id = None
        if organization_client_account:
            organization_id = organization_client_account.organization_id

        # get client_id
        client_id = request_type.client_id

        # request submitted: send mail to AE
        if update_request_status == "submitted":
            # Mail to AE
            template_name = os.environ.get("REQUEST_SUBMITTED_TO_ACCOUNT_EXECUTIVE_MAIL")
            recipient_role_name = "AE"
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()
            
        # request approved: send mail to principal/client
        if update_request_status == "approved":
            recipient_role_name = None
            
            if request_type.request_created_by_client() or request_type.request_submitted_by_client():
                # Mail to Client
                recipient_role_name = "Client"

            if request_type.request_created_by_principal() or request_type.request_submitted_by_principal():
                # Mail to Principal
                recipient_role_name = "Principal"

            if recipient_role_name:
                template_name = os.environ.get("CREDIT_LIMIT_APPROVED_OR_REJECTED_BY_AE_MAIL")
                send_mails = SendMails(
                    request_type=request_type,
                    client_id=client_id,
                    recipient_role_name=recipient_role_name,
                    template_name=template_name,
                    organization_access=organization_id,
                )
                send_mails.send_mail_request_notifications()

    return custom_response(schema_data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def delete(id):
    """
    Delete A DebtorLimitApprovals
    """
    debtor_limit_approvals = DebtorLimitApprovals.get_one_based_off_control_accounts(id)
    if not debtor_limit_approvals:
        return custom_response(
            {"status": "error", "msg": "debtor_limit_approvals not found"}, 404
        )

    debtor_limit_approvals.deleted_at = datetime.utcnow()
    debtor_limit_approvals.save()

    return custom_response(
        {"status": "success", "msg": "debtor_limit_approvals deleted"}, 202
    )


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def get_approval_history(id):
    dla = DebtorLimitApprovals.get_one_based_off_control_accounts(id)
    if not dla:
        return custom_response(
            {"status": "error", "msg": "debtor_limit_approvals not found"}, 404
        )

    approvals_history = dla.dla_approvals_history()

    return custom_response(approvals_history, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def get_comments(id):
    dla = DebtorLimitApprovals.get_one_based_off_control_accounts(id)
    if not dla:
        return custom_response(
            {"status": "error", "msg": "debtor_limit_approvals not found"}, 404
        )

    comments = dla.dla_comments()
    if not comments:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    dla_comments = comments_schema.dump(comments, many=True).data

    return custom_response(dla_comments, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def get_supporting_documents(id):
    dla = DebtorLimitApprovals.get_one_based_off_control_accounts(id)
    if not dla:
        return custom_response(
            {"status": "error", "msg": "debtor_limit_approvals not found"}, 404
        )

    get_supporting_documents = dla.supporting_documents()
    if not get_supporting_documents:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    supporting_documents = supporting_documents_schema.dump(
        get_supporting_documents, many=True
    ).data

    return custom_response(supporting_documents, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.credit_limit)
def get_reasons(id):
    dla = DebtorLimitApprovals.get_one_based_off_control_accounts(id)
    if not dla:
        return custom_response(
            {"status": "error", "msg": "debtor_limit_approvals not found"}, 404
        )

    get_dla_reasons = dla.dla_reasons()
    if not get_dla_reasons:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    dla_reasons = []
    for dla_reason in get_dla_reasons:
        attribute = dla_reason.attribute

        each_reason = {
            "id": attribute["id"] if "id" in attribute else None,
            "user": dla_reason.user,
            "debtor_limit_approvals_id": dla_reason.debtor_limit_approvals_id,
            "notes": attribute["notes"] if "notes" in attribute else None,
            "status": attribute["status"] if "status" in attribute else None,
            "created_at": utc_to_local(dt=dla_reason.created_at.isoformat()),
            "updated_at": utc_to_local(dt=dla_reason.updated_at.isoformat()),
        }
        dla_reasons.append(each_reason)

    return custom_response(dla_reasons, 200)
