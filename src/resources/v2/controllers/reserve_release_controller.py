from flask import request, json
from src.models import *
from datetime import datetime
from decimal import Decimal
import os
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import (
    SendMails,
    custom_response,
    PermissionExceptions,
    ReserveReleasePDF,
    generate_reserve_release_lcra_csv,
    ReserveReleaseDetails,
    principal_settings,
)
from src import db
from src.resources.v2.schemas import *
import hashlib

reserve_release_schema = ReserveReleaseSchema()


@Auth.auth_required
def create():
    """
    Create reserve release
    """
    try:
        request_data = request.get_json()

        # Don't need ref_id from frontend
        if "ref_id" in request_data:
            del request_data["ref_id"]

        data, error = reserve_release_schema.load(request_data)
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

        # get max of reserve release ref_id based of client id
        reserve_release_ref_id_max = (
            ReserveRelease.query.with_entities(ReserveRelease.ref_id)
            .filter_by(client_id=data["client_id"])
            .order_by(ReserveRelease.created_at.desc())
            .first()
        )

        data["disbursement_amount"] = Decimal(0)
        data["last_processed_at"] = datetime.utcnow()
        reserve_release = ReserveRelease(data)

        # USER_ACTIVITY
        get_user_detail = Permissions.get_user_details()
        user_email = get_user_detail["email"]

        # update ref id for reserve release(LC-1596)
        reserve_release.ref_id = 0 + 1
        if reserve_release_ref_id_max:
            reserve_release.ref_id = reserve_release_ref_id_max[0] + 1

        reserve_release.save()
        data = reserve_release_schema.dump(reserve_release).data

        # approvals_history: reserve_release created
        get_rr_details = ReserveReleaseDetails(reserve_release=reserve_release)
        save_attribute_data = get_rr_details.reserve_release_dict
        business_settings = reserve_release.get_business_settings_disclaimer()
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
                "client_funds": get_rr_details.client_funds,
                "client": get_rr_details.client,
                "client_settings": reserve_release.rr_client_settings(),
                "business_settings": business_settings_data,
            }
        )

        approvals_history_data = {
            "key": "created_at",
            "value": datetime.utcnow(),
            "user": user_email,
            "attribute": save_attribute_data,
            "reserve_release_id": reserve_release.id,
        }
        approvals_history = ApprovalsHistory(approvals_history_data)
        approvals_history.save()

        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get all reserve release
    """
    try:
        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        ordering = request.args.get("ordering", None, type=str)
        search = request.args.get("search", None, type=str)
        start_date = request.args.get("start_date", None, type=str)
        end_date = request.args.get("end_date", None, type=str)
        control_account = request.args.get("control_account", None, type=str)
        stage = request.args.get("stage", None, type=str)
        high_priority = request.args.get("high_priority", None, type=str)
        use_ref = False
        if request.path == "/requests":
            use_ref = True

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
            data = ReserveReleaseListing.get_paginated_reserve_release(
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
            data = ReserveReleaseListing.get_all()

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(reserve_release_id):
    """
    Get a reserve release
    """
    try:
        reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
        if not reserve_release:
            return custom_response(
                {"status": "error", "msg": "reserve_release not found"}, 404
            )
        data = reserve_release_schema.dump(reserve_release).data

        # cal fee to client
        cal_disbursement_total_fees = reserve_release.cal_disbursement_total_fees()
        fee_to_client = Decimal(cal_disbursement_total_fees["total_fees_asap"])

        data.update(
            {
                "total_fee_to_client": fee_to_client,
            }
        )

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(reserve_release_id):
    """
    Update a reserve release
    """
    try:
        request_data = request.get_json()
        request_advance_amount = request_data.get("advance_amount", Decimal(0))
        status_to_be_updated = request_data.get("status", None)
        business_settings = {}

        reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
        if not reserve_release:
            return custom_response(
                {"status": "error", "msg": "reserve_release not found"}, 404
            )

        # miscellaneous_adjustment
        miscellaneous_adjustment = Decimal(
            request_data.get(
                "miscellaneous_adjustment", reserve_release.miscellaneous_adjustment
            )
        )
        # discount_fee_adjustment
        discount_fee_adjustment = Decimal(
            request_data.get(
                "discount_fee_adjustment", reserve_release.discount_fee_adjustment
            )
        )
        # advance_amount
        advance_amount = Decimal(
            request_data.get("advance_amount", reserve_release.advance_amount)
        )
        # cal advance subtotal
        advance_subtotal = (
            advance_amount - miscellaneous_adjustment - discount_fee_adjustment
        )

        # check, if client exists
        if request_data.get("client_id", reserve_release.client_id):
            client = Client.get_one_client(
                request_data.get("client_id", reserve_release.client_id)
            )
            if not client:
                return custom_response(
                    {
                        "status": "error",
                        "msg": f'client - {request_data.get("client_id", reserve_release.client_id)} not found',
                    },
                    404,
                )

        # ToDo: Code commented if not needed will remove it
        # reserve release status
        # reserve_release_status_list = [status.value for status in ReserveReleaseStatus]
        # request_status = request_data['status'] if 'status' in request_data and request_data['status'] in reserve_release_status_list else None

        # check, if reserve release can be updated
        validated_request_status = Permissions.has_request_updating_permissions(
            request=reserve_release
        )
        print("reserve_release", validated_request_status)
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

        # Need to get client settings and business settings before reserve release status updates for saving in approval history
        if status_to_be_updated:
            business_settings = reserve_release.get_business_settings_disclaimer()

        # only principal can add reference number
        if (
            reserve_release.status.value != "draft"
            and "reference_number" in request_data
        ):
            del request_data["reference_number"]

        # get history of reserve_release approved by AE
        reserve_release_approved = None
        if reserve_release.status.value == "approved":
            reserve_release_approved = (
                reserve_release.request_approved_by_ae()
                if reserve_release.request_approved_by_ae()
                else None
            )

        # get client funds from approval history if reserve_release approved by AE
        # rr_client_funds = None
        # if reserve_release_approved:
        #     if isinstance(reserve_release_approved.attribute, str):
        #         attribute_json = json.loads(reserve_release_approved.attribute)
        #         rr_client_funds = attribute_json['client_funds']

        #     if isinstance(reserve_release_approved.attribute, dict) and 'client_funds' in reserve_release_approved.attribute and reserve_release_approved.attribute['client_funds'] is not None:
        #         rr_client_funds = reserve_release_approved.attribute['client_funds']

        # status updated by user
        approvals_history_data = {}
        if "status" in request_data:
            get_user_detail = Permissions.get_user_details()
            user_email = get_user_detail["email"]

            # Pending
            if request_data["status"] == "pending":
                approvals_history_data = {
                    "user": user_email,
                    "key": "submitted_at",
                    "value": datetime.utcnow(),
                    "reserve_release_id": reserve_release_id,
                }

            # approved
            if request_data["status"] == "approved":

                has_action_required = False
                if reserve_release.had_action_required():
                    has_action_required = True
                permission_exception = PermissionExceptions(
                    request_type=reserve_release,
                    disbursement_amount=reserve_release.disbursement_amount,
                    has_action_required=has_action_required,
                )
                print(permission_exception.get())
                # Check, if has been already reviewed.
                if reserve_release.status == "reviewed" and (
                    reserve_release.disbursement_amount
                    > permission_exception.get()["approval_limit"]
                ):
                    return custom_response(
                        {
                            "msg": "Request has already been reviewed and send to desired person."
                        },
                        404,
                    )

                request_data["status"] = permission_exception.get()["status"]

                key_value = "approved_at"
                if request_data["status"] == "reviewed":
                    key_value = "reviewed_at"

                approvals_history_data = {
                    "user": user_email,
                    "key": key_value,
                    "value": datetime.utcnow(),
                    "reserve_release_id": reserve_release_id,
                }

            # completed
            if request_data["status"] == "completed":
                approvals_history_data = {
                    "user": user_email,
                    "key": "funded_at",
                    "value": datetime.utcnow(),
                    "reserve_release_id": reserve_release_id,
                }

            # rejected
            if request_data["status"] == "rejected":
                approvals_history_data = {
                    "user": user_email,
                    "key": "rejected_at",
                    "value": datetime.utcnow(),
                    "reserve_release_id": reserve_release_id,
                }

        # Advance amount
        # if request_data and "advance_amount" in request_data:
        #     advance_amount = Decimal(request_advance_amount)
        # else:
        #     advance_amount = (
        #         Decimal(reserve_release.advance_amount)
        #         if reserve_release.advance_amount is not None
        #         else Decimal(0)
        #     )

        disbursement_total_fees = reserve_release.cal_disbursement_total_fees()
        get_total_fee_to_client = disbursement_total_fees["total_fees_asap"]
        get_payees = disbursement_total_fees["payee_ids"]
        outstanding_amount = disbursement_total_fees["outstanding_amount"]
        high_priority_amount = disbursement_total_fees["high_priority_amount"]

        # checking, when high_priority is updated to True then if outstanding amount less than asap fees(LC-1714)
        if (
            "high_priority" in request_data
            and request_data["high_priority"]
            and not reserve_release.high_priority
        ):
            if (outstanding_amount - high_priority_amount) < 0:
                return custom_response(
                    {
                        "status": "error",
                        "msg": f"You don’t have enough Outstanding Amount to proceed. Please modify your payee disbursement to accommodate for ASAP fee.",
                    },
                    400,
                )
            # minus high_priority fee from advance_subtotal
            advance_subtotal = advance_subtotal - high_priority_amount

        # checking, when high_priority is updated to False
        if (
            "high_priority" in request_data
            and not request_data["high_priority"]
            and reserve_release.high_priority
        ):
            # add high_priority fee in advance_subtotal
            advance_subtotal = advance_subtotal + high_priority_amount

        # calculate disbursement amount
        reserve_release.disbursement_amount = Decimal(advance_subtotal) - Decimal(
            get_total_fee_to_client
        )

        # checking for disabled payee LC-2315
        if get_payees:
            disabled_payees = Payee.query.filter_by(is_active=False, is_deleted=False).filter(
                Payee.id.in_(get_payees)
            ).count()
            if disabled_payees:
                return custom_response({"status": "error", "msg": "There is inactive payees in this request"}, 400)

        # checking, if reserve release has not been updated
        if (
            not reserve_release.is_request_updated()
            and not status_to_be_updated
            and reserve_release.status.value in ["pending", "reviewed"]
        ):
            rr_in_db = reserve_release_schema.dump(reserve_release).data
            if "has_client_submitted" in rr_in_db:
                del rr_in_db["has_client_submitted"]

            if "has_action_required" in rr_in_db:
                del rr_in_db["has_action_required"]

            if "created_at" in rr_in_db:
                del rr_in_db["created_at"]

            if "updated_at" in rr_in_db:
                del rr_in_db["updated_at"]

            # md5 hash, fetched data from reserve release table
            rr_in_db_md5 = hashlib.md5(str(rr_in_db).encode("UTF-8")).hexdigest()

        rr_request_updated = {}
        if request_data:
            data, error = ReserveReleaseSchema(
                exclude=[
                    "ref_id",
                ]
            ).load(request_data, partial=True)
            if error:
                return custom_response(error, 400)

            # on reserve release status update, update last_processed_at
            if "status" in request_data:
                data["last_processed_at"] = datetime.utcnow()

            reserve_release.update(data)

            # to be saved in approval history
            rr_request_updated = {
                "key": "updated_at",
                "value": datetime.utcnow(),
                "reserve_release_id": reserve_release_id,
                "attribute": {"updated": "reserve_release_updated"},
            }

        data = reserve_release_schema.dump(reserve_release).data

        # checking, if user has role 'AE' then add in approvals history
        if (
            rr_request_updated
            and not reserve_release.is_request_updated()
            and not status_to_be_updated
            and reserve_release.status.value in ["pending", "reviewed"]
            and user_role
            and user_role.lower() == "ae"
        ):
            rr_updated = data
            if "has_client_submitted" in rr_updated:
                del rr_updated["has_client_submitted"]

            if "has_action_required" in rr_updated:
                del rr_updated["has_action_required"]

            if "created_at" in rr_updated:
                del rr_updated["created_at"]

            if "updated_at" in rr_updated:
                del rr_updated["updated_at"]

            # md5 hash reserve release updated
            rr_updated_md5 = hashlib.md5(str(rr_updated).encode("UTF-8")).hexdigest()

            # checking, if data in db(md5) != data updated(md5)
            if rr_in_db_md5 != rr_updated_md5:
                get_user_detail = Permissions.get_user_details()
                user_email = get_user_detail["email"]

                rr_request_updated.update({"user": user_email})
                approvals_history = ApprovalsHistory(rr_request_updated)
                approvals_history.save()

        # Update new payee to is_new = False after BO has approved(LC-1138)
        if (
            "status" in request_data
            and request_data["status"] == "completed"
            and get_payees
        ):
            Payee.query.filter_by(is_new=True, is_deleted=False).filter(
                Payee.id.in_(get_payees)
            ).update({Payee.is_new: False}, synchronize_session="fetch")

            db.session.commit()

        # check for rr 'updated_at' in approval history and update to is_deleted = True after AE has approved
        if status_to_be_updated == "approved":
            ApprovalsHistory.query.filter_by(
                reserve_release_id=reserve_release_id,
                is_deleted=False,
                key="updated_at",
            ).update(
                {
                    ApprovalsHistory.is_deleted: True,
                    ApprovalsHistory.deleted_at: datetime.utcnow(),
                },
                synchronize_session=False,
            )
            db.session.commit()

        # approvals_history: reserve_release update
        if approvals_history_data:
            get_rr_details = ReserveReleaseDetails(reserve_release=reserve_release)
            save_attribute_data = get_rr_details.reserve_release_dict
            business_settings_data = {}

            if (
                business_settings
                and isinstance(business_settings, list)
                and "text" in business_settings[0]
            ):
                business_settings_data.update({
                    "disclaimer_text": business_settings[0]["text"]
                })

            # get_client_funds = ClientFundSchema().dump(reserve_release.client.client_funds[0]).data

            # # reserve_release approved by AE
            # if rr_client_funds:
            #     get_client_funds = rr_client_funds

            # save_attribute_data.update({
            #     'client_funds': get_client_funds,
            #     'client': get_rr_details.client
            # })

            save_attribute_data.update(
                {
                    "client_funds": get_rr_details.client_funds,
                    "client": get_rr_details.client,
                    "client_settings": reserve_release.rr_client_settings(),
                    "business_settings": business_settings_data,
                }
            )

            approvals_history_data.update({"attribute": save_attribute_data})
            approvals_history = ApprovalsHistory(approvals_history_data)
            approvals_history.save()

        if data["status"] == "completed":
            # Auto generate the LCRA export file and upload to LCRA system after BO has approved(LC-1044)
            generate_reserve_release_lcra_csv(reserve_release_id=reserve_release_id)
            # Auto money transfer after the BO has clicked “Set Up” checkboxes and approved the request.(LC-1668)
            reserve_release.rr_payment_process()

        # Get organization ids
        organization_client_account = OrganizationClientAccount.query.filter_by(
            lcra_client_account_id=reserve_release.client.lcra_client_accounts_id
        ).first()

        organization_id = None
        if organization_client_account:
            organization_id = organization_client_account.organization_id

        request_type = reserve_release
        # reserve release status
        reserve_release_status_list = [status.value for status in ReserveReleaseStatus]
        request_status = (
            request_data["status"]
            if "status" in request_data
            and request_data["status"] in reserve_release_status_list
            else None
        )

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

            if reserve_release.had_client_submitted():
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
def delete(reserve_release_id):
    """
    Delete a reserve release
    """
    try:
        reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
        if not reserve_release:
            return custom_response(
                {"status": "error", "msg": "reserve_release not found"}, 404
            )

        # reserve_release.is_deleted = True
        # reserve_release.deleted_at = datetime.utcnow()

        # user email
        user_email = Permissions.get_user_details()["email"]

        # approvals_history:
        get_rr_details = ReserveReleaseDetails(reserve_release=reserve_release)
        save_attribute_data = get_rr_details.reserve_release_dict
        business_settings = reserve_release.get_business_settings_disclaimer()
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
                "client_funds": get_rr_details.client_funds,
                "client": get_rr_details.client,
                "client_settings": reserve_release.rr_client_settings(),
                "business_settings": business_settings_data,
            }
        )

        approvals_history_data = {
            "key": "deleted_at",
            "value": datetime.utcnow(),
            "user": user_email,
            "attribute": save_attribute_data,
            "reserve_release_id": reserve_release.id,
        }
        
        # soft delete
        reserve_release.archive()

        approvals_history = ApprovalsHistory(approvals_history_data)
        approvals_history.save()
        return custom_response(
            {"status": "success", "msg": "Reserve release deleted"}, 202
        )

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def reserve_release_pdf(reserve_release_id):
    # Get Reserve Release
    reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
    if not reserve_release:
        return custom_response(
            {"status": "error", "msg": "Reserve Release not found"}, 404
        )

    get_rr_pdf = ReserveReleasePDF(reserve_release=reserve_release)
    return get_rr_pdf.download_pdf


@Auth.auth_required
def generate_lcra_csv(reserve_release_id):
    # Reserve Release
    rr_lcra_csv = generate_reserve_release_lcra_csv(
        reserve_release_id=reserve_release_id
    )
    return rr_lcra_csv


@Auth.auth_required
def get_rr_details(reserve_release_id):
    try:
        reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
        if not reserve_release:
            return custom_response(
                {"status": "error", "msg": "Reserve Release not found"}, 404
            )

        rr_details = ReserveReleaseDetails(reserve_release).get()

        return custom_response({"reserve_release": rr_details})

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_client_settings(reserve_release_id):
    reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
    if not reserve_release:
        return custom_response(
            {"status": "error", "msg": "Reserve Release not found"}, 404
        )

    rr_client_settings = reserve_release.rr_client_settings()
    return custom_response(rr_client_settings, 200)


@Auth.auth_required
def get_disclaimer(reserve_release_id):
    reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
    if not reserve_release:
        return custom_response(
            {"status": "error", "msg": "Reserve Release not found"}, 404
        )

    if reserve_release.status.value not in ["client_draft", "client_submission", "draft"]:
        get_client_disclaimer = reserve_release.get_saved_disclaimer()
    else:
        get_client_disclaimer = reserve_release.get_client_disclaimer()
    return custom_response(get_client_disclaimer, 200)


@Auth.auth_required
def get_bofa_transaction_status(reserve_release_id):
    reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)

    if not reserve_release:
        return custom_response(
            {"status": "error", "msg": "Reserve Release not found"}, 404
        )

    transaction_status = reserve_release.rr_payment_status()
    return custom_response(transaction_status, 200)


@Auth.auth_required
def client_reserve_release_pdf(reserve_release_id):
    # Get Reserve Release
    reserve_release = ReserveRelease.get_one_based_off_control_accounts(reserve_release_id)
    if not reserve_release:
        return custom_response(
            {"status": "error", "msg": "Reserve Release not found"}, 404
        )

    get_rr_pdf = ReserveReleasePDF(
        reserve_release=reserve_release, html_template="client_reserve_release.html"
    )
    return get_rr_pdf.download_pdf
