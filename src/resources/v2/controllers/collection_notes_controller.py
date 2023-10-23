from flask import request
from src.models import *
from datetime import date, datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import *
from src.middleware.permissions import Permissions
from src.resources.v2.models.collection_notes_model import CollectionStatus, CollectionNotesContactMethod

collection_notes_schema = CollectionNotesSchema()
collection_notes_ref_schema = CollectionNotesRefSchema()


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def create():
    """
    Create a Collection Note
    """
    req_data = request.get_json()

    if req_data.get("client_id") and req_data.get("debtor_id"):
        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        # added validation for not creating collection notes with inactive clients LC-2188
        client = Client.get_one_based_off_control_accounts(req_data["client_id"])
        if not client:
            return custom_response({"status": "error", "msg": "Client not found"}, 404)
        if client.is_active == False:
            return custom_response({"status": "error", "msg": "Client is Inactive"}, 404)

        # added validation for not creating collection notes with inactive debtors LC-2187
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

    if req_data.get("invoice_id"):
        invoice  = Invoice.get_one_based_off_control_accounts(req_data.get("invoice_id"))
        if not invoice:
            return custom_response(
                {"status": "error", "msg": "Invoice not found"}, 404
            )

    if "collection_status" in req_data and req_data["collection_status"] is not None:
        if req_data["collection_status"] not in CollectionStatus:
            return custom_response(
                {"status": "error", "msg": "Invalid collection_status Value"}, 404
            )

    if "contact_method" in req_data and req_data["contact_method"] is not None:
        if req_data["contact_method"] not in CollectionNotesContactMethod:
            return custom_response(
                {"status": "error", "msg": "Invalid contact_method Value"}, 404
            )

    data, error = collection_notes_schema.load(req_data)
    if error:
        return custom_response(error, 400)

    data["status"] = "draft"
    data["last_processed_at"] = datetime.utcnow()

    collection_notes = CollectionNotes(data)
    collection_notes.save()

    data = collection_notes_schema.dump(collection_notes).data

    data["request_type"] = Permissions.collection_notes

    # get logged user email
    user_email = Permissions.get_user_details()["email"]

    # save collection_notes approvals history
    approvals_history_data = {
        "key": "created_at",
        "value": datetime.utcnow(),
        "user": user_email,
        "attribute": data,
        "collection_notes_id": collection_notes.id,
    }
    approvals_history = CollectionNotesApprovalHistory(approvals_history_data)
    approvals_history.save()

    return custom_response(data, 201)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def get_all():
    """
    Get All Collection Notes
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
        data = CollectionNotesListing.get_paginated(
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
        data = CollectionNotesListing.get_all()

    if not data:
        data = []

    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def get_one(id):
    """
    Get A Collection Note
    """
    collection_notes = CollectionNotes.get_one_based_off_control_accounts(id)
    if not collection_notes:
        return custom_response(
            {"status": "error", "msg": "collection_notes not found"}, 404
        )

    data = collection_notes_ref_schema.dump(collection_notes).data
    data["client_name"] = collection_notes.client.name
    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def update(id):
    """
    Update A Collection Note
    """
    req_data = request.get_json()
    update_request_status = req_data.get("status", None)
    approvals_history_data = {}

    collection_notes = CollectionNotes.get_one_based_off_control_accounts(id, active_client=True)
    if not collection_notes:
        return custom_response(
            {"status": "error", "msg": "collection_notes not found"}, 404
        )

    # checking, only update status to "submitted"
    if update_request_status and update_request_status not in ["submitted"]:
        del req_data["status"]
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
    if user_role.lower() in ["ae", "bo"]:
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to edit",
            },
            403,
        )

    if "collection_status" in req_data and req_data["collection_status"] is not None:
        if req_data["collection_status"] not in CollectionStatus:
            return custom_response(
                {"status": "error", "msg": "Invalid collection_status Value"}, 404
            )

    if "contact_method" in req_data and req_data["contact_method"] is not None:
        if req_data["contact_method"] not in CollectionNotesContactMethod:
            return custom_response(
                {"status": "error", "msg": "Invalid contact_method Value"}, 404
            )


    # check, if request can be updated
    validated_request_status = Permissions.can_update_collection_notes(
        request=collection_notes,
        update_request_status=update_request_status,
        user_role=user_role,
    )
    print("collection_notes", validated_request_status)
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
        data, error = CollectionNotesSchema(
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
                "collection_notes_id": collection_notes.id,
            }
        collection_notes.update(data)

    data = collection_notes_schema.dump(collection_notes).data

    if approvals_history_data:        
        approvals_history_data.update({"attribute": data})
        approvals_history = CollectionNotesApprovalHistory(approvals_history_data)
        approvals_history.save()

    return custom_response(data, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def delete(id):
    """
    Delete A Collection Note
    """
    collection_notes = CollectionNotes.get_one_based_off_control_accounts(id)
    if not collection_notes:
        return custom_response(
            {"status": "error", "msg": "collection_notes not found"}, 404
        )

    if collection_notes.status.value != "draft":
        return custom_response(
            {
                "status": "error",
                "msg": f"You cannot delete collection notes having status '{collection_notes.status.value}'",
            },
            400,
        )

    user_role = Permissions.get_user_role_permissions()["user_role"]
    if user_role != Permissions.principal:
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to delete",
            },
            403,
        )

    # collection_notes.deleted_at = datetime.utcnow()
    # collection_notes.save()
    collection_notes.delete()

    return custom_response(
        {"status": "success", "msg": "collection_notes deleted"}, 202
    )


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def get_approval_history(id):
    collection_notes = CollectionNotes.get_one_based_off_control_accounts(id)
    if not collection_notes:
        return custom_response(
            {"status": "error", "msg": "collection_notes not found"}, 404
        )

    collection_notes_approvals_history = collection_notes.cn_approvals_history()

    return custom_response(collection_notes_approvals_history, 200)
