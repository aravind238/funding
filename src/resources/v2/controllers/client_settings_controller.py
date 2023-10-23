from flask import request
from src.models import ClientSettings, Client
from datetime import datetime
from src.middleware.authentication import Auth
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import ClientSettingsSchema
from src.middleware.permissions import Permissions

client_settings_schema = ClientSettingsSchema()


@Auth.auth_required
def create():
    """
    Create Client Settings
    """
    # user role
    get_user_role = Permissions.get_user_role_permissions()
    user_role = get_user_role["user_role"]

    if user_role and user_role.lower() != "principal":
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to add Client Settings",
            },
            403,
        )

    req_data = request.get_json()
    data, error = client_settings_schema.load(req_data)
    if error:
        return custom_response(error, 400)

    client = Client.get_one_client(req_data.get("client_id"))
    if not client:
        return custom_response({"status": "error", "msg": "Client not found"}, 404)

    client_settings_exists = ClientSettings.query.filter_by(
        client_id=client.id, is_deleted=False
    ).first()
    if client_settings_exists:
        return custom_response(
            {"status": "error", "msg": f"{client.name} already has settings"}, 400
        )

    client_settings = ClientSettings(data)
    client_settings.save()

    data = client_settings_schema.dump(client_settings).data
    return custom_response(data, 201)


@Auth.auth_required
def get_all():
    """
    Get All Client Settings
    """
    client_settings = ClientSettings.get_all()
    data = client_settings_schema.dump(client_settings, many=True).data
    return custom_response(data, 200)


@Auth.auth_required
def get_one(id):
    """
    Get A Client Settings
    """
    client_settings = ClientSettings.get_one(id)
    if not client_settings:
        return custom_response(
            {"status": "error", "msg": "Client Settings not found"}, 404
        )
    data = client_settings_schema.dump(client_settings).data
    return custom_response(data, 200)


@Auth.auth_required
def update(id):
    """
    Update A Client Settings
    """
    # user role
    get_user_role = Permissions.get_user_role_permissions()
    user_role = get_user_role["user_role"]

    if user_role and user_role.lower() != "principal":
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to edit Client Settings",
            },
            403,
        )

    req_data = request.get_json()
    client_settings = ClientSettings.get_one(id)

    if not client_settings:
        return custom_response(
            {"status": "error", "msg": "Client Settings not found"}, 404
        )

    # if req_data.get("client_id"):
    #     # checking, if client id can been updated
    #     if client_settings.client_id != req_data.get("client_id"):
    #         # checking, if client exists
    #         client = Client.get_one_client(req_data.get("client_id"))
    #         if not client:
    #             return custom_response(
    #                 {"status": "error", "msg": "Client not found"}, 404
    #             )

    #         client_settings_exists = ClientSettings.query.filter_by(
    #             client_id=client.id, is_deleted=False
    #         ).first()
    #         if client_settings_exists:
    #             return custom_response(
    #                 {"status": "error", "msg": f"{client.name} already has settings"},
    #                 400,
    #             )

    if req_data:
        data, error = ClientSettingsSchema(
            exclude=[
                "client_id",
            ]
        ).load(req_data, partial=True)
        if error:
            return custom_response(error, 400)
        client_settings.update(data)

    data = client_settings_schema.dump(client_settings).data
    return custom_response(data, 200)


@Auth.auth_required
def delete(id):
    """
    Delete A Client Settings
    """
    # user role
    get_user_role = Permissions.get_user_role_permissions()
    user_role = get_user_role["user_role"]

    if user_role and user_role.lower() != "principal":
        return custom_response(
            {
                "status": "error",
                "msg": f"{user_role} doesn't have permission to delete Client Settings",
            },
            403,
        )

    client_settings = ClientSettings.get_one(id)
    if not client_settings:
        return custom_response(
            {"status": "error", "msg": "Client Settings not found"}, 404
        )

    # client_settings.is_deleted = True
    # client_settings.deleted_at = datetime.utcnow()

    client_settings.delete()
    return custom_response({"status": "success", "msg": "Client Settings deleted"}, 202)
