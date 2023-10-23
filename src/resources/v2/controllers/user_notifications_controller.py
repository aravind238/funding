from flask import request
from src.models import *
import datetime
from src.middleware.authentication import Auth
from src.middleware.permissions import Permissions
from src.resources.v2.helpers import custom_response
from src.resources.v2.schemas import UserNotificationsSchema

user_notifications_schema = UserNotificationsSchema()



@Auth.auth_required
def create():
    """
    Create UserNotifications
    """
    try:
        request_data = request.get_json()
        data, error = user_notifications_schema.load(request_data)
        if error:
            return custom_response(error, 400)

        user_notifications = UserNotifications(data)
        user_notifications.save()

        data = user_notifications_schema.dump(user_notifications).data
        return custom_response(data, 201)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_all():
    """
    Get All UserNotifications
    """
    try:
        # Get logged user details
        user = Permissions.get_user_details()

        page = request.args.get("page", 0, type=int)
        rpp = request.args.get("rpp", 20, type=int)
        user_uuid = user["user_uuid"] if "user_uuid" in user else None
        is_read = request.args.get("is_read", None, type=str)

        if page > 0:
            data = UserNotificationsListing.get_paginated_user_notifications(
                page=page, rpp=rpp, user_uuid=user_uuid, is_read=is_read
            )
        else:
            data = UserNotificationsListing.get_all(user_uuid=user_uuid)

        if data is None:
            data = []

        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_one(user_notifications_id):
    """
    Get A UserNotifications
    """
    try:
        user_notifications = UserNotifications.get_one_user_notification(
            user_notifications_id
        )
        if not user_notifications:
            return custom_response({"status": "error", "msg": "User notification not found"}, 404)

        data = user_notifications_schema.dump(user_notifications).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def update(user_notifications_id):
    """
    Update A UserNotifications
    """
    try:
        request_data = request.get_json()
        user_notifications = UserNotifications.get_one_user_notification(
            user_notifications_id
        )
        if not user_notifications:
            return custom_response({"status": "error", "msg": "User notification not found"}, 404)

        if request_data:
            data, error = user_notifications_schema.load(request_data, partial=True)
            if error:
                return custom_response(error, 400)
            user_notifications.update(data)

        else:
            user_notifications = UserNotifications.query.filter_by(
                is_deleted=False, id=user_notifications_id
            ).first()

        data = user_notifications_schema.dump(user_notifications).data
        return custom_response(data, 200)
    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def delete(user_notifications_id):
    """
    Delete A UserNotifications
    """
    try:
        user_notifications = UserNotifications.get_one_user_notification(
            user_notifications_id
        )
        if not user_notifications:
            return custom_response({"status": "error", "msg": "User notifications not found"}, 404)

        # user_notifications.is_deleted = True
        # user_notifications.deleted_at = datetime.datetime.utcnow()

        user_notifications.delete()
        return custom_response({"status": "success", "msg": "User notification deleted"}, 202)

    except Exception as e:
        return custom_response({"status": "error", "msg": str(e)}, 404)


@Auth.auth_required
def get_user_notifications():          
    try: 
        # Get logged user details
        user = Permissions.get_user_details()
        user_uuid = user["user_uuid"] if "user_uuid" in user else None

        # try exception: getting Failed to decode JSON object when calling a POST request
        try:
            request_data = request.get_json()
            page = int(1)
            rpp = int(20)
            is_read = False

            if request_data and "page" in request_data:
                page = request_data["page"]

            if request_data and "rpp" in request_data:
                rpp = request_data["rpp"]

            if (
                (request_data)
                and ("is_read" in request_data)
                and (isinstance(request_data["is_read"], bool))
            ):
                is_read = request_data["is_read"]
        except:
            page = int(1)
            rpp = int(20)
            is_read = False

        data = UserNotificationsListing.get_paginated_user_notifications(
            page = page,
            rpp = rpp,
            user_uuid = user_uuid,
            is_read = is_read
        )
        
        if data is None:
            data = []

        return custom_response(data, 200)           
    except Exception as e:
        print("Exception- ", str(e))
        return custom_response({"status": "error", "msg": str(e)}, 404)
