from flask import request
from src.models import *
from src import db
import datetime
import os
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import custom_response, SendMails
from src.resources.v2.schemas import *

reasons_schema = ReasonsSchema()
soa_schema = SOASchema()
reserve_release_schema = ReserveReleaseSchema()
payee_schema = PayeeSchema()
dla_schema = DebtorLimitApprovalsSchema()
generic_request_schema = GenericRequestSchema()
compliance_repository_schema = ComplianceRepositorySchema()


@Auth.auth_required
def create():
    """
    Create Reasons Function
    """
    try:
        req_data = request.get_json()

        # status
        request_status = req_data.get("status", None)
        # soa_id
        soa_id = req_data.get("soa_id", None)
        # reserve_release_id
        reserve_release_id = req_data.get("reserve_release_id", None)
        # payee_id
        payee_id = req_data.get("payee_id", None)
        # client_id
        get_client_id = req_data.get("client_id", None)
        # debtor_limit_approvals_id
        debtor_limit_approvals_id = req_data.get("debtor_limit_approvals_id", None)
        # compliance_repository_id
        compliance_repository_id = req_data.get("compliance_repository_id", None)
        previous_credit_limit = float(0)
        if debtor_limit_approvals_id:
            # for now only status 'rejected' for dla on reasoning
            req_data["status"] = "rejected"

        # generic_request_id
        generic_request_id = req_data.get("generic_request_id", None)
        if generic_request_id:
            # for generic_requests only status 'rejected' for now
            req_data["status"] = "rejected"

        if compliance_repository_id:
            # for compliance_repository only status 'principal_rejection' for now
            req_data["status"] = "principal_rejection"


        if not request_status:
            return custom_response({
                "status": "error", "msg": "status cannot be empty"
                }, 400
            )

        # request_type
        if soa_id:
            soa = SOA.query.filter_by(is_deleted=False, id=soa_id).first()
            request_type = soa

            if not request_type:
                return custom_response({
                    "status": "error", "msg": "soa not found"
                    }, 404
                )
        elif reserve_release_id:
            reserve_release = ReserveRelease.query.filter_by(
                is_deleted=False, id=reserve_release_id
            ).first()
            request_type = reserve_release

            if not request_type:
                return custom_response({
                    "status": "error", "msg": "reserve release not found"
                    }, 404
                )
        elif payee_id:
            payee = Payee.query.filter_by(
                is_deleted=False, is_active=True, id=payee_id
            ).first()
            request_type = payee

            if not request_type:
                return custom_response({
                    "status": "error", "msg": "payee not found"
                    }, 404
                )
            
            # needs client_id for checking client payee
            if not get_client_id:
                return custom_response(
                    {"status": "error", "msg": "client_id is required"}, 400
                )
            
            # check for client payee
            client_payee = ClientPayee.get_by_client_payee_id(get_client_id, payee_id)
            if not client_payee:
                return custom_response(
                    {"status": "error", "msg": "client_payee not found"}, 404
                )
        elif debtor_limit_approvals_id:
            debtor_limit_approvals = DebtorLimitApprovals.query.filter_by(
                deleted_at=None, id=debtor_limit_approvals_id
            ).first()
            request_type = debtor_limit_approvals

            if not request_type:
                return custom_response({
                    "status": "error", "msg": "debtor_limit_approvals not found"
                    }, 404
                )
        elif generic_request_id:
            generic_request = GenericRequest.query.filter_by(
                deleted_at=None, id=generic_request_id
            ).first()
            request_type = generic_request

            if not request_type:
                return custom_response({
                    "status": "error", "msg": "generic_request not found"
                    }, 404
                )
        elif compliance_repository_id:
            compliance_repository = ComplianceRepository.query.filter_by(
                deleted_at=None, id=compliance_repository_id
            ).first()
            request_type = compliance_repository

            if not request_type:
                return custom_response({
                    "status": "error", "msg": "compliance_repository not found"
                    }, 404
                )
        else:
            request_type = None

        # check, if request can be updated
        if request_type:
            if payee_id:
                validated_request_status = Permissions.can_update_payee(
                    request=request_type, update_request_status=request_status
                )
            elif debtor_limit_approvals_id:
                validated_request_status = Permissions.can_update_debtor_limits(
                    request=request_type, update_request_status=request_status
                )
            elif generic_request_id:
                validated_request_status = Permissions.can_update_generic_request(
                    request=request_type, update_request_status=request_status
                )
            elif compliance_repository_id:
                validated_request_status = Permissions.can_update_compliance_repository(
                    request=request_type, update_request_status=request_status
                )
            else:
                validated_request_status = Permissions.has_request_updating_permissions(
                    request=request_type
                )
            print("reasons", validated_request_status)
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

        data, error = reasons_schema.load(req_data)
        if error:
            return custom_response(error, 400)
        reasons = Reasons(data)

        # User details
        get_user_detail = Permissions.get_user_details()
        user_email = get_user_detail["email"]

        get_status = reasons.status
        approvals_history_data = {}

        status_dict = {"status": get_status}

        if get_status == "rejected":
            get_status = "rejected_at"

        if get_status == "principal_rejection":
            get_status = "principal_rejection_at"

        # update soa Status
        if soa_id:
            soa_data, soa_error = soa_schema.load(status_dict, partial=True)
            if not soa_error:
                # on soa status update, update last_processed_at
                soa_data.update({"last_processed_at": datetime.datetime.utcnow()})
                soa.update(soa_data)

                # approvals_history: soa rejected/action required
                approvals_history_data = {
                    "key": get_status,
                    "value": datetime.datetime.utcnow(),
                    "user": user_email,
                    "soa_id": soa_id,
                }
                
                # update invoices is_deleted=true if soa is rejected
                if request_status in ["principal_rejection", "rejected"]:
                    Invoice.query.filter_by(
                        soa_id=soa_id, is_deleted=False
                    ).update(
                        {
                            Invoice.is_deleted: True,
                            Invoice.deleted_at: datetime.datetime.utcnow(),
                        },
                        synchronize_session=False,
                    )
                    db.session.commit()

        # update reserve release Status
        if reserve_release_id:
            reserve_release_data, reserve_release_error = reserve_release_schema.load(
                status_dict, partial=True
            )
            if not reserve_release_error:
                # on reserve release status update, update last_processed_at
                reserve_release_data.update({"last_processed_at": datetime.datetime.utcnow()})
                reserve_release.update(reserve_release_data)

                # approvals_history: reserve_release rejected/action required
                approvals_history_data = {
                    "key": get_status,
                    "value": datetime.datetime.utcnow(),
                    "user": user_email,
                    "reserve_release_id": reserve_release_id,
                }

        # update payee Status
        if payee_id:
            payee_data, payee_error = payee_schema.load(
                status_dict, partial=True
            )
            if not payee_error:
                # on payee status update, update last_processed_at
                payee_data.update({"last_processed_at": datetime.datetime.utcnow()})
                payee.update(payee_data)

                # approvals_history: payee rejected/action required
                approvals_history_data = {
                    "key": get_status,
                    "value": datetime.datetime.utcnow(),
                    "user": user_email,
                    "payee_id": payee_id,
                }

        # update debtor limit approvals Status
        if debtor_limit_approvals_id:
            dla_data, dla_error = dla_schema.load(
                status_dict, partial=True
            )
            if not dla_error:
                # on debtor limit approvals status update, update last_processed_at
                dla_data.update({"last_processed_at": datetime.datetime.utcnow()})
                debtor_limit_approvals.update(dla_data)

                previous_credit_limit = debtor_limit_approvals.get_previous_credit_limit()

                # approvals_history: rejected
                approvals_history_data = {
                    "key": get_status,
                    "value": datetime.datetime.utcnow(),
                    "user": user_email,
                    "debtor_limit_approvals_id": debtor_limit_approvals_id,
                }

        # update generic request Status
        if generic_request_id:
            generic_request_data, generic_request_error = generic_request_schema.load(
                status_dict, partial=True
            )
            if not generic_request_error:
                # on generic request status update, update last_processed_at
                generic_request_data.update({"last_processed_at": datetime.datetime.utcnow()})
                generic_request.update(generic_request_data)

                # approvals_history: rejected
                approvals_history_data = {
                    "key": get_status,
                    "value": datetime.datetime.utcnow(),
                    "user": user_email,
                    "generic_request_id": generic_request_id,
                }

        # update compliance repository Status
        if compliance_repository_id:
            compliance_repository_data, compliance_repository_error = compliance_repository_schema.load(
                status_dict, partial=True
            )
            if not compliance_repository_error:
                # on compliance_repository status update, update last_processed_at
                compliance_repository_data.update({"last_processed_at": datetime.datetime.utcnow()})
                compliance_repository.update(compliance_repository_data)

                # approvals_history: principal_rejection
                approvals_history_data = {
                    "key": get_status,
                    "value": datetime.datetime.utcnow(),
                    "user": user_email,
                    "compliance_repository_id": compliance_repository_id,
                }

        reasons.save()
        data = reasons_schema.dump(reasons).data
        
        if approvals_history_data:
            approvals_history_data.update({"attribute": data})
            if debtor_limit_approvals_id:
                approvals_history_data["attribute"][
                    "previous_credit_limit"
                ] = float(previous_credit_limit)
                approvals_history = DebtorLimitApprovalsHistory(approvals_history_data)
                approvals_history.save()
            elif generic_request_id:
                approvals_history = GenericRequestApprovalsHistory(approvals_history_data)
                approvals_history.save()
            elif compliance_repository_id:
                approvals_history = ComplianceRepositoryApprovalsHistory(approvals_history_data)
                approvals_history.save()
            else:
                approvals_history = ApprovalsHistory(approvals_history_data)
                approvals_history.save()

        if not payee_id and not debtor_limit_approvals_id and not generic_request_id and not compliance_repository_id:
            # get client_id
            client_id = request_type.client_id

            # get logged user role and organization ids
            get_user_role = Permissions.get_user_role_permissions()
            role = get_user_role["user_role"]

            # Get organization ids
            organization_client_account = OrganizationClientAccount.query.filter_by(
                lcra_client_account_id=request_type.client.lcra_client_accounts_id
            ).first()

            organization_id = None
            if organization_client_account:
                organization_id = organization_client_account.organization_id

            # rejected
            if request_status == "rejected":
                if role.lower() == "ae":
                    # Mail to Principal
                    template_name = os.environ.get("REQUEST_REJECTED_MAIL")
                    recipient_role_name = "Principal"
                    send_mails = SendMails(
                        request_type=request_type,
                        client_id=client_id,
                        recipient_role_name=recipient_role_name,
                        template_name=template_name
                     )
                    send_mails.send_mail_request_notifications()

                if role.lower() == "bo":
                    # Mail to AE
                    template_name = os.environ.get("REQUEST_REJECTED_TO_AE_MAIL")
                    recipient_role_name = "AE"
                    send_mails = SendMails(
                        request_type=request_type,
                        client_id=client_id,
                        recipient_role_name=recipient_role_name,
                        template_name=template_name
                    )
                    send_mails.send_mail_request_notifications()

            # principal_rejection
            if request_status == "principal_rejection":
                # Mail to Client
                template_name = os.environ.get("REQUEST_REJECTED_OR_ACTION_REQUIRED_MAIL_TO_CLIENT")
                recipient_role_name = "Client"
                send_mails = SendMails(
                    request_type=request_type,
                    client_id=client_id,
                    recipient_role_name=recipient_role_name,
                    template_name=template_name
                )
                send_mails.send_mail_request_notifications()

            # action required
            if request_status == "action_required":
                # Mail to Principal
                template_name = os.environ.get("ACTION_REQUIRED_MAIL")
                recipient_role_name = "Principal"
                send_mails = SendMails(
                    request_type=request_type,
                    client_id=client_id,
                    recipient_role_name=recipient_role_name,
                    template_name=template_name,
                    organization_access=organization_id,
                )
                send_mails.send_mail_request_notifications()

            # action required by client
            if request_status == "action_required_by_client":
                # Mail to Client
                template_name = os.environ.get("REQUEST_REJECTED_OR_ACTION_REQUIRED_MAIL_TO_CLIENT")
                recipient_role_name = "Client"
                send_mails = SendMails(
                    request_type=request_type,
                    client_id=client_id,
                    recipient_role_name=recipient_role_name,
                    template_name=template_name,
                    organization_access=organization_id,
                )
                send_mails.send_mail_request_notifications()

        # payee notifications
        if payee_id and request_status:
            # get client_id
            client_id = client_payee.client_id

            # get payee_lcra_client_accounts_id 
            payee_lcra_client_accounts_id = request_type.get_payee_lcra_client_accounts_id()

            # Get organization ids
            organization_id = None
            if payee_lcra_client_accounts_id:
                organization_client_account = OrganizationClientAccount.query.filter_by(
                    lcra_client_account_id=payee_lcra_client_accounts_id
                ).first()

                if organization_client_account:
                    organization_id = organization_client_account.organization_id

            recipient_role_name = None
            if request_status in ["action_required", "rejected"]:
                # Mail to Principal
                recipient_role_name = "Principal"
            if request_status in ["action_required_by_client", "principal_rejection"]:
                # Mail to Client
                recipient_role_name = "Client"

            send_mails = SendMails(
                request_type=payee,
                client_id=client_id,
                recipient_role_name=recipient_role_name,
                organization_access=organization_id,
            )
            send_mails.send_mail_request_notifications()
            
        # debtor_limit_approvals notifications
        if debtor_limit_approvals_id and request_status:
            # get client_id
            client_id = request_type.client_id

            # request rejected by AE
            if request_status == "rejected":
                recipient_role_name = None

                if request_type.request_created_by_client():
                    # Mail to Client
                    recipient_role_name = "Client"

                if request_type.request_created_by_principal():
                    # Mail to Principal
                    recipient_role_name = "Principal"

                # send mail to principal/client
                if recipient_role_name:
                    template_name = os.environ.get("CREDIT_LIMIT_APPROVED_OR_REJECTED_BY_AE_MAIL")
                    send_mails = SendMails(
                        request_type=request_type,
                        client_id=client_id,
                        recipient_role_name=recipient_role_name,
                        template_name=template_name
                    )
                    send_mails.send_mail_request_notifications()

        # generic_request notifications
        if generic_request_id and request_status:
            # get client_id
            client_id = request_type.client_id

            # request rejected by AE
            if request_status == "rejected":
                # Mail to Principal
                recipient_role_name = "Principal"

                # send mail to principal
                if recipient_role_name:
                    template_name = os.environ.get("CREDIT_LIMIT_APPROVED_OR_REJECTED_BY_AE_MAIL")
                    send_mails = SendMails(
                        request_type=request_type,
                        client_id=client_id,
                        recipient_role_name=recipient_role_name,
                        template_name=template_name
                    )
                    send_mails.send_mail_request_notifications()

        # compliance_repository notifications
        if compliance_repository_id and request_status:
            # get client_id
            client_id = request_type.client_id
            
            # request rejected by Principal
            if request_status == "principal_rejection":
                if request_type.request_created_by_client() or request_type.request_submitted_by_client():
                    # send mail to client
                    template_name = os.environ.get("CREDIT_LIMIT_APPROVED_OR_REJECTED_BY_AE_MAIL")
                    send_mails = SendMails(
                        request_type=request_type,
                        client_id=client_id,
                        recipient_role_name="Client",
                        template_name=template_name
                    )
                    send_mails.send_mail_request_notifications()

        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Reasons
    """
    try:
        reasons = Reasons.get_all_reasons()
        data = reasons_schema.dump(reasons, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(reasons_id):
    """
    Get A Reasons
    """
    try:
        reasons = Reasons.get_one_reasons(reasons_id)
        if not reasons:
            return custom_response({"status": "error", "msg": "reasons not found"}, 404)
        data = reasons_schema.dump(reasons).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(reasons_id):
    """
    Update A Reasons
    """
    try:
        req_data = request.get_json()
        reasons = Reasons.get_one_reasons(reasons_id)
        if not reasons:
            return custom_response({"status": "error", "msg": "reasons not found"}, 404)

        if req_data:
            data, error = reasons_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            reasons.update(data)

        else:
            reasons = Reasons.query.filter_by(is_deleted=False, id=reasons_id).first()

        data = reasons_schema.dump(reasons).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(reasons_id):
    """
    Delete A Reasons
    """
    try:
        reasons = Reasons.get_one_reasons(reasons_id)
        if not reasons:
            return custom_response({"status": "error", "msg": "reasons not found"}, 404)

        # reasons.is_deleted = True
        # reasons.deleted_at = datetime.datetime.utcnow()

        reasons.delete()
        return custom_response({"status": "success", "msg": "Reason deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)

