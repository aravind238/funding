import os
import ast
import requests
from flask import json, abort
from src.middleware.permissions import Permissions
from datetime import datetime
from pytz import timezone
from src.models import UserNotifications
from src import db
from .resources import custom_response
import threading
from src.resources.v2.helpers.convert_datetime import datetime_to_string_format
from src.resources.v2.helpers.logs import Logs


class SendMails:
    def __init__(
        self,
        request_type,
        client_id=None,
        recipient_role_name=None,
        request_status=None,
        template_name=None,
        user_emails=None,
        organization_access=None,
        category=None,
    ) -> None:
        # request type: soa/reserve release/payee
        self.request_type = request_type
        self.request_status = (
            request_status if request_status else request_type.status.value
        )
        self.recipient_role_name = (
            recipient_role_name.lower() if recipient_role_name else None
        )
        self.category = (
            category.capitalize() if category else None
        )
        self.template_name = template_name
        self.user_emails = user_emails

        # lc details
        self.lc_email = os.environ.get("LC_EMAIL")
        self.lc_name = os.environ.get("LC_NAME")

        # logged user role and organization ids
        logged_user_role = Permissions.get_user_role_permissions()
        self.user_role = (
            logged_user_role["user_role"].lower() if logged_user_role else None
        )
        self.organization_access = organization_access
        self.client_id = client_id

        # get lc_action_required_email values and converted into dictionary
        self.lc_action_required_email = os.environ.get("LC_ACTION_REQUIRED_EMAIL")
        lc_action_required_email_dict = ast.literal_eval(self.lc_action_required_email)
        
        # add bcc recipient email address
        if (
            self.organization_access 
            and int(self.organization_access) == lc_action_required_email_dict["organization_id"] 
            and self.request_type.status.value in ["action_required", "action_required_by_client"]
            ):
            self.bcc_recipients = [{"email": self.lc_email, "name": self.lc_name}, {"email": lc_action_required_email_dict["email"], "name": self.lc_name}]
        else:
            self.bcc_recipients = [{"email": self.lc_email, "name": self.lc_name}]

        # get branding logo url
        get_branding = Permissions.get_user_details()["business_branding"]
        self.logo_url = (
            get_branding["logo_url"]
            if get_branding and "logo_url" in get_branding
            else None
        )

        self.sender_name = None
        self.sender_email = None

        # Get email of user who created request
        self.request_created_by_client = None
        self.request_created_by_principal = None

        # Get notify_status
        self.notify_status = None

        # notification message and subject
        self.subject = ""
        self.notification_message = ""
        self.save_notification_message = ""

        self.get_request_created_by()
        self.sender_details()
        self.request_type_details()
        self.payee_notification_message()
        self.mails_notification_message()

    def sendgrid_mail(self, data=None):
        headers = {
            "Content-Type": "application/json",
            "api-token": os.environ.get("SENDGRID_API_TOKEN"),
        }

        sendgrid_mail_url = os.environ.get("SEND_MAIL_URL") + os.environ.get(
            "SENDGRID_MAIL"
        )

        if not data:
            return abort(404, f"sendgrid mail: Data is empty")
        print("--sendgrid_mail--")
        requests.post(url=sendgrid_mail_url, data=json.dumps(data), headers=headers)
        
        # save mail data in logs
        logs = Logs(filename="mail_logs", data=data)
        logs.save_logs()


    def send_mail_request_notifications(self):
        if not self.recipient_role_name:
            print(f"Recipient Role name is required {self.recipient_role_name}")
            return custom_response(
                {"status": "error", "msg": "Role name is required"}, 404
            )

        # template name
        template_name = (
            self.template_name
            if self.template_name
            else os.environ.get("PAYEE_REQUEST_MAILS_TO_USERS")
        )

        # client portal
        if self.request_created_by_client:
            if not isinstance(self.request_created_by_client, list):
                self.request_created_by_client = [self.request_created_by_client]

            client_users_details = Permissions.get_users_by_email(
                self.request_created_by_client
            )
            if client_users_details and client_users_details["status_code"] != 200:
                print(f"send mail:- msg: {client_users_details['msg']}")
                return custom_response(
                    {"status": "error", "msg": client_users_details["msg"]},
                    client_users_details["status_code"],
                )

            recipient_users_details = client_users_details["users"]

            if not recipient_users_details:
                print(
                    f"client_user_details:- Client {self.request_created_by_client} not found on permissions"
                )
                return custom_response(
                    {
                        "status": "error",
                        "msg": f"Client {self.request_created_by_client} not found on permissions",
                    },
                    404,
                )

            print("---client_user_details---", recipient_users_details)

        else:
            # get users to be notified
            recipient_users_details = self.search_users_by_permissions()

            # Get recipient users from get_recipient_users where user_emails match
            if self.request_created_by_principal and recipient_users_details:
                recipient_users_details = [
                    users
                    for users in recipient_users_details
                    if self.request_created_by_principal in users["email"]
                ]
                if not recipient_users_details:
                    print(
                        f"recipient_users_details:- {recipient_users_details} ----- msg: Principal {self.request_created_by_principal} not found on permissions"
                    )
                    return custom_response(
                        {
                            "status": "error",
                            "msg": f"Principal {self.request_created_by_principal} not found on permissions",
                        },
                        404,
                    )

        recipient_emails_list = []
        add_user_notifications = []
        counter = 1
        if recipient_users_details:
            for recipient_user_info in recipient_users_details:
                recipient_name = (
                    recipient_user_info["first_name"]
                    + " "
                    + recipient_user_info["last_name"]
                )
                recipient_email = recipient_user_info["email"]
                user_uuid = recipient_user_info["id"]

                recipient_name_email = (
                    f"{counter}. {recipient_name} - {recipient_email}"
                )
                recipient_emails_list.append(recipient_name_email)

                roles_names = ["principal", "ae", "bo", "client"]
                if self.recipient_role_name.lower() in roles_names:
                    recipient_name = recipient_name

                data = {
                    "sender_email": self.lc_email,
                    "sender_name": self.lc_name,
                    "recipients": [{"email": recipient_email, "name": recipient_name}],
                    "bcc": self.bcc_recipients,
                    "subject": self.subject,
                    "template_name": template_name,
                    "template_data": {
                        "sender_name": self.sender_name,
                        "recipient_name": recipient_name,
                        "notification_message": self.notification_message,
                        "sender_role": self.user_role,
                        "request_status": self.request_status,
                        "request_type": self.request_type.object_as_string(),
                        "request_id": self.request_id_string,
                        "link": self.request_link,
                        "web_url": self.app_url,
                        "branding_logo_url": self.logo_url,
                    },
                }
                print("--data--", data)
                # send to sendgrid
                threading.Thread(
                    target=self.sendgrid_mail, kwargs={"data": data}
                ).start()

                # for user notification type
                if self.request_type_string in ["reserve-release", "credit-limit", "generic-request", "compliance-repository"]:
                    self.request_type_string = self.request_type_string.replace(
                        "-", "_"
                    )

                # save user_notifications
                user_notifications_data = {
                    "user_uuid": user_uuid,
                    "notification_type": self.request_type_string,
                    "message": self.save_notification_message,
                    "url_link": self.url_link,
                    "client_id": self.client_id,
                }
                add_user_notifications.append(
                    UserNotifications(user_notifications_data)
                )
                counter += 1

        # notification to sender about which users notified
        self.notify_to_sender(
            recipient_emails_list=recipient_emails_list,
        )

        if len(add_user_notifications):
            db.session.add_all(add_user_notifications)

        db.session.commit()

    def send_permission_exception_mail(self):
        if not self.user_emails or (not isinstance(self.user_emails, list)):
            print("Permission exception mail:- User emails empty")
            return custom_response(
                {"status": "error", "msg": "User emails not found"}, 404
            )

        # for reviewed mails
        template_name = os.environ.get("USER_TAGGED_MAIL")
        notification_message = f"We're writing to inform you that {self.sender_name} has submitted {self.request_type.object_as_string()} - {self.request_id_string} for your review."
        notification_message_for_db = f"{self.current_datetime} {self.request_type.object_as_string()} - {self.request_id_string} was REVIEWED by A/E: {self.sender_name}"
        object_string = self.request_type.object_as_string()
        subject_request_id = (
            f"{self.request_type.client.ref_client_no}-SOAID{self.request_type.soa_ref_id}"
            if object_string == "SOA"
            else f"{self.request_type.id}"
        )
        subject = f"Please review {object_string} - {subject_request_id}"

        # get_recipient_users
        recipient_users_details = self.get_users_by_email()

        recipient_emails_list = []
        add_user_notifications = []
        counter = 1
        if recipient_users_details:
            for recipient_user_info in recipient_users_details:
                recipient_name = (
                    recipient_user_info["first_name"]
                    + " "
                    + recipient_user_info["last_name"]
                )
                recipient_email = recipient_user_info["email"]
                user_uuid = recipient_user_info["id"]

                recipient_name_email = (
                    f"{counter}. {recipient_name} - {recipient_email}"
                )
                recipient_emails_list.append(recipient_name_email)

                data = {
                    "sender_email": self.lc_email,
                    "sender_name": self.lc_name,
                    "recipients": [{"email": recipient_email, "name": recipient_name}],
                    "bcc": self.bcc_recipients,
                    "subject": subject,
                    "template_name": template_name,
                    "template_data": {
                        "recipient_name": recipient_name,
                        "notification_message": notification_message,
                        "request_type": self.request_type.object_as_string(),
                        "request_id": self.request_id,
                        "link": self.request_link,
                        "web_url": self.app_url,
                        "branding_logo_url": self.logo_url,
                    },
                }
                print("--data--", data)
                # send to sendgrid
                threading.Thread(
                    target=self.sendgrid_mail, kwargs={"data": data}
                ).start()

                # for user notification type
                if self.request_type_string == "reserve-release":
                    self.request_type_string = self.request_type_string.replace(
                        "-", "_"
                    )

                # save user_notifications
                user_notifications_data = {
                    "user_uuid": user_uuid,
                    "notification_type": self.request_type_string,
                    "message": notification_message_for_db,
                    "url_link": self.url_link,
                    "client_id": self.client_id,
                }

                add_user_notifications.append(
                    UserNotifications(user_notifications_data)
                )
                counter += 1

        # notification to sender ae about which users notified
        self.notify_to_sender_ae(
            recipient_emails_list=recipient_emails_list,
        )
        if len(add_user_notifications):
            db.session.add_all(add_user_notifications)

        db.session.commit()

    def send_mail_to_tagged(self):
        if not self.user_emails or (not isinstance(self.user_emails, list)):
            print("tagged mail:- User emails empty")
            return custom_response(
                {"status": "error", "msg": "User emails not found"}, 404
            )

        # for tagged mails
        notification_message = f"{self.current_datetime}  You were tagged in the {self.request_type.object_as_string()} - {self.request_id_string}"
        notification_message_for_db = notification_message
        object_string = self.request_type.object_as_string()
        subject_request_id = (
            f"{self.request_type.client.ref_client_no}-SOAID{self.request_type.soa_ref_id}"
            if object_string == "SOA"
            else f"{self.request_type.id}"
        )
        subject = f"You were tagged in the {object_string} - {subject_request_id}"

        # get_recipient_users
        recipient_users_details = self.get_users_by_email()

        recipient_emails_list = []
        add_user_notifications = []
        counter = 1
        if recipient_users_details:
            for recipient_user_info in recipient_users_details:
                recipient_name = (
                    recipient_user_info["first_name"]
                    + " "
                    + recipient_user_info["last_name"]
                )
                recipient_email = recipient_user_info["email"]
                user_uuid = recipient_user_info["id"]

                recipient_name_email = (
                    f"{counter}. {recipient_name} - {recipient_email}"
                )
                recipient_emails_list.append(recipient_name_email)

                data = {
                    "sender_email": self.lc_email,
                    "sender_name": self.lc_name,
                    "recipients": [{"email": recipient_email, "name": recipient_name}],
                    "bcc": self.bcc_recipients,
                    "subject": subject,
                    "template_name": self.template_name,
                    "template_data": {
                        "recipient_name": recipient_name,
                        "notification_message": notification_message,
                        "request_type": self.request_type.object_as_string(),
                        "request_id": self.request_id_string,
                        "link": self.request_link,
                        "web_url": self.app_url,
                        "branding_logo_url": self.logo_url,
                    },
                }
                print("--data--", data)
                # send to sendgrid
                threading.Thread(
                    target=self.sendgrid_mail, kwargs={"data": data}
                ).start()

                # for user notification type
                if self.request_type_string in ["reserve-release", "credit-limit", "generic-request", "compliance-repository"]:
                    self.request_type_string = self.request_type_string.replace(
                        "-", "_"
                    )

                # save user_notifications
                user_notifications_data = {
                    "user_uuid": user_uuid,
                    "notification_type": self.request_type_string,
                    "message": notification_message_for_db,
                    "url_link": self.url_link,
                    "client_id": self.client_id,
                }

                add_user_notifications.append(
                    UserNotifications(user_notifications_data)
                )
                counter += 1

        if len(add_user_notifications):
            db.session.add_all(add_user_notifications)

        db.session.commit()

    def search_users_by_permissions(self):
        if not self.recipient_role_name:
            print(f"Recipient Role name is required {self.recipient_role_name}")
            return abort(404, "Role name is required")

        user_permissions = [
            {"app_resource_name": "app_flow", "permissions": [self.recipient_role_name]}
        ]
        require_all = False

        if self.organization_access:
            user_permissions = [
                {
                    "app_resource_name": "app_flow",
                    "permissions": [self.recipient_role_name],
                },
                {
                    "app_resource_name": "organization_access",
                    "permissions": [self.organization_access],
                },
            ]
            require_all = True
        print(
            user_permissions, "--self.recipient_role_name--", self.recipient_role_name
        )
        # get users by role and organization access
        get_recipient_users = Permissions.search_users_by_permissions(
            permissions_include=user_permissions, require_all=require_all
        )
        if get_recipient_users and get_recipient_users["status_code"] != 200:
            print("send mail:- ", "msg: " + str(get_recipient_users["msg"]))
            # return abort(get_recipient_users["status_code"], f'{get_recipient_users["msg"]}')
            return None
        print(
            get_recipient_users,
            "--yes self.recipient_role_name--",
            self.recipient_role_name,
        )
        return get_recipient_users["users"]

    def get_users_by_email(self):
        if not self.user_emails:
            print(f"User emails is required {self.user_emails}")
            return abort(404, "User emails is required")

        # get users by emails
        get_recipient_users = Permissions.get_users_by_email(self.user_emails)
        if get_recipient_users and get_recipient_users["status_code"] != 200:
            print("send mail:- ", "msg: " + str(get_recipient_users["msg"]))
            # return abort(get_recipient_users["status_code"], f'{get_recipient_users["msg"]}')
            return None
        print(
            get_recipient_users,
            "--yes self.user_emails--",
            self.user_emails,
        )
        return get_recipient_users["users"]

    def sender_details(self):
        # sender details
        user = Permissions.get_user_details()
        self.sender_name = (
            user["first_name"] + " " + user["last_name"] if user["user_uuid"] else None
        )
        self.sender_email = user["email"] if user["user_uuid"] else None

    @property
    def current_datetime(self):
        return datetime_to_string_format(fmt="%Y-%m-%d: %H:%M")

    @property
    def app_url(self):
        # Web url
        app_url = os.environ.get("APP_URL")
        if self.recipient_role_name and self.recipient_role_name.lower() == "client":
            app_url = os.environ.get("CLIENT_APP_URL")
        return app_url

    def request_type_details(self):
        # string to lower case
        self.request_type_string = (
            self.request_type.object_as_string().lower() if self.request_type else None
        )

        # request id
        self.request_id = self.request_type.id if self.request_type else None

        # for sending as string in mail
        self.request_id_string = self.request_id

        # for soa
        if self.request_type_string == "soa":
            self.request_id_string = f"{self.request_type.client.ref_client_no}-SOAID{self.request_type.soa_ref_id}"

        # for reserve release
        if self.request_type_string == "reserve release":
            self.request_type_string = self.request_type_string.replace(" ", "-")
            self.request_id_string = f"{self.request_type.get_ref_client_rr_id()}"
            
        # for credit limit
        if self.request_type_string == "credit limit":
            self.request_type_string = self.request_type_string.replace(" ", "-")
            self.request_id_string = f"{self.request_type.get_cl_reference()}"

        # for generic request
        if self.request_type_string == "generic request":
            self.request_type_string = self.request_type_string.replace(" ", "-")
            self.request_id_string = f"{self.request_type.get_gn_reference()}"

        # for compliance repository
        if self.request_type_string == "compliance repository":
            self.request_type_string = self.request_type_string.replace(" ", "-")
            self.request_id_string = f"{self.request_type.get_cr_reference()}"

        # request link and url link
        # for payee
        if self.request_type_string == "payee":
            self.request_link = (
                f"{self.app_url}{self.request_type_string}/{self.request_id}?client_id={self.client_id}"
            )
            self.url_link = f"{self.request_type_string}/{self.request_id}?client_id={self.client_id}"

        else:
            self.request_link = (
                f"{self.app_url}{self.request_type_string}/{self.request_id}"
            )
            self.url_link = f"{self.request_type_string}/{self.request_id}"
        
    def get_request_created_by(self):
        # Get email of user who created request
        if self.recipient_role_name == "client":
            request_created_by_client = self.request_type.request_created_by_client()

            # if request not created by client but submitted by client
            if not request_created_by_client:
                request_created_by_client = (
                    self.request_type.request_submitted_by_client()
                )

            self.request_created_by_client = (
                request_created_by_client.user if request_created_by_client else None
            )

        if self.recipient_role_name == "principal":
            request_created_by_principal = (
                self.request_type.request_created_by_principal()
            )
            # if request not created by principal but submitted
            if not request_created_by_principal:
                request_created_by_principal = (
                    self.request_type.request_submitted_by_principal()
                )

            self.request_created_by_principal = (
                request_created_by_principal.user
                if request_created_by_principal
                else None
            )

    def payee_notification_message(self):
        if self.request_type_string == "payee":
            # Mail to Bo
            if self.recipient_role_name == "bo":
                if self.request_type.status.value == "pending":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Submitted"
                    )
                    # notify_status
                    self.notify_status = "submitted"

                    # notification message
                    self.notification_message = f"We're writing to inform you that {self.sender_name} has submitted {self.request_type.object_as_string()} - {self.request_id_string} for your review."
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was submitted by Principal: {self.sender_name}"

            # Mail to Principal
            if self.recipient_role_name == "principal":
                # approved by bo
                if self.request_type.status.value == "approved":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Approved"
                    )
                    # notify_status
                    self.notify_status = "processed"

                    # notification message
                    self.notification_message = f"We're writing to inform you that {self.sender_name} has approved your {self.request_type.object_as_string()} - {self.request_id_string}."
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Approved by BO: {self.sender_name}"

                # rejected by bo
                if self.request_type.status.value == "rejected":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Rejected"
                    )
                    # notify_status
                    self.notify_status = "rejected"

                    # notification message
                    self.notification_message = f"We're writing to inform you that {self.sender_name} has rejected your {self.request_type.object_as_string()} - {self.request_id_string}."
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Rejected by BO: {self.sender_name}"

                # returned by bo
                if self.request_type.status.value == "action_required":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Action Required"
                    )
                    # notify_status
                    self.notify_status = "sent back"

                    # notification message
                    self.notification_message = f"We're writing to inform you that {self.sender_name} has returned your {self.request_type.object_as_string()} - {self.request_id_string}."
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was returned from BO: {self.sender_name}"

            # Mail to Client
            if self.recipient_role_name == "client":
                if self.request_type.status.value == "action_required_by_client":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Action Required"
                    )
                    # notify_status
                    self.notify_status = "sent back"

                    # notification message
                    self.notification_message = f"We're writing to inform you that {self.sender_name} has returned your {self.request_type.object_as_string()} - {self.request_id_string}."
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was sent back from Principal: {self.sender_name}"

                # rejected by principal
                if self.request_type.status.value == "principal_rejection":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Rejected"
                    )
                    # notify_status
                    self.notify_status = "rejected"

                    # notification message
                    self.notification_message = f"We're writing to inform you that {self.sender_name} has rejected your {self.request_type.object_as_string()} - {self.request_id_string}."
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Rejected by Principal: {self.sender_name}"

    def mails_notification_message(self):
        if (
            self.request_type_string == "soa"
            or self.request_type_string == "reserve-release"
        ):
            # Mail to AE or Client
            if self.recipient_role_name == "ae" or self.recipient_role_name == "client":
                if self.request_type.status.value == "pending":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Submitted"
                    )
                    # notify_status
                    self.notify_status = "submitted"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was submitted by Principal: {self.sender_name}"

                if self.request_type.status.value == "action_required_by_client":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Action Required"
                    )
                    # notify_status
                    self.notify_status = "sent back"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was sent back from Principal: {self.sender_name}"

                # rejected by principal
                if self.request_type.status.value == "principal_rejection":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Rejected"
                    )
                    # notify_status
                    self.notify_status = "rejected"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Rejected by Principal: {self.sender_name}"

            # Mail to Principal or BO
            if (
                self.recipient_role_name == "principal"
                or self.recipient_role_name == "bo"
            ):
                # approved by ae
                if self.request_type.status.value == "approved":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Approved"
                    )
                    # notify_status
                    self.notify_status = "approved"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Approved by A/E: {self.sender_name}"

            # Mail to Principal or AE
            if (
                self.recipient_role_name == "principal"
                or self.recipient_role_name == "ae"
            ):
                if self.request_type.status.value == "completed":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Processed"
                    )
                    # notify_status
                    self.notify_status = "processed"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was REVIEWED by B/O: {self.sender_name}"

                # rejected by ae
                if self.request_type.status.value == "rejected":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Request Rejected"
                    )
                    # notify_status
                    self.notify_status = "rejected"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Rejected by A/E: {self.sender_name}"

                # action_required by ae
                if self.request_type.status.value == "action_required":
                    # subject
                    self.subject = (
                        f"{self.request_type.object_as_string()} Action Required"
                    )
                    # notify_status
                    self.notify_status = "sent back"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was sent back from A/E: {self.sender_name}"
                    
        if self.request_type_string == "credit-limit":
            # Mail to AE
            if self.recipient_role_name == "ae":
                if self.request_type.status.value == "submitted":
                    # subject
                    self.subject = f"New Credit Limit was submitted {self.request_id_string}"
                    # notify_status
                    self.notify_status = "submitted"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was submitted by Principal: {self.sender_name}"
                    
            # Mail to Principal or Client
            if self.recipient_role_name == "principal" or self.recipient_role_name == "client":
                # rejected by ae
                if self.request_type.status.value == "rejected":
                    # subject
                    self.subject = (
                        f"New {self.request_type.object_as_string()} {self.request_id_string} has been REJECTED"
                    )
                    # notify_status
                    self.notify_status = "rejected"
 
                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Rejected by A/E: {self.sender_name}"
                    
                # approved by ae
                if self.request_type.status.value == "approved":
                    # subject
                    self.subject = (
                        f"New {self.request_type.object_as_string()} {self.request_id_string} has been APPROVED"
                    )
                    # notify_status
                    self.notify_status = "approved"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Approved by A/E: {self.sender_name}"

        
        if self.request_type_string == "generic-request":
            # Mail to AE
            if self.recipient_role_name == "ae":
                if self.request_type.status.value == "submitted":
                    # subject
                    self.subject = f"New Other Request was submitted {self.request_id_string} {self.category}"
                    # notify_status
                    self.notify_status = "submitted"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was submitted by Principal: {self.sender_name}"

            # Mail to Principal
            if self.recipient_role_name == "principal":
                # rejected by ae
                if self.request_type.status.value == "rejected":
                    # subject
                    self.subject = f"New Other Request {self.request_id_string} has been REJECTED"
                    # notify_status
                    self.notify_status = "rejected"
 
                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Rejected by A/E: {self.sender_name}"
                    
                # approved by ae
                if self.request_type.status.value == "approved":
                    # subject
                    self.subject = f"New Other Request {self.request_id_string} has been APPROVED"
                    # notify_status
                    self.notify_status = "approved"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Approved by A/E: {self.sender_name}"


        if self.request_type_string == "compliance-repository":
            # Mail to Client
            if self.recipient_role_name == "client":                    
                # approved by principal
                if self.request_type.status.value == "approved":
                    # subject
                    self.subject = (
                        f"New {self.request_type.object_as_string()} {self.request_id_string} has been APPROVED"
                    )
                    # notify_status
                    self.notify_status = "approved"

                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Approved by Principal: {self.sender_name}"

                # rejected by principal
                if self.request_type.status.value == "principal_rejection":
                    # subject
                    self.subject = (
                        f"New {self.request_type.object_as_string()} {self.request_id_string} has been REJECTED"
                    )
                    # notify_status
                    self.notify_status = "rejected"
 
                    # notification message
                    self.save_notification_message = f"{self.current_datetime} {self.request_type.object_as_string()}  - {self.request_id_string} was Rejected by Principal: {self.sender_name}"


    def notify_to_sender(
        self,
        recipient_emails_list=None,
    ):
        if recipient_emails_list:

            recipient_role_name = "Principal"
            if self.recipient_role_name.lower() == "ae":
                recipient_role_name = "AE"

            if self.recipient_role_name.lower() == "bo":
                recipient_role_name = "BO"

            if self.recipient_role_name.lower() == "client":
                recipient_role_name = "Client"

            template_name = os.environ.get("MAIL_RECIPENTS_EMAIL_TO_USER")
            subject = f"List of {recipient_role_name}s notified for {self.request_type.object_as_string()} - {self.request_id_string}"
            emails_list = "<br />".join(map(str, recipient_emails_list))
            notification_message = f"We're writing to inform you that {self.request_type.object_as_string()} - {self.request_id_string} have been {self.notify_status}. The details have been sent to the following {recipient_role_name}'s: <br />{emails_list}"

            data = {
                "sender_email": self.lc_email,
                "sender_name": self.lc_name,
                "recipients": [{"email": self.sender_email, "name": self.sender_name}],
                "bcc": self.bcc_recipients,
                "subject": subject,
                "template_name": template_name,
                "template_data": {
                    "sender_name": self.sender_name,
                    "notification_message": notification_message,
                    "web_url": self.app_url,
                    "branding_logo_url": self.logo_url,
                },
            }

            threading.Thread(target=self.sendgrid_mail, kwargs={"data": data}).start()
            print(
                f"{self.request_status}: sender notified-{self.sender_email} --> {emails_list}"
            )

    def notify_to_sender_ae(
        self,
        recipient_emails_list=None,
    ):
        if recipient_emails_list and self.request_status == "reviewed":
            recipient_role_name = "AE"
            notify_status = self.request_status
            template_name = os.environ.get("MAIL_RECIPENTS_EMAIL_TO_USER")
            subject = f"List of {recipient_role_name}s notified for {self.request_type.object_as_string()} - {self.request_id_string}"
            emails_list = "<br />".join(map(str, recipient_emails_list))
            notification_message = f"We're writing to inform you that {self.request_type.object_as_string()} - {self.request_id_string} have been {notify_status}. The details have been sent to the following {recipient_role_name}'s: <br />{emails_list}"

            data = {
                "sender_email": self.lc_email,
                "sender_name": self.lc_name,
                "recipients": [{"email": self.sender_email, "name": self.sender_name}],
                "bcc": self.bcc_recipients,
                "subject": subject,
                "template_name": template_name,
                "template_data": {
                    "sender_name": self.sender_name,
                    "notification_message": notification_message,
                    "web_url": self.app_url,
                    "branding_logo_url": self.logo_url,
                },
            }

            threading.Thread(target=self.sendgrid_mail, kwargs={"data": data}).start()
            print(
                f"{self.request_status}: sender AE notified-{self.sender_email} --> {emails_list}"
            )
