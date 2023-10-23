import os
from decimal import Decimal

from src.resources.v2.helpers.mails import SendMails
from src.middleware.permissions import Permissions


class PermissionExceptions:
    
    STATUS_REVIEWED = 'reviewed'
    STATUS_APPROVED = 'approved'

    def __init__(self, request_type, disbursement_amount, has_action_required):
        print(f'PermissionExceptions Initialized: {request_type}: {request_type.id}')

        # request_type = SOA|reserve_release
        self.request_type = request_type
        self.app_flow = 'ae'
        self.disbursement_amount = disbursement_amount
        self.approval_limit = Decimal(0)
        self.return_status = None
        self.has_exception = False
        self.has_action_required = has_action_required 
        self.notification_already_sent = False
        self.override_action_required = False
        self.require_all = True
        self.organization_access = []
        if Permissions.get_user_role_permissions()['status_code'] == 200:
            self.organization_access = Permissions.get_user_role_permissions()['organization_access']        
        
        self.can_modify_requests = False
        self.has_can_modify_permission = False
        self.is_request_updated = False

        # if request has been updated by AE
        if self.request_type.is_request_updated():
            self.is_request_updated = True

        # Approval limits
        self.jam_approval_limit = Decimal(50000)
        self.fom_approval_limit = Decimal(1000000)
        self.rm_approval_limit = Decimal(500000)
        self.coo_approval_limit = Decimal(1000000)
        self.cro_approval_limit = Decimal(999999999)
        
        # TODO : add override_action_required in permissions for coo and cro
        # self.override_action_required = True

        #Test
        # self.approval_limit = self.jam_approval_limit
        # self.disbursement_amount = Decimal(60000)
        
        self.set_approval_limit()
        self.check_approval_limit()
        self.check_exceptions()
        
        """
        CASE - 1 (https://unoapp.atlassian.net/browse/LC-818)
        APPROVE if there's no Action Required - JAM 50,000 ---> Notificaton BO (role: approval_permissions_50000)
        Exception: 
        1. NO-Action Required
        *** REVIEW 50,000 - 1,000,000  ---> Notificaton FOM (role: approval_permissions_1000000)
        *** REVIEW > 1,000,000 ----> Notificaton CRO (role: override_approval_permissions)
        2. ACTION REQUIRED
        *** REVIEW 50,000 - 500,000 ---> Notificaton RM
        *** REVIEW 500,000 - 1,000,000 ---> Notificaton COO (role: approval_permissions_1000000)
        *** REVIEW > 1,000,000 ----> Notificaton CRO (role: override_approval_permissions)

        CASE - 2 (https://unoapp.atlassian.net/browse/LC-819)(role: approval_permissions_1000000)
        APPROVE if there's no Action Required - FOM 1,000,000 ---> Notificaton BO 
        Exception:(ACTION REQUIRED)
        *** REVIEW < 1,000,000 ---> Notificaton COO
        *** REVIEW > 1,000,000 ----> Notificaton CRO

        CASE - 3 (https://unoapp.atlassian.net/browse/LC-820) (role: approval_permissions_500000)
        APPROVE if there's no Action Required - RM 500,000 ---> Notificaton BO 
        Exception:(ACTION REQUIRED)
        *** REVIEW < 1,000,000 ---> Notificaton COO
        *** REVIEW > 1,000,000 ----> Notificaton CRO

        Case - 4 (https://unoapp.atlassian.net/browse/LC-821) (role: approval_permissions_1000000)
        
        APPROVE if there's [action-required was earlier]-earlier Action Required - COO 1,000,000 ---> Notificaton BO 
        Exception:(ACTION REQUIRED)
        *** REVIEW > 1,000,000 ----> Notificaton CRO

        CASE - 5 (https://unoapp.atlassian.net/browse/LC-822) (role: override_approval_permissions)
        CRO NO LIMIT ---> Notificaton BO 

        CASE - 6 (new requirements - which will throw things off!) : override_permissions_case
        Any user who has override permissions + limit ---> should be able to approve.

        CASE - 7 (https://unoapp.atlassian.net/browse/LC-1312) : can_modify case
        Any user who has can_modify permissions + limit ---> should be able to approve.
        """

    def can_review(self):
        self.return_status = self.STATUS_REVIEWED

    def can_approve(self):
        self.return_status = self.STATUS_APPROVED

    
    def set_approval_limit(self):
        user_permissions = Permissions.get_user_role_permissions(active=True)
        # print(user_permissions)
        user_role = user_permissions["user_role"]
        if (
            user_role == self.app_flow
            and user_permissions["user_permissions"]["approval_limit"]
        ):
            self.approval_limit = Decimal(
                list(user_permissions["user_permissions"]["approval_limit"].keys())[0]
            )

        misc_permissions = (
            user_permissions["user_permissions"]["misc_permissions"]
            if "misc_permissions" in user_permissions["user_permissions"]
            else None
        )
        if (
            misc_permissions
            and "override_action_required" in misc_permissions
            and misc_permissions["override_action_required"]
        ):
            self.override_action_required = True

        if (
            misc_permissions
            and "can_modify" in misc_permissions
            and misc_permissions["can_modify"]
        ):
            self.has_can_modify_permission = True
            
        self.can_modify_requests = self.has_can_modify_permission or (
            not self.has_can_modify_permission and not self.is_request_updated
        )
    
    def notify_to_fom(self):
        action_required = self.has_action_required
        has_limit = (self.disbursement_amount > self.jam_approval_limit and self.disbursement_amount <= self.fom_approval_limit)
        is_jam = (self.jam_approval_limit == self.approval_limit)
        is_rm = (self.rm_approval_limit == self.approval_limit)
        if not action_required and has_limit and (is_jam or is_rm):
            self.can_review()
            permissions_include = [
                {
                    "app_resource_name": "approval_limit",
                    "permissions": ["1000000"]
                },
                {
                    "app_resource_name": "app_flow",
                    "permissions": ["ae"]
                },
                {
                    "app_resource_name": "organization_access",
                    "permissions": self.organization_access
                }
            ]
            permissions_exclude = [
                {
                    "app_resource_name": "misc_permissions",
                    "permissions": [
                        "override_action_required"
                    ]
                }
            ]
            # role = 'factoring_operations_manager'
            self.send_notifications(permissions_include=permissions_include, permissions_exclude=permissions_exclude)

    def notify_to_rm(self):
        action_required = self.has_action_required
        has_limit = (self.disbursement_amount > self.jam_approval_limit and self.disbursement_amount <= self.rm_approval_limit)
        is_jam = (self.jam_approval_limit == self.approval_limit)
        
        if action_required and has_limit and is_jam:
            self.can_review()
            permissions_include = [
                    {
                        "app_resource_name": "approval_limit",
                        "permissions": ["500000"]
                    },
                    {
                        "app_resource_name": "app_flow",
                        "permissions": ["ae"]
                    },
                    {
                        "app_resource_name": "organization_access",
                        "permissions": self.organization_access
                    }
            ]
            # role = 'relationship_manager'
            self.send_notifications(permissions_include=permissions_include)

    def notify_to_coo(self):
        action_required = self.has_action_required
        has_limit = (self.disbursement_amount <= self.coo_approval_limit)
        
        if action_required and has_limit:
            self.can_review()
            permissions_include = [
                    {
                        "app_resource_name": "approval_limit",
                        "permissions": ["1000000"]
                    },
                    {
                        "app_resource_name": "app_flow",
                        "permissions": ["ae"]
                    },
                    {
                        "app_resource_name": "misc_permissions",
                        "permissions": ["override_action_required"]
                    },
                    {
                        "app_resource_name": "organization_access",
                        "permissions": self.organization_access
                    }
            ]
            # role = 'chief_operation_officer'
            self.send_notifications(permissions_include=permissions_include)

    def notify_to_cro(self):
        has_limit = (self.disbursement_amount > self.coo_approval_limit)
        
        if has_limit:
            self.can_review()
            permissions_include = [
                    {
                        "app_resource_name": "approval_limit",
                        "permissions": ["999999999"]
                    },
                    {
                        "app_resource_name": "app_flow",
                        "permissions": ["ae"]
                    },
                    {
                        "app_resource_name": "misc_permissions",
                        "permissions": ["override_action_required"]
                    }
            ]
            # role = 'chief_risk_officer'
            self.send_notifications(permissions_include=permissions_include)

    def notify_to_can_modify_users(self):
        self.can_review()
        permissions_include = [
            {
                "app_resource_name": "misc_permissions",
                "permissions": ["can_modify"]
            },
            {
                "app_resource_name": "app_flow",
                "permissions": ["ae"]
            },
            {
                "app_resource_name": "organization_access",
                "permissions": self.organization_access
            }
        ]
        self.send_notifications(permissions_include=permissions_include)


    def check_exceptions(self):
        # IF there's NOT action-required associated to SOA - and I've limit 50K?
        # IF there's any action-required associated to SOA?
        # override -- permissions
        # self.notify_to_fom()
        if not self.has_exception:
            print(f'No Exceptions for {self.request_type}: {self.request_type.id}')
            return
        
        self.notify_to_rm()
        self.notify_to_fom()
        self.notify_to_coo()
        self.notify_to_cro()
        self.notify_to_can_modify_users()
        

    def send_notifications(self, permissions_include=None, permissions_exclude=None):
        if not self.notification_already_sent and len(permissions_include):
            self.notification_already_sent = True # So that we're not sending emails in loop.
            print(f'Notifications has been sent to role: {permissions_include} {permissions_exclude}')
            # Send email
            user_emails = Permissions.search_users_by_permissions(permissions_include=permissions_include, require_all=self.require_all, permissions_exclude=permissions_exclude)['user_emails']
            print( '--user_emails--', user_emails, permissions_include, permissions_exclude)
            # get client_id
            client_id = self.request_type.client_id
            if len(user_emails):
                send_mails = SendMails(
                    request_type=self.request_type,
                    client_id=client_id,
                    request_status=self.STATUS_REVIEWED,
                    user_emails=user_emails
                )
                send_mails.send_permission_exception_mail()


    def check_approval_limit(self):
        #TODO: Check for pending & reviewed.
        action_required = self.has_action_required
        can_modify_requests = self.can_modify_requests
        can_approve =  self.disbursement_amount <= self.approval_limit and can_modify_requests

        normal_case = not action_required and can_approve
        coo = self.override_action_required and (self.coo_approval_limit == self.approval_limit) and can_approve
        cro = (self.cro_approval_limit == self.approval_limit) and self.override_action_required
        
        #TODO: It's a hot fix. Need to revisit old requirements sooner or later.
        override_permissions_case = self.override_action_required and can_approve

        print('Permissions:', {
            'normal_case': normal_case,
            'coo': coo,
            'cro': cro,
            'override_permissions_case': override_permissions_case,
            'can_modify_case': can_modify_requests,
        })
        if normal_case or coo or cro or override_permissions_case:
            self.can_approve()
        else:
            self.has_exception = True
            self.can_review()


    def get(self):
       return {
           'status' :  self.return_status,
           'approval_limit': self.approval_limit,
           'disbursement_amount': self.disbursement_amount,
           'exception': self.has_exception,
           'action_required': self.has_action_required,
           'can_modify_requests': self.has_can_modify_permission,
           'is_request_updated': self.is_request_updated,
       }
