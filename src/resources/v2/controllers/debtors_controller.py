from flask import request, json
from sqlalchemy import not_, or_, and_
from src.models import *
from datetime import datetime
from decimal import Decimal
from src.middleware.authentication import Auth
from src import db
import os
import requests
from src.resources.v2.helpers import custom_response, get_debtor_limits_from_third_party, SendMails
from src.resources.v2.schemas import *
from src.middleware.permissions import Permissions

debtor_schema = DebtorSchema()
debtor_client_schema = DebtorClientSchema()
client_debtor_schema = ClientDebtorSchema()
duplicate_debtors_schema = DuplicateDebtorsSchema()
debtor_limit_approvals_schema = DebtorLimitApprovalsSchema()


@Auth.auth_required
@Auth.has_request_permission(
    request_type=Permissions.credit_limit,
    msg="Please contact support to enable this functionality. Credit Limit permission not set.",
)
def create():
    """
    Create Debtor Function
    """
    try:
        req_data = request.get_json()
        # on client adding debtor, source = 'funding'
        req_data["source"] = "funding"
        # static value for ref_key
        req_data["ref_key"] = str(0)
        # flag for creating the debtor without checking existing name
        create_forcefully = request.args.get("create_forcefully", None, type=str)

        if ("client_id" not in req_data) or (not req_data["client_id"]):
            return custom_response(
                {"status": "error", "msg": "Client id is required"}, 400
            )

        client = Client.get_one_based_off_control_accounts(req_data["client_id"])
        if not client:
            return custom_response({"status": "error", "msg": "Client not found"}, 404)
        if client.is_active == False:
            return custom_response({"status": "error", "msg": "Client is Inactive"}, 404)

        data, error = DebtorSchema(
            exclude=["is_active"]
        ).load(req_data)
        if error:
            return custom_response(error, 400)

        get_debtors_existed_names = Debtor.get_debtors_duplicate_names(
            name=data["name"], client_id=req_data["client_id"], create_forcefully=create_forcefully
        )
        if get_debtors_existed_names["status_code"] != 200:
            return custom_response(
                    {"status": "error", "msg": get_debtors_existed_names["msg"], "can_create_forcefully": get_debtors_existed_names["can_create_forcefully"]}, get_debtors_existed_names["status_code"],
                )

        debtor = Debtor(data)
        debtor.save()

        client_debtor_dict = {
            "client_id": req_data["client_id"],
            "debtor_id": debtor.id,
            "credit_limit": 0,
        }

        client_debtor = ClientDebtor(client_debtor_dict)
        client_debtor.save()

        data = debtor_schema.dump(debtor).data

        # get logged user email
        user_email = Permissions.get_user_details()["email"]

        debtor_data = data.copy()
        debtor_data["client_debtors"] = client_debtor_schema.dump(client_debtor).data

        approvals_history_data = {
            "key": "created_at",
            "value": datetime.utcnow(),
            "user": user_email,
            "attribute": debtor_data,
            "debtor_id": debtor.id,
        }
        approvals_history = DebtorApprovalsHistory(approvals_history_data)
        approvals_history.save()
        
        credit_limit_amount = (
            req_data["credit_limit_requested"]
            if "credit_limit_requested" in req_data and req_data["credit_limit_requested"] > Decimal(0)
            else Decimal(5000)
        )

        debtor_limit_approvals_dict = {
            "client_id": req_data["client_id"],
            "debtor_id": debtor.id,
            "credit_limit_requested": credit_limit_amount,
            "status": "submitted",
            "last_processed_at": datetime.utcnow()
        }

        debtor_limit_approvals = DebtorLimitApprovals(debtor_limit_approvals_dict)
        debtor_limit_approvals.save()

        debtor_limit_schema_data = debtor_limit_approvals_schema.dump(debtor_limit_approvals).data

        # save debtor limit approvals history
        debtor_limit_approvals_history_data = {
            "key": "submitted_at",
            "value": datetime.utcnow(),
            "user": user_email,
            "attribute": debtor_limit_schema_data,
            "debtor_limit_approvals_id": debtor_limit_approvals.id,
        }
        debtor_limit_approvals_history = DebtorLimitApprovalsHistory(debtor_limit_approvals_history_data)
        debtor_limit_approvals_history.save()

        if "status" in debtor_limit_schema_data and debtor_limit_schema_data["status"] == "submitted":
            # Mail to AE
            template_name = os.environ.get("REQUEST_SUBMITTED_TO_ACCOUNT_EXECUTIVE_MAIL")
            recipient_role_name = "AE"
            request_type = debtor_limit_approvals
            organization = OrganizationClientAccount.query.filter_by(
                lcra_client_account_id=debtor_limit_approvals.client.lcra_client_accounts_id
            ).first()
            # get client_id
            client_id = request_type.client_id
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization.organization_id,
            )
            send_mails.send_mail_request_notifications()
            
        data["credit_limit_requested"] = debtor_limit_schema_data["credit_limit_requested"]
        data["credit_limit_approved"] = debtor_limit_schema_data["credit_limit_approved"]
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Debtor
    """
    try:
        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        ordering = request.args.get("ordering", None, type=str)
        search = request.args.get("search", None, type=str)
        control_account = request.args.get("control_account", None, type=str)
        active = request.args.get("active", None, type=str)

        if page > 0:
            data = DebtorListing.get_paginated_debtors(
                page=page,
                rpp=rpp,
                ordering=ordering,
                search=search,
                control_account=control_account,
                active=active,
            )
        else:
            data = DebtorListing.get_all()

        if data is None:
            data = []

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)


@Auth.auth_required
def get_one(debtor_id):
    """
    Get A Debtor
    """
    try:
        client_id = request.args.get("client_id", None)
        if not client_id:
            return custom_response(
                {
                    "status": "error", 
                    "msg": "client id is required"
                },
                400,
            )

        debtor = Debtor.get_one_based_off_control_accounts(debtor_id, client_id=client_id)
        if not debtor:
            return custom_response({"status": "error", "msg": "debtor not found"}, 404)

        client_debtor = ClientDebtor.query.filter_by(
            debtor_id=debtor_id, client_id=client_id, is_deleted=False
        ).first()
        if not client_debtor:
            return custom_response(
                {"status": "error", "msg": "client_debtor not found"}, 404
            )
            
        client_ref_key = client_debtor.client.ref_key

        # get debtor from 3rd party
        debtor_limits = get_debtor_limits_from_third_party(
            debtor.ref_key, client_ref_key
        )

        if "status_code" in debtor_limits and debtor_limits["status_code"] == 200:
            # update to client_debtor table
            req_client_debtor = {
                "current_ar": debtor_limits["current_ar"],
                "credit_limit": debtor_limits["debtor_limit"],
                "days_31_60": str(debtor_limits["age_31_60_days"]),
                "days_61_90": str(debtor_limits["age_61_90_days"]),
                "days_91_120": str(debtor_limits["age_91_120_days"]),
            }

            data, error = client_debtor_schema.load(req_client_debtor, partial=True)
            if error:
                return custom_response(error, 400)

            client_debtor.update(data)

        client_name = None
        credit_limit = None
        current_ar = float(0)
        days_1_30 = None
        days_31_60 = None
        days_61_90 = None
        days_91_120 = None
        default_term_value = None
        credit_limit_requested = float(0)
        credit_limit_approved = float(0)

        if client_debtor:
            client_name = client_debtor.client.name
            credit_limit = client_debtor.credit_limit
            current_ar = client_debtor.current_ar
            days_1_30 = client_debtor.days_1_30
            days_31_60 = client_debtor.days_31_60
            days_61_90 = client_debtor.days_61_90
            days_91_120 = client_debtor.days_91_120
            default_term_value = client_debtor.default_term_value

        debtor.update(
            {
                "client_name": client_name,
                "credit_limit": credit_limit,
                "current_ar": current_ar,
                "days_1_30": days_1_30,
                "days_31_60": days_31_60,
                "days_61_90": days_61_90,
                "days_91_120": days_91_120,
                "default_term_value": default_term_value,
            }
        )

        data = debtor_client_schema.dump(debtor).data

        debtor_limit_approvals_obj = DebtorLimitApprovals.query.filter_by(
            debtor_id=debtor_id, client_id=client_id, deleted_at=None
        ).order_by(
            DebtorLimitApprovals.id.desc()
        ).first()

        if debtor_limit_approvals_obj:
            credit_limit_requested = debtor_limit_approvals_obj.credit_limit_requested
            credit_limit_approved = debtor_limit_approvals_obj.credit_limit_approved

        data["credit_limit_requested"] = credit_limit_requested
        data["credit_limit_approved"] = credit_limit_approved
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)


@Auth.auth_required
def update(debtor_id):
    """
    Update A Debtor
    """
    req_data = request.get_json()

    # has_debtor = Debtor.query.filter_by(is_deleted=False)
    # debtor = has_debtor.filter_by(id=debtor_id).first()
    
    client_id = req_data["client_id"] if "client_id" in req_data else None
    if ("client_id" not in req_data) or (not client_id):
        return custom_response(
            {"status": "error", "msg": "client_id is required"}, 400
        )

    debtor = Debtor.get_one_based_off_control_accounts(debtor_id, client_id=client_id)
    if not debtor:
        return custom_response(
            {"status": "error", "msg": "debtor not found"}, 404
        )

    if debtor.source.value != "funding":
        return custom_response(
            {"status": "error", "msg": "debtor cannot be updated"}, 400
        )

    get_debtors_soa = get_soa_by_debtor(debtor_id=debtor_id, client_id=client_id)

    if get_debtors_soa["status_code"] != 200:
        return custom_response(
            {
                "status": "error", 
                "msg": get_debtors_soa["msg"]
            }, 
            get_debtors_soa["status_code"]
        )
    
    debtors_soa_status = []
    if len(get_debtors_soa["reference_ids"]) > 0:
        [
            debtors_soa_status.append(each_data["status"])
            for each_data in get_debtors_soa["data"]
            if each_data["status"] != "draft"
        ]
        
        if debtors_soa_status:
            return custom_response(
                {
                    "status": "error", 
                    "msg": f"New Debtor '{debtor.name}' details cannot be changed."
                }, 
                400
            )

    if req_data:
        if (
            "ref_key" in req_data
            # and req_data["ref_key"] > 0
            and debtor.source.value == "funding"
        ):
            del req_data["ref_key"]

        if "source" in req_data:
            del req_data["source"]
        
        data, error = DebtorSchema(
            exclude=["is_active", "uuid"]
        ).load(req_data, partial=True)
        if error:
            return custom_response(error, 400)

        # if "name" in req_data and req_data["name"] != debtor.name:
        #     has_debtor_name = has_debtor.filter_by(name=req_data["name"]).count()
        #     if has_debtor_name:
        #         req_debtor_name = req_data["name"]
        #         return custom_response(
        #             {
        #                 "status": "error",
        #                 "msg": f"name '{req_debtor_name}' already exists",
        #             },
        #             400,
        #         )

        debtor.update(data)

        client_debtor = ClientDebtor.query.filter_by(
            debtor_id=debtor_id, client_id=client_id, is_deleted=False
        ).first()
        if not client_debtor:
            client_debtor_dict = {
                "client_id": client_id,
                "debtor_id": debtor.id,
                "credit_limit": 0,
            }

            client_debtor = ClientDebtor(client_debtor_dict)
            client_debtor.save()
    
    data = debtor_schema.dump(debtor).data

    # get logged user email
    user_email = Permissions.get_user_details()["email"]

    debtor_data = data.copy()
    debtor_data["client_debtors"] = client_debtor_schema.dump(client_debtor).data

    approvals_history_data = {
        "key": "updated_at",
        "value": datetime.utcnow(),
        "user": user_email,
        "attribute": debtor_data,
        "debtor_id": debtor.id,
    }
    approvals_history = DebtorApprovalsHistory(approvals_history_data)
    approvals_history.save()

    # debtor limit approvals
    debtor_limit_approvals = DebtorLimitApprovals.query.filter(
        DebtorLimitApprovals.debtor_id == debtor.id,
        DebtorLimitApprovals.deleted_at == None,
    ).order_by(DebtorLimitApprovals.id.desc()).first()
    if debtor_limit_approvals:            
        credit_limit_requested = (
            req_data["credit_limit_requested"]
            if "credit_limit_requested" in req_data and req_data["credit_limit_requested"]
            else debtor_limit_approvals.credit_limit_requested
        )
        debtor_limit_approvals.credit_limit_requested = credit_limit_requested
        debtor_limit_approvals.save()
    
        debtor_limit_schema_data = debtor_limit_approvals_schema.dump(debtor_limit_approvals).data

        # save debtor limit approvals history
        debtor_limit_approvals_history_data = {
            "key": "updated_at",
            "value": datetime.utcnow(),
            "user": user_email,
            "attribute": debtor_limit_schema_data,
            "debtor_limit_approvals_id": debtor_limit_approvals.id,
        }
        debtor_limit_approvals_history = DebtorLimitApprovalsHistory(debtor_limit_approvals_history_data)
        debtor_limit_approvals_history.save()
        
        data["credit_limit_requested"] = debtor_limit_schema_data["credit_limit_requested"]
        data["credit_limit_approved"] = debtor_limit_schema_data["credit_limit_approved"]
    return custom_response(data, 200)


@Auth.auth_required
def delete(debtor_id):
    """
    Delete A Debtor
    """
    try:
        client_id = request.args.get("client_id", None)
        debtor = Debtor.get_one_based_off_control_accounts(debtor_id, client_id=client_id)
        
        if not debtor:
            return custom_response({"status": "error", "msg": "debtor not found"}, 404)

        if debtor.source.value != "funding":
            return custom_response(
                {
                    "status": "error", 
                    "msg": "Debtor cannot be deleted"
                },
                400,
            )

        can_delete_debtors = False
        # user permissions
        user_permissions = Permissions.get_user_role_permissions()
        
        misc_permissions = (
            user_permissions["user_permissions"]["misc_permissions"]
            if "misc_permissions" in user_permissions["user_permissions"]
            else None
        )
        # checking, if has permission can_delete_debtors
        if (
            misc_permissions
            and "can_delete_debtors" in misc_permissions
            and misc_permissions["can_delete_debtors"]
        ):
            can_delete_debtors = True

        if not can_delete_debtors:
            return custom_response(
                {
                    "status": "error", 
                    "msg": "You do not have permission to delete debtor"
                },
                403,
            )

        if not client_id:
            return custom_response(
                {
                    "status": "error", 
                    "msg": "client id is required"
                },
                400,
            )

        client = Client.query.filter_by(
            id=client_id, is_deleted=False
        ).first()

        if not client:
            return custom_response(
                {
                    "status": "error", 
                    "msg": "client not found"
                },
                404,
            )
        get_debtors_soa = get_soa_by_debtor(debtor_id=debtor_id, client_id=client_id)
        
        if len(get_debtors_soa["reference_ids"]) > 0:
            reference_ids = ','.join(get_debtors_soa["reference_ids"])
            return custom_response(
                {
                    "status": "error", 
                    "msg": f'There are {len(get_debtors_soa["reference_ids"])} requests having reference ids {reference_ids} using the New Debtor.'
                }, 
                400
            )
        
        client_debtor = ClientDebtor.query.filter_by(
            debtor_id=debtor_id, client_id=client_id, is_deleted=False
        ).first()

        # soft delete
        client_debtor.soft_delete()
        debtor.soft_delete()
        
        # get logged user email
        user_email = Permissions.get_user_details()["email"]
        
        debtor_data = debtor_schema.dump(debtor).data
        debtor_data["client_debtors"] = client_debtor_schema.dump(client_debtor).data

        approvals_history_data = {
            "key": "deleted_at",
            "value": datetime.utcnow(),
            "user": user_email,
            "attribute": debtor_data,
            "debtor_id": debtor.id,
        }

        approvals_history = DebtorApprovalsHistory(approvals_history_data)
        approvals_history.save()

        return custom_response({"status": "success", "msg": "Debtor deleted successfully"}, 202)
    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)

@Auth.auth_required
def get_requests_by_debtor(debtor_id):
    """
    Get SOA and Invoices of Debtor
    """
    client_id = request.args.get("client_id", None)
    if not client_id:
        return custom_response(
            {
                "status": "error", 
                "msg": "client id is required"
            },
            400,
        )
      
    get_soas = get_soa_by_debtor(debtor_id=debtor_id, client_id=client_id)
    if get_soas["status_code"] != 200:
        return custom_response(
            {
                "status": "error", 
                "msg": get_soas["msg"]
            }, 
            get_soas["status_code"]
        )
        
    return {
        "data": get_soas["data"],
        "total_invoices": get_soas["total_invoices"],
    }


@Auth.auth_required
def get_debtor_limits():
    client_id = request.args.get("client_id", None)
    debtor_id = request.args.get("debtor_id", None)

    joined_table_query = (
        db.session.query(
            Debtor.ref_key, Client.ref_key, Client.id, Client.name, Debtor.name
        )
        .filter(Debtor.id == debtor_id)
        .filter(ClientDebtor.debtor_id == debtor_id)
        .filter(Client.id == client_id)
        .first()
    )

    if not joined_table_query:
        return custom_response(
            {"status": "error", "msg": "debtor/client not found"}, 404
        )

    # get debtor from 3rd party
    data = get_debtor_limits_from_third_party(
        joined_table_query[0], joined_table_query[1]
    )

    if "status_code" in data and data["status_code"] == 200:
        # PATCH DATA
        req_client_debtor = {
            "current_ar": data["current_ar"],
            "credit_limit": data["debtor_limit"],
            "days_1_30": str(data["current_age"]),
            "days_31_60": str(data["age_31_60_days"]),
            "days_61_90": str(data["age_61_90_days"]),
            "days_91_120": str(data["age_91_120_days"]),
        }

        client_debtor = ClientDebtor.query.filter_by(
            debtor_id=debtor_id, client_id=client_id, is_deleted=False
        )
        if not client_debtor:
            return custom_response(
                {"status": "error", "msg": "client_debtor not found"}, 404
            )

        data, error = client_debtor_schema.load(req_client_debtor, partial=True)
        if error:
            return custom_response(error, 400)

        client_debtor.update(data)

    if "status_code" in data:
        del data["status_code"]

    # GET CLIENT AND DEBTOR NAME
    client_name = joined_table_query[3]
    debtor_name = joined_table_query[4]
    data.update({"client_name": client_name, "debtor_name": debtor_name})
    db.session.commit()

    return custom_response(data, 200)


def get_soa_by_debtor(debtor_id=None, client_id=None):
    soa_info = []
    reference_ids = []
    msg = "soa not found"
    client = Client.query.filter_by(
            id=client_id, is_deleted=False
        ).first()

    if not client:
        return {
                "status_code": 404, 
                "msg": "client not found",
                "data": soa_info,
                "reference_ids": reference_ids
        }

    invoices = Invoice.query.filter_by(
        debtor=debtor_id, client_id=client_id, is_deleted=False
    )

    # total number of invoices
    total_invoices = invoices.count()

    invoices = (
        invoices.with_entities(Invoice.soa_id)
        .group_by(Invoice.soa_id)
        .order_by(Invoice.id.asc())
        .all()
    )

    if invoices:
        for invoice in invoices:
            soa = SOA.query.filter_by(id=invoice, is_deleted=False).first()
            reference_id = f"{client.ref_client_no}-SOAID{soa.soa_ref_id}"
            reference_ids.append(reference_id)
            soa_info.append({
                "reference_id": reference_id,
                "id": soa.id,
                "status": soa.status.value
            })

    if soa_info:
        msg = "soa found"

    return {
        "status_code": 200,
        "msg": msg,
        "data": soa_info,
        "reference_ids": reference_ids,
        "total_invoices": total_invoices
    }
    

@Auth.auth_required
def get_duplicate_debtors(debtor_id):
    """
    Get Duplicate Debtors(LC-1934)
    """
    client_id = request.args.get("client_id", None)
    search = request.args.get("search", None, type=str)

    if not client_id:
        return custom_response(
            {
                "status": "error", 
                "msg": "client id is required"
            },
            400,
        )

    debtor = Debtor.get_one_based_off_control_accounts(debtor_id, client_id=client_id)
    if not debtor:
        return custom_response({"status": "error", "msg": "debtor not found"}, 404)
    if debtor.is_active == False:
            return custom_response({"status": "error", "msg": "Debtor is Inactive"}, 404)

    duplicate_debtors = debtor.get_duplicate_debtors(
        client_id=client_id, search=search
    )
    duplicate_debtors_data = duplicate_debtors_schema.dump(
        duplicate_debtors, many=True
    ).data

    return custom_response(duplicate_debtors_data, 200)


def merge_duplicate_debtors(debtor_id):
    """
    Merge Duplicate Debtors(LC-1934)
    """
    client_id = request.args.get("client_id", None)
    if not client_id:
        return custom_response(
            {
                "status": "error", 
                "msg": "client id is required"
            },
            400,
        )
    
    req_data = request.get_json()
    merge_debtors_id = req_data.get("merge_debtors", [])

    keep_debtor = Debtor.get_one_based_off_control_accounts(debtor_id, client_id=client_id)
    if not keep_debtor:
        return custom_response({"status": "error", "msg": "debtor not found"}, 404)

    can_merge_debtors = False
    approval_limit = Decimal(0)
    # Allow RM, FOM, CRO, COO - except the basic AE - to merge debtors(LC-2268)
    fom_approval_limit = Decimal(1000000)
    rm_approval_limit = Decimal(500000)
    coo_approval_limit = Decimal(1000000)
    cro_approval_limit = Decimal(999999999)

    # user permissions
    user_permissions = Permissions.get_user_role_permissions()
    # user role
    user_role = user_permissions["user_role"]

    if (
        user_role.lower() == Permissions.ae
        and user_permissions["user_permissions"]["approval_limit"]
    ):
        approval_limit = Decimal(
            list(user_permissions["user_permissions"]["approval_limit"].keys())[0]
        )
    
    misc_permissions = (
        user_permissions["user_permissions"]["misc_permissions"]
        if "misc_permissions" in user_permissions["user_permissions"]
        else None
    )
    # LC-2268: checking, if user(RM, FOM, CRO, COO) has permission 'can_merge_debtors'
    if (
        misc_permissions
        and "can_merge_debtors" in misc_permissions
        and misc_permissions["can_merge_debtors"]
    ) and (
        approval_limit in [fom_approval_limit, rm_approval_limit, coo_approval_limit, cro_approval_limit]
    ):
        can_merge_debtors = True

    if not can_merge_debtors:
        return custom_response(
            {
                "status": "error", 
                "msg": "You do not have permission to merge debtors"
            },
            403,
        )

    merge_debtors = Debtor.query.join(ClientDebtor).filter(
        ClientDebtor.is_deleted == False,
        Debtor.is_deleted == False,
        ClientDebtor.client_id == client_id,
        Debtor.id.in_(merge_debtors_id),
    ).with_entities(Debtor.id).all()
    
    if not merge_debtors:
        return custom_response(
            {
                "status": "error",
                "msg": f"Duplicate debtors not found for FC ID {keep_debtor.id}",
            },
            404,
        )
    
    # checking, if have merge debtors then merge invoices and soft delete clientdebtor
    # keep_debtor.merge_duplicate_debtors_invoice(client_id=client_id, merge_debtors=merge_debtors)
    from src.cli.merge_duplicate_debtors import MergeDuplicateDebtors
    MergeDuplicateDebtors(
        db=db, debtor_id=debtor_id, debtor_ref_key=keep_debtor.ref_key, merge_debtors=merge_debtors
    ).run()

    # get logged user email
    user_email = Permissions.get_user_details()["email"]

    approvals_history_data = {
        "key": "merged_debtors_at",
        "value": datetime.utcnow(),
        "user": user_email,
        "attribute": json.dumps(merge_debtors),
        "debtor_id": keep_debtor.id,
    }
    approvals_history = DebtorApprovalsHistory(approvals_history_data)
    approvals_history.save()

    return custom_response(
        {"status": "success", "msg": "Duplicate Debtors are merged successfully"}, 200
    )


@Auth.auth_required
def get_approval_history(debtor_id):
    """
    Get Debtor's approval history
    """
    debtor = Debtor.get_one_based_off_control_accounts(debtor_id)

    if not debtor:
        return custom_response({"status": "error", "msg": "debtor not found"}, 404)

    approvals_history = debtor.approvals_history()

    return custom_response(approvals_history, 200)

@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def get_collection_notes(debtor_id):
    """
    Get Debtor's collection notes
    """
    client_id = request.args.get("client_id", 0, type=int)
    if not client_id:
        return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    debtor = Debtor.get_one_based_off_control_accounts(debtor_id, client_id)

    if not debtor:
        return custom_response({"status": "error", "msg": "debtor not found"}, 404)

    collection_notes = debtor.collection_notes(client_id)

    return custom_response(collection_notes, 200)

@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.collection_notes)
def get_cn_approval_history(debtor_id):
    """
    Get Debtor's collection notes approval history
    """
    client_id = request.args.get("client_id", 0, type=int)
    if not client_id:
        return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    debtor = Debtor.get_one_based_off_control_accounts(debtor_id, client_id)

    if not debtor:
        return custom_response({"status": "error", "msg": "debtor not found"}, 404)

    approval_history = debtor.cn_approvals_history(client_id)

    return custom_response(approval_history, 200)
    