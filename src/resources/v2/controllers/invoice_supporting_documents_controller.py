from flask import request
from src.models import *
from datetime import date, datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import *
from src.middleware.permissions import Permissions

invoice_supporting_documents_schema = InvoiceSupportingDocumentsSchema()
invoice_supporting_documents_ref_schema = InvoiceSupportingDocumentsRefSchema()


@Auth.auth_required
def create():
    """
    Create Invoice Supporting Documents
    """
    req_data = request.get_json()

    if req_data.get("client_id") and req_data.get("debtor_id"):
        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]
        
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
                {"status": "error", "msg": "Client Debtor not found"}, 404
            )

    # check invoice
    if "invoice_id" not in req_data:
        return custom_response(
            {"status": "error", "msg": "invoice_id is required"}, 400
        )

    invoice  = Invoice.get_one_based_off_control_accounts(req_data.get("invoice_id"))
    if not invoice:
        return custom_response(
            {"status": "error", "msg": "Invoice not found"}, 404
        )

    # check soa
    if "soa_id" not in req_data:
        return custom_response(
            {"status": "error", "msg": "soa_id is required"}, 400
        )
    
    soa = SOA.get_one_based_off_control_accounts(req_data.get("soa_id"))
    if not soa:
        return custom_response({"status": "error", "msg": "SOA not found"}, 404)

    # get logged user email
    user_email = Permissions.get_user_details()["email"]

    req_data["user"] = user_email

    data, error = invoice_supporting_documents_schema.load(req_data)
    if error:
        return custom_response(error, 400)
    
    invoice_supporting_documents = InvoiceSupportingDocuments(data)
    invoice_supporting_documents.save()

    data = invoice_supporting_documents_schema.dump(invoice_supporting_documents).data

    return custom_response(data, 201)


@Auth.auth_required
def get_all():
    """
    Get All Invoice Supporting Documents
    """
    invoice_supporting_documents = InvoiceSupportingDocuments.get_all()
    if not invoice_supporting_documents:
        # as per frontend requirement, static status=200 for error handling
        return custom_response([], 200)

    data = invoice_supporting_documents_ref_schema.dump(invoice_supporting_documents, many=True).data
    return custom_response(data, 200)


@Auth.auth_required
def get_one(id):
    """
    Get a Invoice Supporting Document
    """
    invoice_supporting_documents = InvoiceSupportingDocuments.get_one_based_off_control_accounts(id)
    if not invoice_supporting_documents:
        return custom_response(
            {"status": "error", "msg": "There is no Supporting Document File for Invoice in this request."}, 404
        )

    data = invoice_supporting_documents_ref_schema.dump(invoice_supporting_documents).data
    return custom_response(data, 200)


@Auth.auth_required
def update(id):
    """
    Update a Invoice Supporting Document
    """
    req_data = request.get_json()

    invoice_supporting_documents = InvoiceSupportingDocuments.get_one_based_off_control_accounts(id)
    if not invoice_supporting_documents:
        return custom_response(
            {"status": "error", "msg": "Invoice Supporting Document not found"}, 404
        )

    if req_data:
        data, error = InvoiceSupportingDocumentsSchema(
            exclude=["client_id", "debtor_id"]
        ).load(req_data, partial=True)
        if error:
            return custom_response(error, 400)
        
        # user email
        user_email = Permissions.get_user_details()["email"]
        data["user"] = user_email
        invoice_supporting_documents.update(data)

    data = invoice_supporting_documents_schema.dump(invoice_supporting_documents).data

    return custom_response(data, 200)


@Auth.auth_required
def delete(id):
    """
    Delete a Invoice Supporting Document
    """
    invoice_supporting_documents = InvoiceSupportingDocuments.get_one_based_off_control_accounts(id)
    if not invoice_supporting_documents:
        return custom_response(
            {"status": "error", "msg": "Invoice Supporting Document not found"}, 404
        )

    # can only delete if soa status is draft
    if invoice_supporting_documents.soa.status.value != "draft":
        return custom_response(
            {
                "status": "error",
                "msg": f"request can't be deleted",
            },
            403,
        )

    invoice_supporting_documents.delete()

    return custom_response(
        {"status": "success", "msg": "Invoice Supporting Document deleted"}, 202
    )
