from flask import request
from src.models import ControlAccount
import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.models import *
from src.resources.v2.schemas import ControlAccountSchema
from src.middleware.permissions import Permissions
from sqlalchemy import and_, or_, not_

control_account_schema = ControlAccountSchema()


@Auth.auth_required
def create():
    """
    Create A Control Account
    """
    try:
        req_data = request.get_json()
        data, error = control_account_schema.load(req_data)
        if error:
            return custom_response(error, 400)

        control_account = ControlAccount(data)
        control_account.save()

        data = control_account_schema.dump(control_account).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)


@Auth.auth_required
def get_all():
    """
    Get All Control Accounts
    """
    # control_accounts = ControlAccount.get_all_control_accounts()
    business_settings_control_accounts = Permissions.get_business_settings()[
        "control_accounts"
    ]
    # get logged user role organization ids
    organization_ids = Permissions.get_user_role_permissions()["organization_access"]
    
    # Only display the control accounts where the user has access to(LC-1607)
    control_accounts = ControlAccount.query.filter(
        ControlAccount.is_deleted == False,
        ClientControlAccounts.is_deleted == False,
        Client.is_deleted == False,
        not_(
            Client.ref_client_no.in_(
                [
                    "TODO-cadence",
                    "Cadence:sync-pending",
                    "TODO-factorcloud",
                ]
            )
        ),
        ControlAccount.name.in_(business_settings_control_accounts),
        ClientControlAccounts.control_account_id == ControlAccount.id,
        ClientControlAccounts.client_id == Client.id,
        OrganizationClientAccount.lcra_client_account_id == Client.lcra_client_accounts_id,
        OrganizationClientAccount.organization_id.in_(organization_ids)
    ).all()
    
    data = control_account_schema.dump(control_accounts, many=True).data
    return custom_response(data, 200)


@Auth.auth_required
def get_one(control_account_id):
    """
  Get A Control Account
  """
    try:
        control_account = ControlAccount.get_one_control_account(control_account_id)
        if not control_account:
            return custom_response({"status": "error", "msg": "control_account not found"}, 404)
        data = control_account_schema.dump(control_account).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)


@Auth.auth_required
def update(control_account_id):
    """
    Update A Control Account
    """
    try:
        req_data = request.get_json()
        control_account = ControlAccount.get_one_control_account(control_account_id)
        if not control_account:
            return custom_response({"status": "error", "msg": "control_account not found"}, 404)

        if req_data:
            data, error = control_account_schema.load(req_data, partial=True)
            if error:
                return custom_response(error, 400)
            control_account.update(data)


        data = control_account_schema.dump(control_account).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)


@Auth.auth_required
def delete(control_account_id):
    """
    Delete A Control Account
    """
    try:
        control_account = ControlAccount.get_one_control_account(control_account_id)
        if not control_account:
            return custom_response({"status": "error", "msg": "control_account not found"}, 404)

        # control_account.is_deleted = True
        # control_account.deleted_at = datetime.datetime.utcnow()

        control_account.delete()
        return custom_response({"status": "success", "msg": "Control account deleted"}, 202)
    except Exception as e:
        return custom_response({f'status: error, msg: Exception {e}'}, 404)
