from flask import request
from src.models import OrganizationClientAccount
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import OrganizationClientAccountSchema

organization_client_account_schema = OrganizationClientAccountSchema()


@Auth.auth_required
def create():
    """
    Create OrganizationClientAccount Function
    """
    try:
        req_data = request.get_json()
        data, error = organization_client_account_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        organization_client_account = OrganizationClientAccount(data)
        organization_client_account.save()

        data = organization_client_account_schema.dump(organization_client_account).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All OrganizationClientAccount
    """
    try:
        client_accounts = (
            OrganizationClientAccount.get_all_organization_client_account()
        )
        data = organization_client_account_schema.dump(client_accounts, many=True).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(organization_client_account_id):
    """
    Get A OrganizationClientAccount
    """
    try:
        organization_client_account = OrganizationClientAccount.get_one_organization_client_account(
            organization_client_account_id
        )
        if not organization_client_account:
            return custom_response({"status": "error", "msg": "organization_client_account not found"}, 404)
        data = organization_client_account_schema.dump(organization_client_account).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(organization_client_account_id):
    """
    Update A OrganizationClientAccount
    """
    try:
        req_data = request.get_json()
        organization_client_account = OrganizationClientAccount.get_one_organization_client_account(
            organization_client_account_id
        )
        if not organization_client_account:
            return custom_response({"status": "error", "msg": "organization_client_account not found"}, 404)

        if req_data:
            data, error = organization_client_account_schema.load(
                req_data, partial=True
            )
            if error:
                return custom_response(error, 400)
            organization_client_account.update(data)
        else:
            organization_client_account = OrganizationClientAccount.query.filter_by(
                is_deleted=False, id=organization_client_account_id
            ).first()

        data = organization_client_account_schema.dump(organization_client_account).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(organization_client_account_id):
    """
    Delete A OrganizationClientAccount
    """
    try:
        organization_client_account = OrganizationClientAccount.get_one_organization_client_account(
            organization_client_account_id
        )
        if not organization_client_account:
            return custom_response({"status": "error", "msg": "organization_client_account not found"}, 404)

        # organization_client_account.is_deleted = True
        # organization_client_account.deleted_at = datetime.datetime.utcnow()

        organization_client_account.delete()
        return custom_response({"status": "success", "msg": "Organization client account deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)

