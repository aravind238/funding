from flask import request
from src.models import *
import datetime as dt
from decimal import Decimal
from src import db
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import *

disbursements_schema = DisbursementsSchema()
reserve_release_disbursements_schema = ReserveReleaseDisbursementsSchema()


@Auth.auth_required
def create():
    """
    Create Disbursements Function
    """
    try:
        req_data = request.get_json()
        reserve_release_id = req_data.get("reserve_release_id", None)
        soa_id = req_data.get("soa_id", None)
        outstanding_amount = Decimal(0)
        ref_type = None

        # both soa_id, reserve_release_id = None
        if (not soa_id) and (not reserve_release_id):
            return custom_response(
                {
                    "status": "error",
                    "msg": "soa_id/ reserve_release_id is required",
                },
                400,
            )

        # payee_id
        if "payee_id" not in req_data:
            return custom_response(
                {
                    "status": "error",
                    "msg": "payee_id is required",
                },
                400,
            )

        # checking, if payee exists
        payee = Payee.query.filter_by(
            id=req_data.get("payee_id"), is_deleted=False
        ).first()
        if not payee:
            return custom_response({"status": "error", "msg": "payee not found"}, 404)

        if not payee.is_active:
            return custom_response({"status": "error", "msg": "payee is not active"}, 400)

        # reserve_release_id
        if reserve_release_id:
            reserve_release = ReserveRelease.query.filter_by(
                id=reserve_release_id, is_deleted=False
            ).first()
            if not reserve_release:
                return custom_response(
                    {"status": "error", "msg": "reserve_release not found"}, 404
                )

            # get client id from reserve release
            req_data["client_id"] = reserve_release.client.id
            # ref_type for reserve_release
            req_data["ref_type"] = "reserve_release"
            req_data["ref_id"] = reserve_release.id

            # cal outstanding amount
            cal_disbursement_total_fees = reserve_release.cal_disbursement_total_fees()
            outstanding_amount = cal_disbursement_total_fees["outstanding_amount"]

        # soa_id
        if soa_id:
            soa = SOA.query.filter_by(id=soa_id, is_deleted=False).first()
            if not soa:
                return custom_response({"status": "error", "msg": "soa not found"}, 404)

            # get client id from soa
            req_data["client_id"] = soa.client.id
            # ref_type for soa
            req_data["ref_type"] = "soa"
            req_data["ref_id"] = soa.id

            # cal outstanding amount
            cal_disbursement_total_fees = soa.cal_disbursement_total_fees()
            outstanding_amount = cal_disbursement_total_fees["outstanding_amount"]

        data, error = disbursements_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        # checking, if amount is not 0 or less than 0
        if "amount" in data and data["amount"] <= 0:
            amount = f"${data['amount']}"
            if data["amount"] < 0:
                amount = f"-${abs(data['amount'])}"
            return custom_response(
                {"status": "error", "msg": f"Amount cannot be {amount}"}, 400
            )

        # Get client payee
        client_payee = ClientPayee.query.filter_by(
            is_deleted=False,
            payee_id=payee.id,
            client_id=data["client_id"],
        ).first()
        if client_payee:
            ref_type = client_payee.ref_type.value

        # client settings
        client_settings = ClientSettings.query.filter_by(
            client_id=data["client_id"], is_deleted=False
        ).first()
        # checking, if client settings exist
        if client_settings:
            # for same_day_ach
            if (
                "payment_method" in data
                and data["payment_method"].value == "same_day_ach"
            ):
                data["client_fee"] = Decimal(client_settings.same_day_ach_fee)

            # for wire
            if "payment_method" in data and data["payment_method"].value == "wire":
                data["client_fee"] = Decimal(client_settings.wire_fee)
        
            # for third party
            if ref_type == "payee":
                data["third_party_fee"] = Decimal(client_settings.third_party_fee)
            else:
                data["third_party_fee"] = Decimal(0)
        
        # checking, if data not has client_fee
        if "client_fee" not in data:
            data["client_fee"] = Decimal(0)

        # checking, if data not has third_party_fee
        if "third_party_fee" not in data:    
            data["third_party_fee"] = Decimal(0)
        
        # cal net amount
        net_amount = Decimal(data["amount"]) - (
            Decimal(data["client_fee"]) + Decimal(data["third_party_fee"])
        )

        # checking, if net amount is negative or 0
        if net_amount <= 0:
            msg = f"net amount -${abs(net_amount)} cannot be negative"
            if net_amount == 0:
                msg = f"net amount must be greater than ${abs(net_amount)}"

            return custom_response(
                {
                    "status": "error",
                    "msg": msg,
                },
                400,
            )

        # checking, if amount is greater than outstanding amount
        if Decimal("%.2f" % data["amount"]) > outstanding_amount:
            return custom_response(
                {
                    "status": "error",
                    "msg": f"amount ${Decimal(data['amount'])} is more than outstanding amount ${outstanding_amount}",
                },
                400,
            )

        disbursements = Disbursements(data)
        disbursements.save()

        # save reserve_release_disbursements
        if (reserve_release_id) and (soa_id is None) and (disbursements.id is not None):
            reserve_release_disbursements_data = {
                "disbursements_id": disbursements.id,
                "reserve_release_id": reserve_release_id,
            }
            reserve_release_disbursements = ReserveReleaseDisbursements(
                reserve_release_disbursements_data
            )
            reserve_release_disbursements.save()

            # update reserve release disbursement amount on disbursement add
            disbursement_total_fees = reserve_release.cal_disbursement_total_fees()
            reserve_release.disbursement_amount = Decimal(
                disbursement_total_fees["advance_subtotal"]
            ) - Decimal(disbursement_total_fees["total_fees_asap"])
            reserve_release.save()

        data = disbursements_schema.dump(disbursements).data
        data["reserve_release_id"] = reserve_release_id
        data["net_amount"] = disbursements.cal_net_amount()

        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Disbursements
    """
    try:
        disbursements = Disbursements.get_all_disbursements()
        data = disbursements_schema.dump(disbursements, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)


@Auth.auth_required
def get_one(disbursements_id):
    """
    Get A Disbursement
    """
    try:
        disbursements = Disbursements.get_one_disbursement(disbursements_id)
        if not disbursements:
            return custom_response(
                {"status": "error", "msg": "disbursements not found"}, 404
            )
        data = disbursements_schema.dump(disbursements).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)


@Auth.auth_required
def update(disbursements_id):
    """
    Update A Disbursement
    """
    req_data = request.get_json()
    reserve_release_id = None
    soa_id = None
    third_party_fee = Decimal(0)
    outstanding_amount = Decimal(0)
    request_status = None
    ref_type = None
    is_request_approved = False # for soa/reserve release status 

    disbursements = Disbursements.get_one_disbursement(disbursements_id)
    if not disbursements:
        return custom_response(
            {"status": "error", "msg": "disbursements not found"}, 404
        )

    soa_id = disbursements.soa_id

    # get reserve release if soa_id null
    if not disbursements.soa_id:
        disbursement_reserve_release = ReserveReleaseDisbursements.query.filter(
            ReserveReleaseDisbursements.disbursements_id == disbursements.id, 
            ReserveReleaseDisbursements.is_deleted == False
        ).first()
        if disbursement_reserve_release:
            reserve_release_id = disbursement_reserve_release.reserve_release_id
    
    # both soa_id, reserve_release_id = None
    if (not soa_id) and (not reserve_release_id):
        return custom_response(
            {
                "status": "error",
                "msg": "soa_id/ reserve_release_id is required",
            },
            400,
        )

    # payee id
    payee_id = (
        req_data["payee_id"] if "payee_id" in req_data else disbursements.payee_id
    )

    # checking payee id is not none
    if not payee_id:
        return custom_response(
            {
                "status": "error",
                "msg": "payee_id is required",
            },
            400,
        )

    # checking, if payee exists
    payee = Payee.query.filter_by(id=payee_id, is_deleted=False).first()
    if not payee:
        return custom_response({"status": "error", "msg": "payee not found"}, 404)
    if not payee.is_active:
        return custom_response({"status": "error", "msg": "payee is not active"}, 400)

    # reserve_release_id
    if reserve_release_id:
        reserve_release = ReserveRelease.query.filter_by(
            id=reserve_release_id, is_deleted=False
        ).first()
        if not reserve_release:
            return custom_response(
                {"status": "error", "msg": "reserve_release not found"}, 404
            )

        if reserve_release.status.value == "completed":
            return custom_response(
                {"status": "error", "msg": "Reserve Release is already completed"}, 400
            )

        # get client id from reserve release
        req_data["client_id"] = reserve_release.client.id
        # reserve release status
        request_status = reserve_release.status.value
        # cal outstanding amount
        cal_disbursement_total_fees = reserve_release.cal_disbursement_total_fees()
        outstanding_amount = cal_disbursement_total_fees["outstanding_amount"]

    # soa_id
    if soa_id:
        soa = SOA.query.filter_by(id=soa_id, is_deleted=False).first()
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404)

        if soa.status.value == "completed":
            return custom_response(
                {"status": "error", "msg": "SOA is already completed"}, 400
            )

        # get client id from soa
        req_data["client_id"] = soa.client.id
        # soa status
        request_status = soa.status.value
        # cal outstanding amount
        cal_disbursement_total_fees = soa.cal_disbursement_total_fees()
        outstanding_amount = cal_disbursement_total_fees["outstanding_amount"]
        
    # when soa/reserve release has status == approved
    if request_status == "approved":
        is_request_approved = True

    if req_data:
        data, error = DisbursementsSchema(
            exclude=[
                "client_id",
                "soa_id",
                "ref_type",
                "ref_id",
            ]
        ).load(req_data, partial=True)

        # checking, if soa/reserve release is status == approved
        if is_request_approved:
            # if soa/reserve release is approved, disbursement can only be is_reviewed
            data, error = DisbursementsSchema(
                exclude=[
                    "payment_method",
                    "client_fee",
                    "amount",
                    "third_party_fee",
                    "payee_id",
                    "client_id",
                    "soa_id",
                    "ref_type",
                    "ref_id",
                ]
            ).load(req_data, partial=True)
        if error:
            return custom_response(error, 400)
                
        # checking, if soa/reserve release not approved
        if not is_request_approved:
            # checking, if amount is 0 or less than 0
            if "amount" in data and data["amount"] <= 0:
                amount = f"${data['amount']}"
                if data["amount"] < 0:
                    amount = f"-${abs(data['amount'])}"
                return custom_response(
                    {"status": "error", "msg": f"Amount cannot be {amount}"}, 400
                )
            
            # Get client payee
            client_payee = ClientPayee.query.filter_by(
                is_deleted=False,
                payee_id=payee.id,
                client_id=disbursements.client_id,
            ).first()
            if client_payee:
                ref_type = client_payee.ref_type.value

            # client settings
            client_settings = ClientSettings.query.filter_by(
                client_id=disbursements.client_id, is_deleted=False
            ).first()

            if client_settings:
                # for same_day_ach
                if (
                    "payment_method" in data
                    and data["payment_method"].value == "same_day_ach"
                ):
                    data["client_fee"] = Decimal(client_settings.same_day_ach_fee)

                # for wire
                if "payment_method" in data and data["payment_method"].value == "wire":
                    data["client_fee"] = Decimal(client_settings.wire_fee)

                # for third party
                if ref_type == "payee":
                    data["third_party_fee"] = Decimal(client_settings.third_party_fee)
                    third_party_fee = Decimal(client_settings.third_party_fee)
                else:
                    data["third_party_fee"] = Decimal(0)
                    third_party_fee = Decimal(0)
            
            # checking, if data not has client_fee, then get from db
            if "client_fee" not in data:
                data["client_fee"] = Decimal(disbursements.client_fee)

            # checking, if data not has third_party_fee, then get from db
            if "third_party_fee" not in data:    
                data["third_party_fee"] = Decimal(disbursements.third_party_fee)
                third_party_fee = Decimal(disbursements.third_party_fee)
        
            amount = Decimal(req_data.get("amount", disbursements.amount))

            # cal net amount
            net_amount = amount - (
                Decimal(data["client_fee"]) + Decimal(third_party_fee)
            )
            
            # checking, if net amount is negative or 0
            if net_amount <= 0:
                msg = f"net amount -${abs(net_amount)} cannot be negative"
                if net_amount == 0:
                    msg = f"net amount must be greater than ${abs(net_amount)}"

                return custom_response(
                    {
                        "status": "error",
                        "msg": msg,
                    },
                    400,
                )

            # client_fee
            if req_data.get("client_fee"):
                # if new client_fee is less than old client_fee then add the difference to outstanding amount
                if Decimal(data["client_fee"]) < Decimal(disbursements.client_fee):
                    outstanding_amount = outstanding_amount + (
                        Decimal(disbursements.client_fee)
                        - Decimal(data["client_fee"])
                    )

                # if new client_fee is greater than old client_fee then minus the difference from outstanding amount
                if Decimal(data["client_fee"]) > Decimal(disbursements.client_fee):
                    outstanding_amount = outstanding_amount - (
                        Decimal(data["client_fee"]) - Decimal(disbursements.amount)
                    )

            # third_party_fee
            if third_party_fee and third_party_fee > 0:
                # if new third_party_fee is less than old third_party_fee then add the difference to outstanding amount
                if Decimal(data["third_party_fee"]) < Decimal(
                    disbursements.third_party_fee
                ):
                    outstanding_amount = outstanding_amount + (
                        Decimal(disbursements.third_party_fee)
                        - Decimal(data["third_party_fee"])
                    )

                # if new third_party_fee is greater than old third_party_fee then minus the difference from outstanding amount
                if Decimal(data["third_party_fee"]) > Decimal(
                    disbursements.third_party_fee
                ):
                    outstanding_amount = outstanding_amount - (
                        Decimal(data["third_party_fee"])
                        - Decimal(disbursements.third_party_fee)
                    )

            # amount
            if req_data.get("amount"):
                # if new amount is less than old amount then add the difference to outstanding amount
                if float(req_data.get("amount")) < float(disbursements.amount):
                    amount_diff = float(
                        "{0:.2f}".format(
                            float(disbursements.amount) - float(req_data.get("amount"))
                        )
                    )
                    outstanding_amount = float(outstanding_amount) + float(amount_diff)

                # if new amount is greater than old amount then minus the difference from outstanding amount
                if float(req_data.get("amount")) > float(disbursements.amount):
                    amount_diff = float(
                        "{0:.2f}".format(
                            float(req_data.get("amount")) - float(disbursements.amount)
                        )
                    )
                    outstanding_amount = float(outstanding_amount) - float(amount_diff)

                # checking, if outstanding amount is negative
                if outstanding_amount < 0:
                    # format to 2 decimal
                    format_outstanding_amount = "{0:.2f}".format(
                        abs(outstanding_amount)
                    )
                    return custom_response(
                        {
                            "status": "error",
                            "msg": f"outstanding amount will be -${format_outstanding_amount}",
                        },
                        400,
                    )
        
        disbursements.update(data)

    # reserve_release_disbursements
    if (reserve_release_id) and (soa_id is None) and (disbursements.id is not None):
        get_reserve_release_disbursements = ReserveReleaseDisbursements.query.filter_by(
            disbursements_id=disbursements.id,
            reserve_release_id=reserve_release_id,
            is_deleted=False,
        ).first()

        # update reserve release
        if get_reserve_release_disbursements:

            reserve_release_disbursements_data = {
                "disbursements_id": disbursements.id,
                "reserve_release_id": reserve_release_id,
                "id": get_reserve_release_disbursements.id,
            }

            data, error = reserve_release_disbursements_schema.load(
                reserve_release_disbursements_data, partial=True
            )
            if error:
                return custom_response(error, 400)
            get_reserve_release_disbursements.update(data)
        else:
            # save reserve release
            reserve_release_disbursements_data = {
                "disbursements_id": disbursements.id,
                "reserve_release_id": reserve_release_id,
            }
            reserve_release_disbursements = ReserveReleaseDisbursements(
                reserve_release_disbursements_data
            )
            reserve_release_disbursements.save()

            # update reserve release disbursement amount on disbursement update
            disbursement_total_fees = reserve_release.cal_disbursement_total_fees()
            reserve_release.disbursement_amount = Decimal(
                disbursement_total_fees["advance_subtotal"]
            ) - Decimal(disbursement_total_fees["total_fees_asap"])
            reserve_release.save()

    data = disbursements_schema.dump(disbursements).data
    data["reserve_release_id"] = reserve_release_id
    data["net_amount"] = disbursements.cal_net_amount()

    return custom_response(data, 200)


@Auth.auth_required
def delete(disbursements_id):
    """
    Delete A Disbursement
    """
    try:
        disbursements = Disbursements.get_one_disbursement(disbursements_id)
        if not disbursements:
            return custom_response(
                {"status": "error", "msg": "disbursements not found"}, 404
            )

        reserve_release = (
            disbursements.reserve_release[0] if disbursements.reserve_release else None
        )

        # disbursements.is_deleted = True
        # disbursements.deleted_at = dt.datetime.utcnow()

        disbursements.delete()

        # update reserve release disbursement amount on disbursement delete
        if reserve_release:
            disbursement_total_fees = reserve_release.cal_disbursement_total_fees()
            reserve_release.disbursement_amount = Decimal(
                disbursement_total_fees["advance_subtotal"]
            ) - Decimal(disbursement_total_fees["total_fees_asap"])
            reserve_release.save()

        return custom_response(
            {"status": "success", "msg": "Disbursement deleted"}, 202
        )

    except Exception as e:
        return custom_response({"status": "error", "msg": "Exception: " + str(e)}, 404)
