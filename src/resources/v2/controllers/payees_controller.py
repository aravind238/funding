from flask import request, json
from src.models import *
import datetime
from src.resources.v2.helpers import custom_response, PaymentServices, api_response
from src.resources.v2.models.client_payees_model import PayeePaymentStatus
from src.middleware.authentication import Auth
from src.resources.v2.schemas import *
import pandas as pd
import numpy as np
from src.middleware.organization import Organization
from src.middleware.permissions import Permissions
from src.resources.v2.helpers.mails import SendMails
from src.resources.v2.helpers.convert_datetime import utc_to_local

payee_schema = PayeeSchema()
client_schema = ClientSchema()
client_payee_schema = ClientPayeeSchema()
comments_schema = CommentsSchema()
supporting_documents_schema = SupportingDocumentsSchema()


@Auth.auth_required
def create():
    """
    Create Payee
    """
    try:
        req_data = request.get_json()
        
        # user role
        user_role = Permissions.get_user_role_permissions()["user_role"]

        # only principal can create a new payee
        if (
            user_role 
            and user_role.lower() != Permissions.principal
        ):
            return custom_response(
                {
                    "status": "error",
                    "msg": f"{user_role} doesn't have permission to create a payee",
                },
                403,
            )

        if "client_id" not in req_data:
            return custom_response(
                {"status": "error", "msg": "client_id is required"}, 400
            )

        if "ref_type" not in req_data:
            return custom_response(
                {"status": "error", "msg": "ref_type is required"}, 400
            )
        
        client = Client.get_one_based_off_control_accounts(req_data["client_id"])
        if not client:
            return custom_response({"status": "error", "msg": "client not found"}, 404)
        if client.is_active == False:
            return custom_response({"status": "error", "msg": "Client is Inactive"}, 404)

        data, error = PayeeSchema(
            exclude=["is_new", "is_active", "last_processed_at", "status"]
        ).load(req_data)
        if error:
            return custom_response(error, 400)

        payee = Payee(data)
        
        payee.status = "draft"
        payee.last_processed_at = datetime.datetime.utcnow()
        payee.save()

        # add ClientPayee
        client_payee_json = {
            "client_id": req_data["client_id"],
            "payee_id": payee.id,
            "ref_type": req_data["ref_type"],
        }
        data, error = client_payee_schema.load(client_payee_json)
        if error:
            return custom_response(error, 400)

        client_payee = ClientPayee(data)
        client_payee.save()

        user_email = Permissions.get_user_details()["email"]

        data = payee_schema.dump(payee).data

        save_attribute_data = data.copy()
        save_attribute_data["client_payee"] = client_payee_schema.dump(client_payee).data
        save_attribute_data["internal_comments"] = []

        approvals_history_data = {
            "key": "created_at",
            "value": datetime.datetime.utcnow(),
            "user": user_email,
            "attribute": save_attribute_data,
            "payee_id": payee.id,
        }
        approvals_history = ApprovalsHistory(approvals_history_data)
        approvals_history.save()

        data.update(
            {
                "client_name": client.name,
                "client_id": client.id,
                "ref_type": req_data["ref_type"],
            }
        )

        # payment services
        payment_services = PaymentServices(request_type=payee, req_data=req_data)

        payment_services.add_in_payment_services()

        get_institution_details = payment_services.get_institution_details(
            ref_id=f"{payee.id}", ref_id_type=f"{req_data['ref_type']}"
        )
        if (
            get_institution_details["status_code"] == 200
            and get_institution_details["payload"]
        ):
            if (
                "accounts_info" in get_institution_details["payload"][0]
                and get_institution_details["payload"][0]["accounts_info"]
            ):
                for account_info in get_institution_details["payload"][0][
                    "accounts_info"
                ]:
                    if account_info["label"] == "bank_account_name":
                        data[account_info["label"]] = account_info["attribute"][
                            account_info["label"]
                        ]
                    else:
                        data[account_info["label"]] = account_info["attribute"]

        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Payee
    """
    try:
        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        search = request.args.get("search", None, type=str)
        ordering = request.args.get("ordering", None, type=str)
        stage = request.args.get("stage", None, type=str)
        control_account = request.args.get("control_account", None, type=int)
        active = request.args.get("active", None, type=str)

        if page > 0:
            data = PayeeListing.get_paginated_payees(
                page=page,
                rpp=rpp,
                search=search,
                ordering=ordering,
                stage=stage,
                control_account=control_account,
                active=active,
            )
        else:
            data = PayeeListing.get_all()

        if data is None:
            data = []

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(payee_id):
    """
    Get A Payee
    """
    try:
        client_id = request.args.get("client_id", 0)
        if not client_id:
            return custom_response(
                {"status": "error", "msg": "client_id is required"}, 400
            )

        payee = Payee.get_one_based_off_control_accounts(payee_id)
        if not payee:
            return custom_response({"status": "error", "msg": "payee not found"}, 404)
        
        # remove contact information and other components of payee if payee is disabled LC-2315
        if not payee.is_active:
            data = PayeeSchema(
                exclude=["address_line_1", "city", "state_or_province", "country", "postal_code", "phone", "alt_phone", "email"]
            ).dump(payee).data
        else:
            data = payee_schema.dump(payee).data

        client_name = None
        ref_type = None
        client = Client.get_one_client(client_id)
        if not client:
            return custom_response(
                {"status": "error", "msg": "client not found"}, 404
            )
            
        client_payee = ClientPayee.get_by_client_payee_id(client_id, payee_id)
        if not client_payee:
            return custom_response(
                {"status": "error", "msg": "client_payee not found"}, 404
            )
        
        client_name = client.name
        ref_type = client_payee.ref_type.value
        payee_payment_status = client_payee.payment_status

        # payee internal comments
        payee_comments = payee.get_payee_internal_comments()

        internal_comments = None
        if payee_comments:
            internal_comments = payee_comments.comment
        
        data.update(
            {
                "client_name": client_name,
                "client_id": client_id,
                "ref_type": ref_type,
                "payment_status": payee_payment_status,
                "internal_comments": internal_comments,
            }
        )

        if payee.is_active:
            # get institution accounts info
            payment_services = PaymentServices(request_type=payee)

            get_institution_details = payment_services.get_institution_details(
                ref_id=f"{payee.id}", ref_id_type=f"{ref_type}"
            )
            if (
                get_institution_details["status_code"] == 200
                and get_institution_details["payload"]
            ):
                if (
                    "accounts_info" in get_institution_details["payload"][0]
                    and get_institution_details["payload"][0]["accounts_info"]
                ):
                    for account_info in get_institution_details["payload"][0][
                        "accounts_info"
                    ]:
                        if account_info["label"] == "bank_account_name":
                            data[account_info["label"]] = account_info["attribute"][
                                account_info["label"]
                            ]
                        else:
                            data[account_info["label"]] = account_info["attribute"]

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(payee_id):
    """
    Update A Payee
    """
    req_data = request.get_json()
    client_id = req_data.get("client_id", 0)
    ref_type = None
    payment_services = None
    lcra_client_accounts_id = None
    can_edit_payee_payment_status_internal_comments = False

    if not client_id:
        return custom_response(
            {"status": "error", "msg": "client_id is required"}, 400
        )

    if "client_id" in req_data:
        del req_data["client_id"]

    payee = Payee.get_one_based_off_control_accounts(payee_id)
    if not payee:
        return custom_response({"status": "error", "msg": "Payee not found"}, 404)
    if not payee.is_active:
        return custom_response({"status": "error", "msg": "Payee is not active"}, 400)

    # is_active
    is_active = req_data["is_active"] if "is_active" in req_data else None
    # can't reactivate a deactivated payee LC-2315
    if is_active is not None and is_active == True:
        del req_data["is_active"]

    approvals_history_data = {}
    # payee status
    payee_status_update = req_data["status"] if "status" in req_data else None

    # user role
    get_user_role = Permissions.get_user_role_permissions()
    user_role = get_user_role["user_role"]
    create_edit_permission = get_user_role["create_edit_permission"]
    # # organization ids
    # organization_ids = get_user_role["organization_access"]

    # user role not assigned to user
    if not user_role:
        return custom_response(
            {"status": "error", "msg": f"user role not found, please assign role"}, 403
        )

    # Only BO can disable the payee LC-2315
    if (
        is_active is not None
        and is_active == False
        and user_role.lower() != Permissions.bo
    ):
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to disable the payee",
            },
            403,
        )

    # checking, for ae which don't have permission to edit payee(LC-1573)
    if (
        payee_status_update
        and len(req_data) > 1
        or (not payee_status_update and len(req_data) > 1)
    ) and user_role.lower() in ["ae"]:
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to edit payee",
            },
            403,
        )

    # check, if payee can be updated
    validated_request_status = Permissions.can_update_payee(
        request=payee, update_request_status=payee_status_update, user_role=user_role
    )
    print("payee", validated_request_status)
    if validated_request_status and validated_request_status["status_code"] in [
        403,
    ]:
        return custom_response(
            {
                "status": validated_request_status["status"],
                "msg": validated_request_status["msg"],
            },
            validated_request_status["status_code"],
        )
    
    # user details
    get_user_detail = Permissions.get_user_details()
    user_email = get_user_detail["email"]

    if req_data:

        # checking condition for both payment status and internal comments cannot be null.
        if (
            "payment_status" in req_data and req_data["payment_status"] is None
        ) and (
            "internal_comments" in req_data and req_data["internal_comments"] is None
        ):
            return custom_response({"status": "error", "msg": "Payment Status and Internal Comments cannot be null."}, 400)
        
        # Payment Status
        payment_status = req_data["payment_status"] if "payment_status" in req_data else None
        # Internal Comments
        internal_comments = req_data["internal_comments"] if "internal_comments" in req_data else None
        
        # LC-2318: checking, BO has permission to edit the payment_status and internal_comments
        if (
            user_role.lower() == Permissions.bo
            and "edit_payee_payment_status_internal_comments" in create_edit_permission 
            and create_edit_permission["edit_payee_payment_status_internal_comments"]
        ):
            can_edit_payee_payment_status_internal_comments = True

        # LC-2317: Only BO can edit the payment_status and internal_comments
        if (
            (
                payment_status is not None
                or internal_comments is not None
            )
            and payee.status.value == "approved"
            and (
                user_role.lower() != Permissions.bo
                or not can_edit_payee_payment_status_internal_comments
            )
        ):
            return custom_response(
                {
                    "status": "error",
                    "msg": f"{user_role} doesn't have permission to edit the Payment Status and Internal Comments.",
                },
                403,
            )
        
        # saved payee payment status
        get_payee_payment_status = payee.get_payee_payment_status(client_id)
        # saved payee internal comments
        get_payee_internal_comments = payee.get_payee_internal_comments()

        ## LC-2316: checking condition, add payment status mandatory for approval ##
        # - I can select In-System, Out-of-System. (mandatory for approval,  not for reject or action required)
        #       a. For existing Payee in the system, we don’t force any value in the “status field”
        # - I can add internal comments. (mandatory for approval,  not for reject or action required)
        #       a. Only make it mandatory IF the Status field is “Out-of-Sytem”
        #       b. NOT REQUIRED for In-System
        if (
            payee_status_update 
            and payee_status_update == "approved"
        ):
            if (
                payment_status is None
                and not get_payee_payment_status
            ):
                return custom_response({"status": "error", "msg": "Please add Payee Payment Status."}, 400)
            
            if (
                (
                    (
                        payment_status is None 
                        and get_payee_payment_status 
                        and get_payee_payment_status == "Out-of-System" 
                    ) or (
                        payment_status is not None 
                        and payment_status == "Out-of-System" 
                    )
                ) and (
                    not get_payee_internal_comments 
                    and internal_comments is None 
                )
            ):
                return custom_response({"status": "error", "msg": "Please add Internal Comments."}, 400)
        
        # checking for saving key value in approval history on payment status and internal comments added/updated
        ## LC-2316: ##
        # - internal comments are mandatory IF the Status field is “Out-of-Sytem”
        # - NOT REQUIRED for In-System
        if (
            payment_status is not None 
            or internal_comments is not None
        ):

            key_value = None
            if (
                payment_status is not None 
                and internal_comments is None 
                and not get_payee_payment_status
            ):
                key_value = "payment_status_added_at"

            if (
                (
                    payment_status is not None 
                    and internal_comments is None 
                    and get_payee_payment_status
                ) or (
                    payment_status is not None 
                    and internal_comments is not None 
                    and get_payee_payment_status 
                    and get_payee_internal_comments
                    and get_payee_internal_comments.comment == internal_comments
                    and get_payee_payment_status != payment_status
                )
            ):
                key_value = "payment_status_updated_at"

            if (
                internal_comments is not None 
                and payment_status is None 
                and not get_payee_internal_comments
            ):
                key_value = "internal_comments_added_at"

            if (
                (
                    internal_comments is not None 
                    and payment_status is None 
                    and get_payee_internal_comments
                ) or (
                    payment_status is not None 
                    and internal_comments is not None 
                    and get_payee_payment_status 
                    and get_payee_internal_comments
                    and get_payee_payment_status == payment_status
                    and get_payee_internal_comments.comment != internal_comments
                )
            ):
                key_value = "internal_comments_updated_at"

            if (
                payment_status is not None 
                and internal_comments is not None 
                and not get_payee_payment_status 
                and not get_payee_internal_comments
            ):
                key_value = "payment_status_and_internal_comments_added_at"

            if (
                payment_status is not None 
                and internal_comments is not None 
                and get_payee_payment_status 
                and get_payee_internal_comments
                and get_payee_payment_status != payment_status
                and get_payee_internal_comments.comment != internal_comments
            ):
                key_value = "payment_status_and_internal_comments_updated_at"


            if (
                payment_status 
                and payment_status not in PayeePaymentStatus
            ):
                return custom_response({"status": "error", "msg": "Invalid Payee Payment Status Value"}, 400)
            
            if (
                (
                    (
                        payment_status is None 
                        and get_payee_payment_status 
                        and get_payee_payment_status == "Out-of-System" 
                    ) or (
                        payment_status is not None 
                        and payment_status == "Out-of-System" 
                    )
                ) and (
                    not get_payee_internal_comments 
                    and internal_comments is None 
                )
            ):
                return custom_response({"status": "error", "msg": "Please add Internal Comments."}, 400)
            
            # add/update payee payment status
            if payment_status is not None :
                payee.add_payee_payment_status(payment_status)

            # add/update payee internal comments
            if internal_comments is not None :
                payee.add_payee_internal_comments(internal_comments)

            # save approvals history
            if key_value:
                approvals_history_data = {
                    "user": user_email,
                    "key": key_value,
                    "value": datetime.datetime.utcnow(),
                    "payee_id": payee_id,
                }

        if user_role.lower() == Permissions.bo:
            data, error = PayeeSchema(
                exclude=[
                    "first_name",
                    "last_name",
                    "account_nickname",
                    "address_line_1",
                    "city",
                    "state_or_province",
                    "country",
                    "postal_code",
                    "phone",
                    "alt_phone",
                    "email",
                    "notes",
                ]
            ).load(req_data, partial=True)
        else:
            data, error = payee_schema.load(req_data, partial=True)
        if error:
            return custom_response(error, 400)

        # on payee status update, update last_processed_at
        if "status" in req_data:
            data["last_processed_at"] = datetime.datetime.utcnow()

            # Pending
            if req_data["status"] == "pending":
                approvals_history_data = {
                    "user": user_email,
                    "key": "submitted_at",
                    "value": datetime.datetime.utcnow(),
                    "payee_id": payee_id,
                }

            # approved
            if req_data["status"] == "approved":
                approvals_history_data = {
                    "user": user_email,
                    "key": "approved_at",
                    "value": datetime.datetime.utcnow(),
                    "payee_id": payee_id,
                }

        payee.update(data)

        # get client
        client = Client.get_one_client(client_id)
        if not client:
            return custom_response(
                {"status": "error", "msg": "client not found"}, 404
            )
            
        # get client payee
        client_payee = ClientPayee.get_by_client_payee_id(client_id, payee_id)
        if not client_payee:
            return custom_response(
                {"status": "error", "msg": "client_payee not found"}, 404
            )
        
        client_name = client.name
        ref_type = client_payee.ref_type.value
        lcra_client_accounts_id = client.lcra_client_accounts_id
        payee_payment_status = client_payee.payment_status

        # payee internal comments
        payee_internal_comments = payee.get_payee_internal_comments()
        internal_comments = None
        if payee_internal_comments:
            internal_comments = payee_internal_comments.comment

        req_data["ref_type"] = ref_type

        payment_services = PaymentServices(request_type=payee, req_data=req_data)

        ## for updating data in payment services if payee status in ["action_required", "draft"]##
        if payee.status.value in ["action_required", "draft"]:
            payment_services.add_in_payment_services()

    data = payee_schema.dump(payee).data


    if approvals_history_data:        
        save_attribute_data = data.copy()
        save_attribute_data["client_payee"] = client_payee_schema.dump(client_payee).data
        save_attribute_data["internal_comments"] = (
            comments_schema.dump(payee_internal_comments).data 
            if payee_internal_comments 
            else []
        )

        approvals_history_data.update({"attribute": save_attribute_data})
        approvals_history = ApprovalsHistory(approvals_history_data)
        approvals_history.save()

    data.update(
        {
            "client_name": client_name,
            "client_id": client_id,
            "ref_type": ref_type,
            "payment_status": payee_payment_status,
            "internal_comments": internal_comments,
        }
    )

    # if payment services is None
    if not payment_services:
        payment_services = PaymentServices(request_type=payee)

    # get institution accounts info
    get_institution_details = payment_services.get_institution_details(
        ref_id=payee.id, ref_id_type=f"{ref_type}"
    )
    if (
        get_institution_details["status_code"] == 200
        and get_institution_details["payload"]
    ):
        if (
            "accounts_info" in get_institution_details["payload"][0]
            and get_institution_details["payload"][0]["accounts_info"]
        ):
            for account_info in get_institution_details["payload"][0]["accounts_info"]:
                if account_info["label"] == "bank_account_name":
                    data[account_info["label"]] = account_info["attribute"][
                        account_info["label"]
                    ]
                else:
                    data[account_info["label"]] = account_info["attribute"]

    # payee notifications
    if payee_status_update:
        recipient_role_name = None
        if payee_status_update == "pending":
            # Mail to Bo
            recipient_role_name = "BO"
        if payee_status_update == "approved":
            # Mail to Principal
            recipient_role_name = "Principal"

        if recipient_role_name:
            # Get Organization ids
            organization_client_account = OrganizationClientAccount.query.filter(
                OrganizationClientAccount.lcra_client_account_id
                == lcra_client_accounts_id
            ).first()

            organization_id = None
            if organization_client_account:
                organization_id = organization_client_account.organization_id

            send_mails = SendMails(
                request_type=payee,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()

    return custom_response(data, 200)


@Auth.auth_required
def delete(payee_id):
    """
    Delete A Payee
    """
    try:
        requests_by_payee = []
        cannot_delete_payee = False
        user_role = Permissions.get_user_role_permissions()["user_role"]

        # user role not assigned to user
        if not user_role:
            return custom_response(
                {"status": "error", "msg": f"user role not found, please assign role"},
                403,
            )

        # checking, for ae/bo which don't have permission to delete payee(LC-1834)
        if user_role.lower() in ["ae", "bo"]:
            return custom_response(
                {
                    "status": "error",
                    "msg": f"{user_role} doesn't have permission to delete payee",
                },
                403,
            )

        payee = Payee.get_one_based_off_control_accounts(payee_id)
        if not payee:
            return custom_response({"status": "error", "msg": "payee not found"}, 404)
        
        if payee.status.value not in ["draft", "approved"]:
            return custom_response(
                {
                    "status": "error",
                    "msg": "payee cannot be deleted"
                },
                400,
            )

        # get soa based off payee
        soa = payee.get_soa_by_payee()
        # checking, if soa is associated with payee
        if soa:
            requests_by_payee.extend([f"{s.client.ref_client_no}-SOAID{s.soa_ref_id}" for s in soa])
            cannot_delete_payee = True

        # get reserve release based off payee
        rr = payee.get_rr_by_payee()
        # checking, if reserve release is associated with payee
        if rr:
            requests_by_payee.extend([f"{r.client.ref_client_no}-RRID{r.ref_id}" for r in rr])
            cannot_delete_payee = True
        
        # checking, if payee can be deleted LC-1864
        if cannot_delete_payee:
            requests_by_payee = ", ".join(requests_by_payee)
            return custom_response(
                {
                    "status": "error",
                    "msg": f"Payee cannot be deleted. Please review requests: {requests_by_payee} . Once those requests are completed, you will be able to delete the payee."
                },
                400,
            )

        payee.archive()
        return custom_response({"status": "success", "msg": "Payee deleted"}, 202)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def import_payees():
    try:
        # For reading excel file
        excel_file = (
            "src/resources/v1/payees/services/[Funding interface] PayeesDB - LCEI.xlsx"
        )
        file_data = pd.read_excel(excel_file)

        # if having value Null or NaN
        if not file_data.empty:
            file_data = file_data.replace({pd.np.nan: None})

        file_data = file_data.values.tolist()

        for row in file_data:
            # print('have_client', row[7])
            get_client = Client.query.filter_by(
                is_deleted=False, lcra_client_accounts_number=row[7]
            ).first()

            if get_client is not None:
                get_payee = Payee.query.filter_by(is_deleted=False, name=row[1]).first()

                if get_payee is not None:
                    # print('have_client_payee', row[7], row[1])
                    exists = bool(
                        ClientPayee.query.filter(
                            ClientPayee.is_deleted == False,
                            ClientPayee.payee_id == get_payee.id,
                            ClientPayee.client_id == get_client.id,
                        ).first()
                    )
                    if exists is True:
                        continue
                else:
                    # print('no_client_payee')
                    # store payees to payees model
                    req_data = {
                        "name": str(row[1]),
                        "address_line_1": str(row[2]),
                        "city": str(row[3]),
                        "state_or_province": str(row[4]),
                        "country": str(row[6]),
                    }

                    data, error = payee_schema.load(req_data)
                    if error:
                        return custom_response(error, 400)

                    payee = Payee(data)
                    payee.save()

                    # store client_payees to client_payees model
                    req_data = {"client_id": get_client.id, "payee_id": payee.id}
                    data, error = client_payee_schema.load(req_data)

                    if error:
                        return custom_response(error, 400)

                    client_payee = ClientPayee(data)
                    client_payee.save()

        return custom_response(
            {"status": "success", "msg": "Payees list imported successfully"}, 200
        )
    except Exception as e:
        return custom_response({"status": "success", "msg": str(e)}, 404)


@Auth.auth_required
def get_approval_history(payee_id):
    payee = Payee.get_one_based_off_control_accounts(payee_id)
    if not payee:
        return custom_response({"status": "error", "msg": "payee not found"}, 404)

    approvals_history = payee.payee_approvals_history()

    return custom_response(approvals_history, 200)


@Auth.auth_required
def get_comments(payee_id):
    payee = Payee.get_one_based_off_control_accounts(payee_id)
    if not payee:
        return custom_response({"status": "error", "msg": "payee not found"}, 404)

    comments = payee.payee_comments()
    if not comments:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    payee_comments = comments_schema.dump(comments, many=True).data

    return custom_response(payee_comments, 200)


@Auth.auth_required
def get_supporting_documents(payee_id):
    payee = Payee.get_one_based_off_control_accounts(payee_id)
    if not payee:
        return custom_response({"status": "error", "msg": "payee not found"}, 404)

    get_supporting_documents = payee.payee_supporting_documents()
    if not get_supporting_documents:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    supporting_documents = supporting_documents_schema.dump(
        get_supporting_documents, many=True
    ).data

    return custom_response(supporting_documents, 200)

@Auth.auth_required
def get_reasons(payee_id):
    status = request.args.get("status", "")

    payee = Payee.get_one_based_off_control_accounts(payee_id)
    if not payee:
        return custom_response({"status": "error", "msg": "payee not found"}, 404)

    get_payee_reasons = payee.reasons(status=status)
    if not get_payee_reasons:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    payee_reasons = []
    for payee_reason in get_payee_reasons:
        attribute = payee_reason.attribute

        each_reason = {
            "id": attribute["id"] if "id" in attribute else None,
            "user": payee_reason.user,
            "payee_id": payee_reason.payee_id,
            "notes": attribute["notes"] if "notes" in attribute else None,
            "status": attribute["status"] if "status" in attribute else None,
            "created_at": utc_to_local(dt=payee_reason.created_at.isoformat()),
            "updated_at": utc_to_local(dt=payee_reason.updated_at.isoformat()),
        }
        payee_reasons.append(each_reason)

    return custom_response(payee_reasons, 200)
