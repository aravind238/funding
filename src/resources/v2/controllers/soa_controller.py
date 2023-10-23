from flask import request, json
from src.models import *
from datetime import datetime
import os
from decimal import Decimal
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import (
    SendMails,
    custom_response,
    PermissionExceptions,
    SOAPDF,
    generate_soa_lcra_csv,
    SOADetails,
    principal_settings,
)
from src import db
from src.resources.v2.schemas import *
import hashlib

soa_schema = SOASchema()
approvals_history_schema = ApprovalsHistorySchema()


@Auth.auth_required
def create():
    """
    Create SOA Function
    """
    try:
        req_data = request.get_json()
        data, error = soa_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        # check, if client exists
        client = Client.get_one_based_off_control_accounts(data["client_id"])
        if not client:
            return custom_response(
                {"status": "error", "msg": f'client - {data["client_id"]} not found'},
                404,
            )
        if client.is_active == False:
            return custom_response({"status": "error", "msg": "Client is Inactive"}, 404)

        # USER_ACTIVITY
        get_user_detail = Permissions.get_user_details()
        user_email = get_user_detail["email"]
        # soa.created_by = user_email

        # calculate ref_id
        get_total_value = SOA.query.filter_by(client_id=req_data["client_id"]).count()
        soa = SOA(data)
        soa.soa_ref_id = get_total_value + 1
        soa.last_processed_at = datetime.utcnow()
        soa.save()

        data = soa_schema.dump(soa).data

        # approvals_history: soa created
        get_soa_details = SOADetails(soa=soa)
        save_attribute_data = get_soa_details.soa_dict
        business_settings = soa.get_business_settings_disclaimer()
        business_settings_data = {}

        if (
            business_settings
            and isinstance(business_settings, list)
            and "text" in business_settings[0]
        ):
            business_settings_data.update({
                "disclaimer_text": business_settings[0]["text"]
            })

        save_attribute_data.update(
            {
                "client_funds": ClientFundSchema()
                .dump(soa.client.client_funds[0])
                .data,
                "client": get_soa_details.client,
                "client_debtors": get_soa_details.client_debtors,
                "debtors": get_soa_details.debtors,
                "participants": get_soa_details.participants,
                "client_settings": soa.soa_client_settings(),
                "business_settings": business_settings_data,
            }
        )

        approvals_history_data = {
            "key": "created_at",
            "value": datetime.utcnow(),
            "user": user_email,
            "attribute": save_attribute_data,
            "soa_id": soa.id,
        }
        approvals_history = ApprovalsHistory(approvals_history_data)
        approvals_history.save()
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All SOA
    """
    try:
        use_ref = False
        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        ordering = request.args.get("ordering", None, type=str)
        if request.path == "/requests":
            use_ref = True
        search = request.args.get("search", None, type=str)
        start_date = request.args.get("start_date", None, type=str)
        end_date = request.args.get("end_date", None, type=str)
        control_account = request.args.get("control_account", None, type=str)
        stage = request.args.get("stage", None, type=str)
        high_priority = request.args.get("high_priority", None, type=str)

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
            data = SOAListing.get_paginated_soa(
                page=page,
                rpp=rpp,
                ordering=ordering,
                search=search,
                start_date=start_date,
                end_date=end_date,
                control_account=control_account,
                stage=stage,
                use_ref=use_ref,
                high_priority=high_priority,
            )
        else:
            data = SOAListing.get_all()

        if data is None:
            data = []

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(soa_id):
    """
    Get A SOA
    """
    soa = SOA.get_one_based_off_control_accounts(soa_id)
    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    data = soa_schema.dump(soa).data

    # cal fee to client
    cal_disbursement_total_fees = soa.cal_disbursement_total_fees()
    fee_to_client = Decimal(cal_disbursement_total_fees["total_fee_to_client"])

    data.update(
        {
            "total_fee_to_client": fee_to_client,
        }
    )

    return custom_response(data, 200)


@Auth.auth_required
def update(soa_id):
    """
    Update A SOA
    """
    try:
        req_data = request.get_json()
        status_to_be_updated = req_data.get("status", None)
        # for tagging in notes
        notify_to_tagged = req_data.pop("mentions") if "mentions" in req_data else None

        client_settings = {}
        business_settings = {}

        soa = SOA.get_one_based_off_control_accounts(soa_id)
        if not soa:
            return custom_response({"status": "error", "error": "soa not found"}, 404)

        # check, if client exists
        if req_data.get("client_id", soa.client_id):
            client = Client.get_one_client(req_data.get("client_id", soa.client_id))
            if not client:
                return custom_response(
                    {
                        "status": "error",
                        "msg": f'client - {req_data.get("client_id", soa.client_id)} not found',
                    },
                    404,
                )

        # ToDo: Code commented if not needed will remove it
        # request status
        # soa_status_list = [status.value for status in SOAStatus]
        # request_status = req_data['status'] if 'status' in req_data and req_data['status'] in soa_status_list else None

        # check, if soa can be updated
        validated_request_status = Permissions.has_request_updating_permissions(
            request=soa
        )
        print("soa", validated_request_status)
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

        # user role
        get_user_role = Permissions.get_user_role_permissions()
        user_role = get_user_role["user_role"]

        # Need to get client settings and business settings before soa status updates for saving in approval history
        if status_to_be_updated:
            client_settings = soa.soa_client_settings()
            business_settings = soa.get_business_settings_disclaimer()

        # only principal can add reference number
        if soa.status.value != "draft" and "reference_number" in req_data:
            del req_data["reference_number"]

        # get history of soa approved by AE
        soa_approved = None
        if soa.status.value == "approved":
            soa_approved = (
                soa.request_approved_by_ae() if soa.request_approved_by_ae() else None
            )

        ##############################
        # Advance Amount Calculation #
        ##############################

        # invoice_total
        soa.invoice_total = (
            soa.invoice_total if soa.invoice_total is not None else Decimal(0)
        )

        # client_funds #
        discount_fees_percentage = Decimal(0)
        credit_insurance_total_percentage = Decimal(0)
        reserves_withheld_percentage = Decimal(0)

        # get client funds from approval history if soa approved by AE
        soa_client_funds = None
        if soa_approved:
            if isinstance(soa_approved.attribute, str):
                attribute_json = json.loads(soa_approved.attribute)
                soa_client_funds = attribute_json["client_funds"]

            if (
                isinstance(soa_approved.attribute, dict)
                and "client_funds" in soa_approved.attribute
                and soa_approved.attribute["client_funds"] is not None
            ):
                soa_client_funds = soa_approved.attribute["client_funds"]

        if soa_client_funds:
            if (
                "discount_fees_percentage" in soa_client_funds
                and soa_client_funds["discount_fees_percentage"] is not None
            ):
                discount_fees_percentage = Decimal(
                    soa_client_funds["discount_fees_percentage"]
                )

            if (
                "credit_insurance_total_percentage" in soa_client_funds
                and soa_client_funds["credit_insurance_total_percentage"] is not None
            ):
                credit_insurance_total_percentage = Decimal(
                    soa_client_funds["credit_insurance_total_percentage"]
                )

            if (
                "reserves_withheld_percentage" in soa_client_funds
                and soa_client_funds["reserves_withheld_percentage"] is not None
            ):
                reserves_withheld_percentage = Decimal(
                    soa_client_funds["reserves_withheld_percentage"]
                )

        # get client funds from client table if soa not approved by AE
        else:
            client_fund = ClientFund.query.filter(
                ClientFund.client_id == soa.client_id, ClientFund.is_deleted == False
            ).first()

            if client_fund.discount_fees_percentage is not None:
                discount_fees_percentage = Decimal(client_fund.discount_fees_percentage)

            if client_fund.credit_insurance_total_percentage is not None:
                credit_insurance_total_percentage = Decimal(
                    client_fund.credit_insurance_total_percentage
                )

            if client_fund.reserves_withheld_percentage is not None:
                reserves_withheld_percentage = Decimal(
                    client_fund.reserves_withheld_percentage
                )

        # calculate discount_fees
        # discount_fees_percentage = Decimal(client_fund.discount_fees_percentage) if (client_fund.discount_fees_percentage is not None) else Decimal(0)
        rounded_get_discount_fees = soa.invoice_total * discount_fees_percentage / 100
        get_discount_fees = Decimal("%.2f" % rounded_get_discount_fees)
        soa.discount_fees = get_discount_fees

        # # calculate credit_insurance_total
        # credit_insurance_total_percentage = Decimal(client_fund.credit_insurance_total_percentage) if (client_fund.credit_insurance_total_percentage is not None) else Decimal(0)
        rounded_get_credit_insurance_total = (
            soa.invoice_total * credit_insurance_total_percentage / 100
        )
        get_credit_insurance_total = Decimal(
            "%.2f" % rounded_get_credit_insurance_total
        )
        soa.credit_insurance_total = get_credit_insurance_total

        # # calculate reserves_withheld_percentage
        # reserves_withheld_percentage = Decimal(client_fund.reserves_withheld_percentage) if (client_fund.reserves_withheld_percentage is not None) else Decimal(0)
        rounded_get_reserves_withheld = (
            soa.invoice_total * reserves_withheld_percentage / 100
        )
        get_reserves_withheld = Decimal("%.2f" % rounded_get_reserves_withheld)
        soa.reserves_withheld = get_reserves_withheld

        # invoice
        invoice_total_held = Decimal(0)
        cash_reserve_release = Decimal(0)
        get_invoices = Invoice.query.filter(
            Invoice.soa_id == soa_id, Invoice.is_deleted == False
        ).all()

        if get_invoices:
            for each_invoice in get_invoices:
                # calculate invoice held in reserve
                if each_invoice.actions.value == "hold_in_reserves":
                    invoice_total_held += (
                        each_invoice.amount
                        if each_invoice.amount is not None
                        else Decimal(0)
                    )

                # calculate invoice cash reserve release
                if each_invoice.is_release_from_reserve == True:
                    cash_reserve_release += (
                        each_invoice.amount
                        if each_invoice.amount is not None
                        else Decimal(0)
                    )

            rounded_invoice_total_held = Decimal("%.2f" % invoice_total_held)
            invoice_total_held = rounded_invoice_total_held

        rounded_cash_reserve_release = Decimal("%.2f" % cash_reserve_release)
        cash_reserve_release = rounded_cash_reserve_release
        soa.invoice_cash_reserve_release = rounded_cash_reserve_release

        # get additional_cash_reserve_held
        additional_cash_reserve_held = (
            Decimal(soa.additional_cash_reserve_held)
            if bool(soa.additional_cash_reserve_held)
            else Decimal(0)
        )
        if (
            req_data
            and "additional_cash_reserve_held" in req_data
            and bool(req_data["additional_cash_reserve_held"])
        ):
            additional_cash_reserve_held = Decimal(
                req_data["additional_cash_reserve_held"]
            )
            rounded_additional_cash_reserve_held = Decimal(
                "%.2f" % additional_cash_reserve_held
            )
            additional_cash_reserve_held = rounded_additional_cash_reserve_held

        # get fee_adjustment
        fee_adjustment = (
            Decimal(soa.fee_adjustment) if soa.fee_adjustment else Decimal(0)
        )
        if (
            req_data
            and "fee_adjustment" in req_data
            and (
                isinstance(req_data["fee_adjustment"], int)
                or isinstance(req_data["fee_adjustment"], float)
                or isinstance(req_data["fee_adjustment"], Decimal)
            )
        ):
            fee_adjustment = Decimal(req_data["fee_adjustment"])
            rounded_fee_adjustment = Decimal("%.2f" % fee_adjustment)
            fee_adjustment = rounded_fee_adjustment

        # get additional_cash_reserve_release
        additional_cash_reserve_release = (
            Decimal(soa.additional_cash_reserve_release)
            if bool(soa.additional_cash_reserve_release)
            else Decimal(0)
        )
        if (
            req_data
            and "additional_cash_reserve_release" in req_data
            and bool(req_data["additional_cash_reserve_release"])
        ):
            additional_cash_reserve_release = Decimal(
                req_data["additional_cash_reserve_release"]
            )
            rounded_additional_cash_reserve_release = Decimal(
                "%.2f" % additional_cash_reserve_release
            )
            additional_cash_reserve_release = rounded_additional_cash_reserve_release

        # get adjustment_from_ae
        adjustment_from_ae = (
            Decimal(soa.adjustment_from_ae)
            if bool(soa.adjustment_from_ae)
            else Decimal(0)
        )
        if (
            req_data
            and "adjustment_from_ae" in req_data
            and bool(req_data["adjustment_from_ae"])
        ):
            adjustment_from_ae = Decimal(req_data["adjustment_from_ae"])
            rounded_adjustment_from_ae = Decimal("%.2f" % adjustment_from_ae)
            adjustment_from_ae = rounded_adjustment_from_ae

        # calculate advance total
        calculated_advance_amount = (
            soa.invoice_total
            + cash_reserve_release
            + additional_cash_reserve_release
            + adjustment_from_ae
            + fee_adjustment
        ) - (
            additional_cash_reserve_held
            + get_discount_fees
            + invoice_total_held
            + get_reserves_withheld
        )
        rounded_advance_amount = Decimal("%.2f" % calculated_advance_amount)
        soa.advance_amount = rounded_advance_amount

        # calculate subtotal discount fees
        soa.subtotal_discount_fees = soa.discount_fees - fee_adjustment

        ##################
        # Calculate Fees #
        ##################
        disbursement_total_fees = soa.cal_disbursement_total_fees()
        soa.total_fees_to_client = disbursement_total_fees["fees_to_client"]
        soa.total_third_party_fees = disbursement_total_fees["third_party_fees"]
        get_total_fee_to_client = disbursement_total_fees["total_fee_to_client"]
        get_payees = disbursement_total_fees["get_payees"]
        outstanding_amount = disbursement_total_fees["outstanding_amount"]
        high_priority_amount = disbursement_total_fees["high_priority_amount"]

        # checking, when high_priority is updated to True then if outstanding amount less than asap fees(LC-1713)
        if req_data.get("high_priority") and not soa.high_priority:
            if (outstanding_amount - high_priority_amount) < 0:
                return custom_response(
                    {
                        "status": "error",
                        "msg": f"You don’t have enough Outstanding Amount to proceed. Please modify your payee disbursement to accommodate for ASAP fee.",
                    },
                    400,
                )

        # miscellaneous_adjustment
        soa.miscellaneous_adjustment = round(
            Decimal(disbursement_total_fees["total_fee_to_client"]), 2
        )

        # get disbursement_amount #
        # (1) total_fees = total_fees_to_client + total_third_party_fees + high_priority(if true)(LC-1683)
        #     (a) total_fees_to_client (total_client_fees):
        #          • third_party_fee_total + client_fee_total
        #     (b) total_third_party_fees (total_payee_fees):
        #          • third_party_fee_total + client_fee_total
        # (2) disbursement_amount = calculated_advance_amount - total_fees

        # total_fees = Decimal(disbursement_total_fees["total_fee_to_client"])
        total_disbursement_amount = Decimal(soa.advance_amount) - Decimal(
            soa.miscellaneous_adjustment
        )
        # fixed for error 'out of range value for column' on local
        soa.disbursement_amount = Decimal("%.2f" % total_disbursement_amount)

        # checking for disabled payee LC-2315
        if get_payees:
            disabled_payees = Payee.query.filter_by(is_active=False, is_deleted=False).filter(
                Payee.id.in_(get_payees)
            ).count()
            if disabled_payees:
                return custom_response({"status": "error", "msg": "There is inactive payees in this request"}, 400)

        # USER_ACTIVITY
        approvals_history_data = {}
        if "status" in req_data:
            get_user_detail = Permissions.get_user_details()
            user_email = get_user_detail["email"]

            # Pending
            if req_data["status"] == "pending":
                approvals_history_data = {
                    "user": user_email,
                    "key": "submitted_at",
                    "value": datetime.utcnow(),
                    "soa_id": soa_id,
                }

            # approved
            if req_data["status"] == "approved":

                has_action_required = False
                if soa.had_action_required():
                    has_action_required = True
                permission_exception = PermissionExceptions(
                    request_type=soa,
                    disbursement_amount=soa.disbursement_amount,
                    has_action_required=has_action_required,
                )
                print(permission_exception.get())
                # Check, if has been already reviewed.
                if soa.status == "reviewed" and (
                    soa.disbursement_amount
                    > permission_exception.get()["approval_limit"]
                ):
                    return custom_response(
                        {
                            "msg": "Request has already been reviewed and send to desired person."
                        },
                        404,
                    )

                req_data["status"] = permission_exception.get()["status"]

                key_value = "approved_at"
                if req_data["status"] == "reviewed":
                    key_value = "reviewed_at"

                approvals_history_data = {
                    "user": user_email,
                    "key": key_value,
                    "value": datetime.utcnow(),
                    "soa_id": soa_id,
                }

                # AE can complete(funded) soa if disbursement amount = 0 (LC-1495)
                if soa.disbursement_amount == 0 and req_data["status"] == "approved":
                    req_data["status"] = "completed"

            # completed
            if req_data["status"] == "completed":
                approvals_history_data = {
                    "user": user_email,
                    "key": "funded_at",
                    "value": datetime.utcnow(),
                    "soa_id": soa_id,
                }

            # rejected
            if req_data["status"] == "rejected":
                approvals_history_data = {
                    "user": user_email,
                    "key": "rejected_at",
                    "value": datetime.utcnow(),
                    "soa_id": soa_id,
                }

        # if soa has not been updated
        if (
            not soa.is_request_updated()
            and not status_to_be_updated
            and soa.status.value in ["pending", "reviewed"]
        ):
            soa_in_db = soa_schema.dump(soa).data
            if "has_client_submitted" in soa_in_db:
                del soa_in_db["has_client_submitted"]

            if "has_action_required" in soa_in_db:
                del soa_in_db["has_action_required"]

            if "created_at" in soa_in_db:
                del soa_in_db["created_at"]

            if "updated_at" in soa_in_db:
                del soa_in_db["updated_at"]

            # md5 hash, fetched data from soa table
            soa_in_db_md5 = hashlib.md5(str(soa_in_db).encode("UTF-8")).hexdigest()

        soa_request_updated = {}
        # check for soa_ref_id
        if req_data:
            if "soa_ref_id" in req_data:
                return custom_response(
                    {"status": "error", "msg": "something went wrong"}, 404
                )

            data, error = soa_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)

            # on soa status update, update last_processed_at
            if "status" in req_data:
                data["last_processed_at"] = datetime.utcnow()

            soa.update(data)

            # to be saved in approval history
            soa_request_updated = {
                "key": "updated_at",
                "value": datetime.utcnow(),
                "soa_id": soa_id,
                "attribute": {"updated": "soa_updated"},
            }

        else:
            soa = SOA.query.filter_by(is_deleted=False, id=soa_id).first()

        request_type = ""
        request_id = ""
        data = soa_schema.dump(soa).data

        # checking, if user has role 'AE' then add in approvals history
        if (
            soa_request_updated
            and not soa.is_request_updated()
            and not status_to_be_updated
            and soa.status.value in ["pending", "reviewed"]
            and user_role
            and user_role.lower() == "ae"
        ):
            soa_updated = data
            if "has_client_submitted" in soa_updated:
                del soa_updated["has_client_submitted"]

            if "has_action_required" in soa_updated:
                del soa_updated["has_action_required"]

            if "created_at" in soa_updated:
                del soa_updated["created_at"]

            if "updated_at" in soa_updated:
                del soa_updated["updated_at"]

            # md5 hash soa updated
            soa_updated_md5 = hashlib.md5(str(soa_updated).encode("UTF-8")).hexdigest()

            # checking, if data in db(md5) != data updated(md5)
            if soa_in_db_md5 != soa_updated_md5:
                get_user_detail = Permissions.get_user_details()
                user_email = get_user_detail["email"]

                soa_request_updated.update({"user": user_email})
                approvals_history = ApprovalsHistory(soa_request_updated)
                approvals_history.save()


        # Update Verification Notes status = "submitted" after request is submitted by principal
        if "status" in req_data and req_data["status"] == "pending":
            soa.update_verification_notes()

        # Update new payee to is_new = False after BO has approved(LC-1138)
        if "status" in req_data and req_data["status"] == "completed" and get_payees:
            Payee.query.filter_by(is_new=True, is_deleted=False).filter(
                Payee.id.in_(get_payees)
            ).update({Payee.is_new: False}, synchronize_session="fetch")

            db.session.commit()

        # check for soa 'updated_at' in approval history and update to is_deleted = True after AE has approved
        if status_to_be_updated == "approved":
            ApprovalsHistory.query.filter_by(
                soa_id=soa_id, is_deleted=False, key="updated_at"
            ).update(
                {
                    ApprovalsHistory.is_deleted: True,
                    ApprovalsHistory.deleted_at: datetime.utcnow(),
                },
                synchronize_session=False,
            )
            db.session.commit()

        # approvals_history: soa update
        if approvals_history_data:
            get_soa_details = SOADetails(soa=soa)
            save_attribute_data = get_soa_details.soa_dict
            get_client_funds = ClientFundSchema().dump(soa.client.client_funds[0]).data            
            business_settings_data = {}

            if (
                business_settings
                and isinstance(business_settings, list)
                and "text" in business_settings[0]
            ):
                business_settings_data.update({
                    "disclaimer_text": business_settings[0]["text"]
                })

            # soa approved by AE
            if soa_client_funds:
                get_client_funds = soa_client_funds

            save_attribute_data.update(
                {
                    "client_funds": get_client_funds,
                    "client": get_soa_details.client,
                    "client_debtors": get_soa_details.client_debtors,
                    "debtors": get_soa_details.debtors,
                    "participants": get_soa_details.participants,
                    "client_settings": client_settings,
                    "business_settings": business_settings_data,
                }
            )

            approvals_history_data.update({"attribute": save_attribute_data})
            approvals_history = ApprovalsHistory(approvals_history_data)
            approvals_history.save()

        if data["status"] == "completed":
            # Auto generate the LCRA export file and upload to LCRA system after BO has approved(LC-1044)
            generate_soa_lcra_csv(soa_id=soa_id)
            # Auto money transfer after the BO has clicked “Set Up” checkboxes and approved the request.(LC-1668)
            soa.soa_payment_process()

        request_type = soa
        # request status
        soa_status_list = [status.value for status in SOAStatus]
        request_status = (
            req_data["status"]
            if "status" in req_data and req_data["status"] in soa_status_list
            else None
        )

        # Get organization ids
        organization_client_account = OrganizationClientAccount.query.filter_by(
            lcra_client_account_id=soa.client.lcra_client_accounts_id
        ).first()

        organization_id = None
        if organization_client_account:
            organization_id = organization_client_account.organization_id

        # get client_id
        client_id = request_type.client_id

        if request_status == "pending":
            # Mail to AE
            template_name = os.environ.get(
                "REQUEST_SUBMITTED_TO_ACCOUNT_EXECUTIVE_MAIL"
            )
            recipient_role_name = "AE"
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()

            if soa.had_client_submitted():
                # Mail to Client
                template_name = os.environ.get(
                    "CLIENT_REQUEST_APPROVED_BY_PRINCIPAL_MAIL"
                )
                recipient_role_name = "Client"
                send_mails = SendMails(
                    request_type=request_type,
                    client_id=client_id,
                    recipient_role_name=recipient_role_name,
                    template_name=template_name,
                    organization_access=organization_id,
                )
                send_mails.send_mail_request_notifications()

        if request_status == "approved":
            # Mail to Principal
            template_name = os.environ.get("REQUEST_APPROVED_TO_PRINCIPAL_MAIL")
            recipient_role_name = "Principal"
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()

            # Mail to BO
            template_name = os.environ.get("REQUEST_APPROVED_TO_BO_MAIL")
            recipient_role_name = "BO"
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()

        if request_status == "completed":
            # Mail to Principal
            template_name = os.environ.get("REQUEST_PROCESSED_TO_PRINCIPAL_MAIL")
            recipient_role_name = "Principal"
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()

            # Mail to AE
            template_name = os.environ.get("REQUEST_PROCESSED_TO_AE_MAIL")
            recipient_role_name = "AE"
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()

        if notify_to_tagged:
            # Mail to users tagged on notes
            user_emails = notify_to_tagged
            request_type = soa
            template_name = os.environ.get("USER_TAGGED_MAIL")
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                user_emails=user_emails,
                template_name=template_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_to_tagged()

        # get fee to client
        data.update(
            {
                "total_fee_to_client": get_total_fee_to_client,
            }
        )

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(soa_id):
    """
    Delete A SOA
    """
    try:
        soa = SOA.get_one_based_off_control_accounts(soa_id)
        if not soa:
            return custom_response({"status": "error", "msg": "soa not found"}, 404)

        soa.archive()

        return custom_response(
            {"status": "success", "msg": "SOA deleted successfully."}, 202
        )

    except Exception as e:
        print(str(e))
        db.session.rollback()
        raise


@Auth.auth_required
def soa_pdf(soa_id):
    # Get soa
    soa = SOA.get_one_based_off_control_accounts(soa_id)
    if soa is None:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    get_soa_pdf = SOAPDF(soa)
    return get_soa_pdf.download_pdf


@Auth.auth_required
def generate_lcra_csv(soa_id):
    # Soa
    soa_lcra_csv = generate_soa_lcra_csv(soa_id=soa_id)
    return soa_lcra_csv


@Auth.auth_required
def get_soa_details(soa_id):
    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    get_soa_details = SOADetails(soa).get()
    return custom_response({"soa": get_soa_details})


@Auth.auth_required
def get_client_settings(soa_id):
    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    soa_client_settings = soa.soa_client_settings()
    return custom_response(soa_client_settings, 200)


@Auth.auth_required
def get_disclaimer(soa_id):
    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    if soa.status.value not in ["client_draft", "client_submission", "draft"]:
        get_client_disclaimer = soa.get_saved_disclaimer()
        if isinstance(get_client_disclaimer, dict):
            get_client_disclaimer = [soa.get_saved_disclaimer()]
    else:
        get_client_disclaimer = soa.get_client_disclaimer()
    return custom_response(get_client_disclaimer, 200)


@Auth.auth_required
def get_bofa_transaction_status(soa_id):
    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    transaction_status = soa.soa_payment_status()
    return custom_response(transaction_status, 200)


@Auth.auth_required
def client_soa_pdf(soa_id):
    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    get_soa_pdf = SOAPDF(soa, html_template="client_invoice_schedule.html")
    return get_soa_pdf.download_pdf


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def get_verification_notes(soa_id):
    """
    Get SOA's verification notes
    """
    # client_id = request.args.get("client_id", 0, type=int)
    # if not client_id:
    #     return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    soa_verification_notes = soa.soa_verification_notes()
    return custom_response(soa_verification_notes, 200)


@Auth.auth_required
@Auth.has_request_permission(request_type=Permissions.verification_notes)
def get_vn_approval_history(soa_id):
    """
    Get SOA's verification notes approval history
    """
    client_id = request.args.get("client_id", 0, type=int)
    if not client_id:
        return custom_response({"status": "error", "msg": "client_id is required"}, 400)

    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    approval_history = soa.vn_approvals_history(client_id)

    return custom_response(approval_history, 200)

@Auth.auth_required
def get_invoice_supporting_documents(soa_id):
    """
    Get SOA's invoice_supporting_documents
    """
    soa = SOA.get_one_based_off_control_accounts(soa_id)

    if not soa:
        return custom_response({"status": "error", "msg": "soa not found"}, 404)

    invoice_supporting_documents = soa.soa_invoice_supporting_documents()

    return custom_response(invoice_supporting_documents, 200)
