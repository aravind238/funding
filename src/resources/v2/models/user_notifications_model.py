from src import db
import enum
from datetime import datetime
from src.middleware.permissions import Permissions
from src.middleware.organization import Organization
from sqlalchemy import and_, or_, not_


class NotificationType(enum.Enum):
    compliance_repository = "compliance_repository"
    credit_limit = "credit_limit"
    generic_request = "generic_request"
    payee = "payee"
    reserve_release = "reserve_release"
    soa = "soa"


class UserNotifications(db.Model):
    """ UserNotifications model """

    __tablename__ = "user_notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, nullable=False)
    user_uuid = db.Column(db.String(255), nullable=False)
    notification_type = db.Column(
        db.Enum(NotificationType), default=NotificationType.soa.value
    )
    message = db.Column(db.Text, nullable=False)
    url_link = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime)

    # Indexes
    __table_args__ = (
        db.Index("idx_client_id", "client_id"),
        db.Index("idx_user_uuid", "user_uuid"),
    )

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.user_uuid = data.get("user_uuid")
        self.notification_type = data.get("notification_type")
        self.message = data.get("message")
        self.url_link = data.get("url_link")
        self.is_read = data.get("is_read")
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        for key, item in data.items():
            setattr(self, key, item)
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all_user_notifications():
        return UserNotifications.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_user_notification(id):
        return UserNotifications.query.filter_by(id=id, is_deleted=False).first()


class UserNotificationsListing:
    def get_all(user_uuid=None):
        from src.resources.v2.schemas import UserNotificationsSchema

        user_notifications_schema = UserNotificationsSchema(many=True)

        user_notifications = (
            UserNotifications.query.filter_by(is_deleted=False)
            .filter(UserNotifications.user_uuid == user_uuid)
            .order_by(UserNotifications.id.desc())
        )
        data = user_notifications_schema.dump(user_notifications).data

        if len(data) < 1:
            return None

        return data

    def get_paginated_user_notifications(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        user_uuid = kwargs.get("user_uuid", None)
        is_read = kwargs.get("is_read", False)

        from src.models import (
            Client,
            OrganizationClientAccount,
        )

        from src.resources.v2.schemas import (
            UserNotificationsSchema,
        )
        user_notifications_schema = UserNotificationsSchema(many=True)

        # # get logged user role organization ids
        # organization_ids = Permissions.get_user_role_permissions()["organization_access"]
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # user_notifications
        user_notifications = (
            UserNotifications.query
            .join(
                Client,
                and_(                        
                    Client.is_deleted == False,
                    Client.id == UserNotifications.client_id,
                )
            )
            # .join(
            #     OrganizationClientAccount,
            #     and_(                        
            #         OrganizationClientAccount.is_deleted == False,
            #         OrganizationClientAccount.lcra_client_account_id == Client.lcra_client_accounts_id,
            #         OrganizationClientAccount.organization_id.in_(organization_ids)
            #     )
            # )
            .filter(
                UserNotifications.is_deleted == False,
                UserNotifications.client_id.in_(client_ids),
            )
        )

        # user_uuid
        if user_uuid is not None:
            user_notifications = user_notifications.filter(
                UserNotifications.user_uuid == user_uuid
            )

        # is_read
        if isinstance(is_read, bool):
            user_notifications = user_notifications.filter(
                UserNotifications.is_read == is_read
            )

        # order by
        user_notifications = user_notifications.order_by(UserNotifications.id.desc())

        # pagination
        user_notifications_paginated = user_notifications.paginate(page, rpp, False)
        total_pages = user_notifications_paginated.pages
        user_notifications_results = user_notifications_schema.dump(
            user_notifications_paginated.items
        ).data
        total_count = user_notifications_paginated.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(user_notifications_results) < 1:
            return {
                "msg": get_invalid_page_msg,
                "per_page": rpp,
                "current_page": page,
                "total_pages": 0,
                "data": [],
                "total_count": 0,
            }

        return {
            "msg": "Records found",
            "per_page": rpp,
            "current_page": page,
            "total_pages": total_pages,
            "data": user_notifications_results,
            "total_count": total_count,
        }
