from flask import request
from src.models import *
from datetime import date, datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import *
from src.middleware.permissions import Permissions
from src.resources.v2.models.verification_notes_model import verification_type_or_method_list

verification_notes_schema = VerificationNotesSchema()
verification_notes_ref_schema = VerificationNotesRefSchema()


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def create():
    """
    Create a Verification Note
    """
    req_data = request.get_json()

    if req_data.get("client_id") and req_data.get("debtor_id"):
        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        client = Client.get_one_based_off_control_accounts(req_data["client_id"])
        if not client:
            return custom_response({"status": "error", "msg": "Client not found"}, 404)
        if client.is_active == False:
            return custom_response({"status": "error", "msg": "Client is Inactive"}, 404)
        
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

    # check invoice
    if "invoice_id" not in req_data:
        return custom_response(
            {"status": "error", "msg": "invoice_id is required"}, 400
        )

    invoice  = Invoice.get_one_based_off_control_accounts(req_data.get("invoice_id"))
    if not invoice:
        return custom_response(
            {"status": "error", "msg": "Invoice not found"}, 404
        )

    # check soa
    if "soa_id" not in req_data:
        return custom_response(
            {"status": "error", "msg": "soa_id is required"}, 400
        )
    
    soa = SOA.get_one_based_off_control_accounts(req_data.get("soa_id"))
    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404) 

    if "verification_type_or_method" in req_data and req_data["verification_type_or_method"] is not None:
        if req_data["verification_type_or_method"] not in verification_type_or_method_list:
            return custom_response(
                {"status": "error", "msg": "Invalid Verification Type/Method Value"}, 400
            )

    data, error = verification_notes_schema.load(req_data)
    if error:
        return custom_response(error, 400)

    data["status"] = "draft"
    data["last_processed_at"] = datetime.utcnow()

    verification_notes = VerificationNotes(data)
    verification_notes.save()

    data = verification_notes_schema.dump(verification_notes).data

    data["request_type"] = Permissions.verification_notes

    # get logged user email
    user_email = Permissions.get_user_details()["email"]

    # save verification_notes approvals history
    approvals_history_data = {
        "key": "created_at",
        "value": datetime.utcnow(),
        "user": user_email,
        "attribute": data,
        "verification_notes_id": verification_notes.id,
    }
    approvals_history = VerificationNotesApprovalHistory(approvals_history_data)
    approvals_history.save()

    return custom_response(data, 201)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def get_all():
    """
    Get All Verification Notes
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
        data = VerificationNotesListing.get_paginated(
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
        data = VerificationNotesListing.get_all()

    if not data:
        data = []

    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def get_one(id):
    """
    Get A Verification Note
    """
    verification_notes = VerificationNotes.get_one_based_off_control_accounts(id)
    if not verification_notes:
        return custom_response(
            {"status": "error", "msg": "verification_notes not found"}, 404
        )

    data = verification_notes_ref_schema.dump(verification_notes).data
    data["client_name"] = verification_notes.client.name
    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def update(id):
    """
    Update A Verification Note
    """
    req_data = request.get_json()
    update_request_status = req_data.get("status", None)
    approvals_history_data = {}

    verification_notes = VerificationNotes.get_one_based_off_control_accounts(id)
    if not verification_notes:
        return custom_response(
            {"status": "error", "msg": "verification_notes not found"}, 404
        )

    # user role
    get_user_role = Permissions.get_user_role_permissions()
    user_role = get_user_role["user_role"]

    # user role not assigned to user
    if not user_role:
        return custom_response(
            {"status": "error", "msg": f"user role not found, please assign role"}, 403
        )

    # only update if soa status is draft
    if verification_notes.soa.status.value != "draft":
        return custom_response(
            {
                "status": "error",
                "msg": f"request can't be updated",
            },
            403,
        )

    # checking, for ae,bo which don't have permission to edit
    if user_role.lower() in ["ae", "bo"]:
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to edit",
            },
            403,
        )

    if "verification_type_or_method" in req_data and req_data["verification_type_or_method"] is not None:
        if req_data["verification_type_or_method"] not in verification_type_or_method_list:
            return custom_response(
                {"status": "error", "msg": "Invalid Verification Type/Method Value"}, 404
            )


    # check, if request can be updated
    validated_request_status = Permissions.can_update_verification_notes(
        request=verification_notes,
        update_request_status=update_request_status,
        user_role=user_role,
    )
    print("verification_notes", validated_request_status)
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
        data, error = VerificationNotesSchema(
            exclude=["client_id", "debtor_id", "last_processed_at"]
        ).load(req_data, partial=True)
        if error:
            return custom_response(error, 400)

        # on status update, update last_processed_at
        if update_request_status:
            data["last_processed_at"] = datetime.utcnow()

            # user email
            user_email = Permissions.get_user_details()["email"]

            # submitted
            approvals_history_key = f'{req_data["status"]}_at'

            approvals_history_data = {
                "user": user_email,
                "key": approvals_history_key,
                "value": datetime.utcnow(),
                "verification_notes_id": verification_notes.id,
            }
        verification_notes.update(data)

    data = verification_notes_schema.dump(verification_notes).data

    if approvals_history_data:        
        approvals_history_data.update({"attribute": data})
        approvals_history = VerificationNotesApprovalHistory(approvals_history_data)
        approvals_history.save()

    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def delete(id):
    """
    Delete A Verification Note
    """
    verification_notes = VerificationNotes.get_one_based_off_control_accounts(id)
    if not verification_notes:
        return custom_response(
            {"status": "error", "msg": "verification_notes not found"}, 404
        )

    verification_notes.deleted_at = datetime.utcnow()
    verification_notes.save()

    return custom_response(
        {"status": "success", "msg": "verification_notes deleted"}, 202
    )


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def get_approval_history(id):
    verification_notes = VerificationNotes.get_one_based_off_control_accounts(id)
    if not verification_notes:
        return custom_response(
            {"status": "error", "msg": "verification_notes not found"}, 404
        )

    verification_notes_approvals_history = verification_notes.vn_approvals_history()

    return custom_response(verification_notes_approvals_history, 200)
