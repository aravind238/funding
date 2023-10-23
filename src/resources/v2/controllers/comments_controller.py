from flask import request
from src.models import *
import datetime
import os
from src.resources.v2.helpers import SendMails, custom_response
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.schemas import CommentsSchema

comments_schema = CommentsSchema()


@Auth.auth_required
def create():
    """
    Create Comment Function
    """
    try:
        req_data = request.get_json()

        # client_id
        get_client_id = req_data.get("client_id", None)
        # for tagging in comments
        notify_to_tagged = req_data.pop('mentions') if 'mentions' in req_data else None

        data, error = comments_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        comment = Comments(data)
        comment.save()

        data = comments_schema.dump(comment).data
        
        # soa tagging mail
        if data['soa_id'] is not None and data['reserve_release_id'] is None:
            soa_id = data['soa_id']
            soa = SOA.query.filter_by(is_deleted=False, id=soa_id).first()
            request_type = soa
            # get client_id
            client_id = request_type.client_id

        # reserve release tagging
        if data['reserve_release_id'] is not None and data['soa_id'] is None:
            reserve_release_id = data['reserve_release_id']
            reserve_release = ReserveRelease.query.filter_by(is_deleted=False, id=reserve_release_id).first()      
            request_type = reserve_release
            # get client_id
            client_id = request_type.client_id

        # payee tagging
        if (
            data["payee_id"]
            and not data["reserve_release_id"]
            and not data["soa_id"]
        ):
            payee_id = data["payee_id"]
            payee = Payee.query.filter_by(
                is_deleted=False, id=payee_id
            ).first()
            request_type = payee

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
            
            # get client_id
            client_id = client_payee.client_id

        # debtor limit approvals tagging
        if (
            data["debtor_limit_approvals_id"]
            and not data["reserve_release_id"]
            and not data["soa_id"]
            and not data["payee_id"]
        ):
            debtor_limit_approvals_id = data["debtor_limit_approvals_id"]
            debtor_limit_approvals = DebtorLimitApprovals.query.filter_by(
                deleted_at=None, id=debtor_limit_approvals_id
            ).first()
            request_type = debtor_limit_approvals
            # get client_id
            client_id = request_type.client_id

        # generic request tagging
        if (
            data["generic_request_id"]
            and not data["debtor_limit_approvals_id"]
            and not data["reserve_release_id"]
            and not data["soa_id"]
            and not data["payee_id"]
        ):
            generic_request_id = data["generic_request_id"]
            generic_request = GenericRequest.query.filter_by(
                deleted_at=None, id=generic_request_id
            ).first()
            request_type = generic_request
            # get client_id
            client_id = request_type.client_id

        # compliance repository tagging
        if (
            data["compliance_repository_id"]
            and not data["generic_request_id"]
            and not data["debtor_limit_approvals_id"]
            and not data["reserve_release_id"]
            and not data["soa_id"]
            and not data["payee_id"]
        ):
            compliance_repository_id = data["compliance_repository_id"]
            compliance_repository = ComplianceRepository.query.filter_by(
                deleted_at=None, id=compliance_repository_id
            ).first()
            request_type = compliance_repository
            # get client_id
            client_id = request_type.client_id

        if notify_to_tagged and request_type:
            # Mail to users tagged on comments
            user_emails = notify_to_tagged
            template_name = os.environ.get('USER_TAGGED_MAIL')
            send_mails = SendMails(
                request_type=request_type,
                client_id=client_id,
                template_name=template_name,
                user_emails=user_emails
            )
            send_mails.send_mail_to_tagged()

        return custom_response(data, 201)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Comments
    """
    try:
        comments = Comments.get_all_comments()
        data = comments_schema.dump(comments, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)


@Auth.auth_required
def get_one(comment_id):
    """
    Get A Comments
    """
    try:
        comment = Comments.get_one_comment(comment_id)
        if not comment:
            return custom_response({'status': 'error', 'msg': 'comment not found'}, 404)
        data = comments_schema.dump(comment).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)


@Auth.auth_required
def update(comment_id):
    """
    Update A Comments
    """
    try:
        req_data = request.get_json()
        comment = Comments.get_one_comment(comment_id)
        if not comment:
            return custom_response({'status': 'error', 'msg': 'comment not found'}, 404)

        if req_data:
            data, error = comments_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            comment.update(data)

        
        data = comments_schema.dump(comment).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)


@Auth.auth_required
def delete(comment_id):
    """
    Delete A Comments
    """
    try:
        comment = Comments.get_one_comment(comment_id)
        if not comment:
            return custom_response({'status': 'error', 'msg': 'comment not found'}, 404)

        # comment.is_deleted = True
        # comment.deleted_at = datetime.datetime.utcnow()

        comment.delete()
        return custom_response({'status': 'success', 'msg': 'Comment deleted'}, 202)

    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)
        
