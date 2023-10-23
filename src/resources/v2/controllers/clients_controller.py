from src.middleware.authentication import Auth
from src.models import *
from src import db
from src.resources.v2.helpers import (
    custom_response,
    ClientDetails,
    third_party_sync_by_client,
    CalculateClientbalances,
)
import io
import csv
from datetime import datetime
from src.resources.v2.models import *
from flask import request, make_response
import pandas as pd

# from src.models import Client, ClientListing
import uuid
from src.resources.v2.schemas import *
from decimal import Decimal
from src.middleware.permissions import Permissions

client_schema = ClientSchema()
disclaimer_only_schema = DisclaimerOnlySchema()


@Auth.auth_required
def create():
    """
    Create Client Function
    """
    try:
        req_data = request.get_json()
        data, error = client_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        client = Client(data)
        client.uuid = uuid.uuid4().hex
        client.save()

        data = client_schema.dump(client).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({f"status: error, msg: Exception {e}"}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Client
    """
    try:
        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        ordering = request.args.get("ordering", None, type=str)
        search = request.args.get("search", None, type=str)
        control_account = request.args.get("control_account", None, type=str)
        active = request.args.get("active", None, type=str)

        if page > 0:
            data = ClientListing.get_paginated_clients(
                page=page,
                rpp=rpp,
                ordering=ordering,
                search=search,
                control_account=control_account,
                active=active,
            )
        else:
            data = ClientListing.get_all()

        if data is None:
            data = []

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f"status: error, msg: Exception {e}"}, 404)


@Auth.auth_required
def get_one(client_id):
    """
    Get A Client
    """
    try:
        client = Client.get_one_based_off_control_accounts(client_id)
        if not client:
            return custom_response({"status": "error", "msg": "client not found"}, 404)

        data = client_schema.dump(client).data
        clients_control_account = client.clients_control_account
        if clients_control_account:
            control_account_name = clients_control_account[0].control_account.name
            control_account_currency = clients_control_account[0].control_account.currency
            control_account_country = clients_control_account[0].control_account.country
        else:
            control_account_name = None
            control_account_currency = None
            control_account_country = None

        data.update(
            {
                "control_account_name": control_account_name,
                "currency": control_account_currency,
                "country": control_account_country,
            }
        )
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f"status: error, msg: Exception {e}"}, 404)


@Auth.auth_required
def update(client_id):
    """
    Update A Client
    """
    try:
        req_data = request.get_json()

        # # ToDo: fix this part
        # if req_data['uuid']:
        #   return custom_response({'status': 'error', 'msg': 'something went wrong'}, 404)

        client = Client.get_one_based_off_control_accounts(client_id)
        if not client:
            return custom_response({"status": "error", "msg": "client not found"}, 404)

        if req_data:
            data, error = client_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            client.update(data)

        data = client_schema.dump(client).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f"status: error, msg: Exception {e}"}, 404)


@Auth.auth_required
def delete(client_id):
    """
    Delete A Client
    """
    try:
        client = Client.get_one_based_off_control_accounts(client_id)
        if not client:
            return custom_response({"status": "error", "msg": "client not found"}, 404)

        # client.is_deleted = True
        # client.deleted_at = datetime.utcnow()

        client.delete()
        return custom_response({"status": "error", "msg": "Client deleted"}, 202)
    except Exception as e:
        return custom_response({f"status: error, msg: Exception {e}"}, 404)


@Auth.auth_required
def get_clients_control_account(client_id):
    """
    Get control accounts based off client id

    Args:
        client_id (int)

    Returns:
        control_accounts
    """
    
    # control accounts
    business_control_accounts = Permissions.get_business_settings()["control_accounts"]
    
    control_accounts_query = ControlAccount.query.join(ClientControlAccounts).filter(
        ClientControlAccounts.is_deleted == False,
        ControlAccount.id == ClientControlAccounts.control_account_id,
        ClientControlAccounts.client_id == client_id,
        ControlAccount.name.in_(business_control_accounts),
    )

    control_account = (
        ControlAccountSchema().dump(control_accounts_query, many=True).data
    )
    if not control_account:
        return custom_response(
            {"status": "error", "msg": "Control Account not found"}, 404
        )

    return custom_response(control_account, 200)


@Auth.auth_required
def get_client_details(client_id):
    """
    get client details
    """
    try:
        soa_id = request.args.get("soa_id", None, type=int)
        reserve_release_id = request.args.get("reserve_release_id", None, type=int)

        client = Client.get_one_based_off_control_accounts(client_id)
        if not client:
            return custom_response({"status": "error", "msg": "client not found"}, 404)

        # third party sync based off client
        third_party_sync = third_party_sync_by_client(client=client)

        request_type = None
        if soa_id and reserve_release_id is None:
            soa = SOA.query.filter_by(
                is_deleted=False, id=soa_id, client_id=client_id
            ).first()
            if not soa:
                return custom_response({"status": "error", "msg": "SOA not found"}, 404)
            request_type = soa

        if reserve_release_id and soa_id is None:
            reserve_release = ReserveRelease.query.filter_by(
                is_deleted=False, id=reserve_release_id, client_id=client_id
            ).first()
            if not reserve_release:
                return custom_response(
                    {"status": "error", "msg": "Reserve Release not found"}, 404
                )
            request_type = reserve_release

        get_client_details = ClientDetails(client, request_type=request_type)
        return_res = get_client_details.get_details

        # Don't need to pull debtors
        if "debtors" in return_res:
            del return_res["debtors"]

        # Adding in sync response
        return_res["third_party_sync"] = third_party_sync

        return custom_response(return_res, 200)
    except Exception as e:
        print(f"Get client details Exception:- {e}")
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def calculate_client_balances():
    try:
        soa_id = request.args.get("soa_id", None)
        reserve_release_id = request.args.get("reserve_release_id", None)
        invoice_total = request.args.get("invoice_total", Decimal(0), type=Decimal)
        client_id = request.args.get("client_id", None)
        get_client = None
        request_type = None

        # soa
        soa = SOA.query.filter_by(is_deleted=False, id=soa_id).first()
        if soa:
            get_client = soa.client_id
            request_type = soa

        # reserve release
        reserve_release = ReserveRelease.query.filter_by(
            is_deleted=False, id=reserve_release_id
        ).first()
        if reserve_release:
            get_client = reserve_release.client_id
            request_type = reserve_release

        if request_type is None:
            return custom_response(
                {"status": "error", "msg": "SOA/Reserve Release not found"}, 404
            )

        calculate_client_balances = CalculateClientbalances(
            request_type=request_type, invoice_total=invoice_total, client_id=get_client
        )

        return custom_response(
            {
                "ar_balance": calculate_client_balances.ar_balance,
                "funding_balance": calculate_client_balances.funding_balance,
                "reserve_balance": calculate_client_balances.reserve_balance,
                "preview_ar_balance": calculate_client_balances.preview_ar_balance,  # COC1
                "preview_funding_balance": calculate_client_balances.preview_funding_balance,  # COC2
                "preview_reserve_balance": calculate_client_balances.preview_reserve_balance,  # COC3
                "client_funding_balance": calculate_client_balances.client_funding_balance,  # COC4
                "client_limit_flag": calculate_client_balances.client_limit_flag,  # COC5
            }
        )
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_debtors(client_id):
    """
    get debtors
    """
    client = Client.get_one_based_off_control_accounts(client_id)
    if not client:
        return custom_response(
            {"status": "error", "msg": "client not found"}, 404
        )

    get_client_details = ClientDetails(client)

    return custom_response(get_client_details.debtors, 200)


@Auth.auth_required
def export_debtors(client_id):
    client = Client.get_one_based_off_control_accounts(client_id)
    if not client:
        return custom_response({"status": "error", "msg": "client not found"}, 404)

    # filename
    date_time = datetime.utcnow()
    filename = f"debtor_details_{date_time}.csv"

    # get debtors
    get_client_details = ClientDetails(client)
    debtors = get_client_details.debtors

    if not debtors:
        return custom_response({"status": "error", "msg": "Debtors not found"}, 404)

    debtor_name = []
    debtor_address = []
    debtor_is_new = []
    debtor_ref_key = []
    for debtor in debtors:
        name = debtor["name"]
        address = debtor["address"]
        is_new = debtor["is_new"]
        ref_key = debtor["ref_key"]

        debtor_name.append(name)
        debtor_address.append(address)
        debtor_is_new.append(is_new)
        debtor_ref_key.append(ref_key)

    df = pd.DataFrame(
        {
            "Debtor Name": debtor_name,
            "Address": debtor_address,
            "is_new": debtor_is_new,
            "Debtor key": debtor_ref_key,
        }
    )

    response = make_response(df.to_csv(index=False))
    response.headers["Content-Disposition"] = 'attachment; filename="{}"'.format(
        filename
    )
    response.headers["Content-Type"] = "text/csv"
    response.headers["Access-Control-Expose-Headers"] = "content-disposition"

    return response
    

@Auth.auth_required
def get_client_settings(client_id):
    """
    get client settings
    """    
    client = Client.get_one_based_off_control_accounts(client_id)
    if not client:
        return custom_response(
            {"status": "error", "msg": "client not found"}, 404
        )

    get_client_details = ClientDetails(client)

    return custom_response(get_client_details.client_settings, 200)


@Auth.auth_required
def get_client_disclaimers(client_id):
    """
    get client disclaimers
    """    
    client = Client.get_one_based_off_control_accounts(client_id)
    if not client:
        return custom_response(
            {"status": "error", "msg": "client not found"}, 404
        )
    
    # get client's disclaimer
    client_disclaimer = client.get_disclaimer()          

    return custom_response(client_disclaimer, 200)
