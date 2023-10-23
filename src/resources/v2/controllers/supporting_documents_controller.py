from flask import request
from src.models import *
from datetime import datetime
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import (
    custom_response, 
    get_presigned_url,
)
from src.resources.v2.schemas import *

supporting_documents_schema = SupportingDocumentsSchema()



@Auth.auth_required
def create():
    """
    Create Supporting Documents Function
    """
    try:
        req_data = request.get_json()
        # soa_id
        soa_id = req_data.get("soa_id", None)
        # reserve_release_id
        reserve_release_id = req_data.get("reserve_release_id", None)

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
        else:
            request_type = None

        # user role
        get_user_role = Permissions.get_user_role_permissions()
        user_role = get_user_role["user_role"]

        # User details
        get_user_detail = Permissions.get_user_details()
        user_email = get_user_detail["email"]
        user_uuid = get_user_detail["user_uuid"]

        approvals_history_data = {}

        # LC-2313: Allow BO to upload files after the approval of the request(soa/rr)
        if (
            request_type 
            and request_type.status.value == "completed" 
            and user_role.lower() == Permissions.bo
        ):
            # save notes
            req_data["notes"] = "bo_uploaded_document_view_details"

            approvals_history_data = {
                "user": user_email,
                "key": f"{user_role.lower()}_uploaded_document_at",
                "value": datetime.utcnow(),
            }
            
            # soa
            if request_type.object_as_string().lower() == "soa":
                approvals_history_data.update({"soa_id": request_type.id})
            # reserve release
            elif request_type.object_as_string().lower() == "reserve release":
                approvals_history_data.update({"reserve_release_id": request_type.id})

        # save user_uuid
        req_data["user_uuid"] = user_uuid

        data, error = supporting_documents_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        supporting_document = SupportingDocuments(data)
        supporting_document.save()

        data = supporting_documents_schema.dump(supporting_document).data

        # save info in approval history if bo has uploaded documents after request(soa/rr) has been approved by bo
        if approvals_history_data:
            approvals_history_data.update({"attribute": data})
            approvals_history = ApprovalsHistory(approvals_history_data)
            approvals_history.save()

        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Supporting Documents
    """
    try:
        supporting_documents = SupportingDocuments.get_all_supporting_documents()
        data = supporting_documents_schema.dump(supporting_documents, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(supporting_documents_id):
    """
    Get a Supporting Document
    """
    try:
        supporting_document = SupportingDocuments.get_one_supporting_document(
            supporting_documents_id
        )
        if not supporting_document:
            return custom_response({"status": "error", "msg": "Supporting Document not found"}, 404)
        data = supporting_documents_schema.dump(supporting_document).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(supporting_documents_id):
    """
    Update a Supporting Document
    """
    try:
        req_data = request.get_json()
        supporting_document = SupportingDocuments.get_one_supporting_document(
            supporting_documents_id
        )
        if not supporting_document:
            return custom_response({"status": "error", "msg": "Supporting Document not found"}, 404)

        if req_data:
            data, error = supporting_documents_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            supporting_document.update(data)

        else:
            supporting_document = SupportingDocuments.query.filter_by(
                is_deleted=False, id=supporting_documents_id
            ).first()

        data = supporting_documents_schema.dump(supporting_document).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(supporting_documents_id):
    """
    Delete a Supporting Document
    """
    try:
        supporting_document = SupportingDocuments.get_one_supporting_document(
            supporting_documents_id
        )
        if not supporting_document:
            return custom_response({"status": "error", "msg": "Supporting Document not found"}, 404)
        
        # soa_id
        soa_id = supporting_document.soa_id
        # reserve_release_id
        reserve_release_id = supporting_document.reserve_release_id

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
        else:
            request_type = None

        # User details
        get_user_detail = Permissions.get_user_details()
        user_email = get_user_detail["email"]
        user_uuid = get_user_detail["user_uuid"]
        
        # LC-2313: Other users cannot delete the file uploaded by BO
        if (
            supporting_document.notes == "bo_uploaded_document_view_details"
            and supporting_document.user_uuid
            and user_uuid != supporting_document.user_uuid
        ):
            return custom_response(
                {
                    "status": "error",
                    "msg": "You can't delete the document.",
                },
                403,
            )

        # user role
        get_user_role = Permissions.get_user_role_permissions()
        user_role = get_user_role["user_role"]

        approvals_history_data = {}
        if (
            request_type 
            and request_type.status.value == "completed"
            and user_role.lower() == Permissions.bo
        ):            
            approvals_history_data = {
                "user": user_email,
                "key": f"{user_role.lower()}_deleted_document_at",
                "value": datetime.utcnow(),
            }
            
            if request_type.object_as_string().lower() == "soa":
                approvals_history_data.update({"soa_id": request_type.id})

            elif request_type.object_as_string().lower() == "reserve release":
                approvals_history_data.update({"reserve_release_id": request_type.id})

            data = supporting_documents_schema.dump(supporting_document).data

            # save info in approval history if bo has deleted uploaded document after request(soa/rr) has been approved by bo
            if approvals_history_data:
                approvals_history_data.update({"attribute": data})
                approvals_history = ApprovalsHistory(approvals_history_data)
                approvals_history.save()

        # supporting_document.is_deleted = True
        # supporting_document.deleted_at = datetime.utcnow()

        supporting_document.delete()
        return custom_response({"status": "success", "msg": "Supporting document deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def presigned_url():
    try:
        request_obj = request.get_json()
        content_type = request_obj["content_type"]
        name = request_obj["name"]
        description = request_obj["description"]

        make_request = get_presigned_url(
            content_type=content_type, name=name, description=description
        )

        return custom_response(make_request.json(), make_request.status_code)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)
