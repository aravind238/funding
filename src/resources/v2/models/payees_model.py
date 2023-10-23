from src import db
import enum
from datetime import datetime, timedelta
import math
from src.models import *
from src.middleware.organization import Organization
from sqlalchemy import cast, Date, and_, or_, not_, DateTime
from src.middleware.permissions import Permissions
from src.resources.v2.models.client_payees_model import PayeePaymentStatus



class PayeeStatus(enum.Enum):
    action_required = "action_required"
    action_required_by_client = "action_required_by_client"
    approved = "approved"
    client_draft = "client_draft"
    client_submission = "client_submission"
    draft = "draft"
    pending = "pending"
    principal_rejection = "principal_rejection"
    rejected = "rejected"


class Payee(db.Model):
    """ Payee model """

    __tablename__ = "payees"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    account_nickname = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(PayeeStatus), default=PayeeStatus.pending.value, server_default=PayeeStatus.pending.value)
    address_line_1 = db.Column(db.String(255), nullable=True)
    # address_line_2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    state_or_province = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(255), nullable=True)
    postal_code = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(100), nullable=True)
    alt_phone = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_new = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    # back relationship
    client_payee = db.relationship("ClientPayee", backref="payee")
    approvals_history = db.relationship("ApprovalsHistory", backref="payee")

    def __init__(self, data):
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.account_nickname = data.get("account_nickname")
        self.status = data.get("status")
        self.address_line_1 = data.get("address_line_1")
        # self.address_line_2 = data.get("address_line_2")
        self.city = data.get("city")
        self.state_or_province = data.get("state_or_province")
        self.country = data.get("country")
        self.postal_code = data.get("postal_code")
        self.phone = data.get("phone")
        self.alt_phone = data.get("alt_phone")
        self.email = data.get("email")
        self.notes = data.get("notes")
        self.is_deleted = data.get("is_deleted")
        self.is_new = data.get("is_new")
        self.is_active = data.get("is_active")
        self.last_processed_at = data.get("last_processed_at")
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

    def archive(self):
        from src.models import ClientPayee
        
        ClientPayee.query.filter_by(payee_id=self.id, is_deleted=False).update(
            {
                ClientPayee.is_deleted: True,
                ClientPayee.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )

        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.save()

    def add_payee_payment_status(self, payment_status=None):
        from src.models import ClientPayee
        
        # add client payee payment status
        ClientPayee.query.filter_by(payee_id=self.id, is_deleted=False).update(
            {
                ClientPayee.payment_status: payment_status,
            },
            synchronize_session="fetch",
        )

        db.session.commit()

    def add_payee_internal_comments(self, internal_comments=None):
        from src.models import Comments

        # user details
        get_user_detail = Permissions.get_user_details()
        user_email = get_user_detail["email"]

        # add payee internal comments
        payee_internal_comments_obj = {
            "payee_id": self.id,
            "comment": internal_comments,
            "tags": "Internal Comments",
            "added_by": user_email
        }

        update_comment = Comments.query.filter_by(
            payee_id=self.id, is_deleted=False, tags="Internal Comments"
        ).order_by(Comments.id.desc()).first()
        if update_comment:
            update_comment.comment = internal_comments
            update_comment.save()
        else:
            add_payee_internal_comments = Comments(payee_internal_comments_obj)
            add_payee_internal_comments.save()

    @staticmethod
    def get_all_payee():
        return Payee.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_payee(id):
        return Payee.query.filter_by(id=id, is_deleted=False).first()

    @staticmethod
    def get_one_based_off_control_accounts(id):
        from src.models import (
            Client,
            ClientPayee,
            ControlAccount,
            ClientControlAccounts,
        )

        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]
        
        return (
            Payee.query.filter(
                ClientPayee.payee_id == Payee.id,
                Client.id == ClientPayee.client_id,
                Payee.is_deleted == False,
                ClientPayee.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                ClientControlAccounts.client_id == Client.id,
                ControlAccount.id == ClientControlAccounts.control_account_id,
                ControlAccount.name.in_(business_control_accounts),
                Payee.id == id
            )
            .first()
        )
    
    def object_as_string(self):
        return "Payee"

    def get_payee_lcra_client_accounts_id(self):
        from src.models import ClientPayee

        client_payee = ClientPayee.query.filter_by(
            payee_id=self.id
        ).first()

        payee_lcra_client_accounts_id = client_payee.client.lcra_client_accounts_id if client_payee and client_payee.client else None

        return payee_lcra_client_accounts_id
    
    def get_payee_payment_status(self, client_id):
        from src.models import ClientPayee

        # client_payee
        client_payee = ClientPayee.get_by_client_payee_id(client_id, self.id)

        client_payee_payment_status = client_payee.payment_status if client_payee and client_payee.payment_status in PayeePaymentStatus else None

        return client_payee_payment_status
    
    def get_payee_internal_comments(self):
        from src.models import Comments

        return Comments.query.filter(
            Comments.payee_id == self.id, 
            Comments.is_deleted == False,
            Comments.tags == "Internal Comments"
        ).order_by(Comments.id.desc()).first()

    def request_submitted_by_principal(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            payee_id=self.id, key="submitted_at", is_deleted=False
        ).first()

    def request_created_by_principal(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            payee_id=self.id, key="created_at", is_deleted=False
        ).first()

    def request_created_by_client(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            payee_id=self.id, 
            key="client_created_at", 
            is_deleted=False
        ).first()

    def payee_approvals_history(self):
        from src.resources.v2.models.approvals_history_model import ApprovalsHistory
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        submission_activity = []
        approvals_history = ApprovalsHistory.query.filter_by(
            payee_id = self.id,
            # is_deleted = False
        )

        if approvals_history:
            submitted_by_client = 0
            submitted_by_principal = 0
            is_request_approved = False
            for each_history in approvals_history:
                history_status = None
                if each_history.key == "action_required":
                    history_status = "BO Action Required to Principal"

                if each_history.key == "action_required_by_client":
                    history_status = "Principal Action Required to Client"

                if each_history.key == "approved_at":
                    history_status = "Approved by BO"
                    is_request_approved = True

                if (
                    (
                        self.status.value == "client_draft"
                        or self.status.value == "draft"
                    )
                    and (
                        each_history.key == "client_created_at"
                        or each_history.key == "created_at"
                    )
                ):
                    history_status = "Created by"

                if each_history.key == "client_submission_at":
                    history_status = "Submitted by Client"
                    submitted_by_client += 1

                if each_history.key == "submitted_at":
                    history_status = "Submitted by Principal"
                    submitted_by_principal += 1

                if each_history.key == "principal_rejection_at":
                    history_status = "Rejected by Principal"

                if each_history.key == "rejected_at":
                    history_status = "Rejected by BO"

                # if each_history.key == "updated_at":
                #     history_status = "Updated by AE"

                if (
                    submitted_by_client > 1
                    and each_history.key == "client_submission_at"
                ):
                    history_status = "Resubmitted by Client"

                if (
                    submitted_by_principal > 1 
                    and each_history.key == "submitted_at"
                ):
                    history_status = "Resubmitted by Principal"

                # Need Payee approvals history for Payment Status and Internal Comments Activity Logs LC-2317
                if each_history.key == "payment_status_added_at":
                    history_status = "Payment Status Added by BO"

                if each_history.key == "payment_status_updated_at":
                    history_status = "Payment Status Updated by BO"

                if each_history.key == "internal_comments_added_at":
                    history_status = "Internal Comments Added by BO"

                if each_history.key == "internal_comments_updated_at":
                    history_status = "Internal Comments Updated by BO"

                if each_history.key == "payment_status_and_internal_comments_added_at":
                    history_status = "Payment Status and Internal Comments Added by BO"

                if each_history.key == "payment_status_and_internal_comments_updated_at":
                    history_status = "Payment Status and Internal Comments Updated by BO"
                
                # submission activity
                if (
                    history_status
                    and each_history.key in [
                        "client_created_at",
                        "created_at",
                        "client_submission_at",
                        "submitted_at",
                        "approved_at",
                    ]
                ):
                    # not to add resubmitted request
                    if (
                        history_status not in [
                            "Resubmitted by Client", 
                            "Resubmitted by Principal"
                        ]
                    ):
                        submission_activity.append(
                            {
                            "added_at": utc_to_local(dt=each_history.created_at.isoformat()),
                            "description": history_status,
                            "user": each_history.user,
                            }
                        )
                
                # activity log
                if (
                    each_history.key == "client_created_at"
                    or each_history.key == "created_at"
                ):
                    history_status = "Created by"
                    payee_created_by = {
                        "added_at": utc_to_local(dt=each_history.created_at.isoformat()),
                        "user": each_history.user,
                    }
                
                if history_status:
                    activity_log.append(
                        {
                            "added_at": utc_to_local(dt=each_history.created_at.isoformat()),
                            "description": history_status,
                            "user": each_history.user,
                        }
                    )

                if (
                    each_history.key == "client_submission_at"
                    or each_history.key == "submitted_at"
                ):  
                    if (
                        submitted_by_client == 1 and submitted_by_principal == 0 
                        or 
                        submitted_by_client == 0 and submitted_by_principal == 1
                    ):
                        payee_submitted_by = {
                            "added_at": utc_to_local(dt=each_history.created_at.isoformat()),
                            "user": each_history.user,
                        }


        return {
            "activity_log": activity_log,
            "submission_activity": submission_activity,
        }

    def payee_comments(self):
        from src.resources.v2.models.comments_model import Comments

        payee_comments = Comments.query.filter(
            Comments.payee_id == self.id, 
            Comments.is_deleted == False,
            Comments.tags != "Internal Comments"
        ).all()

        return payee_comments

    def payee_supporting_documents(self):
        from src.resources.v2.models.supporting_documents_model import SupportingDocuments

        supporting_documents = SupportingDocuments.query.filter_by(
            payee_id=self.id, is_deleted=False
        ).all()
        
        return supporting_documents
    
    def get_soa_by_payee(self):
        from src.models import Disbursements, SOA
        
        soa = SOA.query.outerjoin(
                Disbursements,
                and_(
                    Disbursements.ref_type == "soa",
                    Disbursements.ref_id == SOA.id,
                    Disbursements.is_deleted == False,
                ),
            ).filter(
                SOA.is_deleted == False,
                not_(
                    SOA.status.in_(
                        [
                            "completed",
                            "rejected",
                        ]
                    )
                ),                
                Disbursements.payee_id == self.id,
            ).group_by(
                SOA.id
            ).all()
            
        return soa
    
    def get_rr_by_payee(self):
        from src.models import Disbursements, ReserveRelease

        reserve_release = (
            ReserveRelease.query.outerjoin(
                Disbursements,
                and_(
                    Disbursements.ref_type == "reserve_release",
                    Disbursements.ref_id == ReserveRelease.id,
                    Disbursements.is_deleted == False,
                ),
            )
            .filter(
                ReserveRelease.is_deleted == False,
                not_(
                    ReserveRelease.status.in_(
                        [
                            "completed",
                            "rejected",
                        ]
                    )
                ),
                Disbursements.payee_id == self.id,
            )
            .group_by(ReserveRelease.id)
            .all()
            )

        return reserve_release

    def reasons(self, status=""):
        from src.models import ApprovalsHistory, Reasons

        history_status = status
        if status == "rejected":
            history_status = "rejected_at"

        reasons = ApprovalsHistory.query.filter(
            ApprovalsHistory.payee_id == self.id, ApprovalsHistory.is_deleted == False
        )

        if history_status:
            reasons = reasons.filter(ApprovalsHistory.key == history_status)
        else:
            reasons = reasons.filter(
                ApprovalsHistory.key.in_(["action_required", "rejected_at"])
            )

        reasons = reasons.order_by(ApprovalsHistory.id.desc()).all()
        return reasons

class PayeeListing:

    def get_all():

        from src.models import (
            Payee,
            Client,
            ClientPayee
        )
        from src.resources.v2.schemas import PayeeSchema
        payee_schema = PayeeSchema(many=True)

        # Organization 
        get_locations = Organization.get_locations()
        client_id = get_locations["client_list"]

        get_client_payee = ClientPayee.query.filter(
            ClientPayee.is_deleted == False, ClientPayee.client_id.in_(client_id)
        )
        client_payee_id = []
        for client_payee in get_client_payee:
            client_payee_id.append(client_payee.payee_id)

        payees = Payee.query.filter(
            Payee.is_deleted == False, Payee.is_active == True, Payee.id.in_(client_payee_id)
        )

        payee_results = payee_schema.dump(payees).data

        if len(payee_results) < 1:
            return None

        for payee in payee_results:
            payee_obj = Payee.get_one_payee(payee["id"])
            clients_payee_obj = payee_obj.client_payee
            if clients_payee_obj:
                client_name = Client.get_one_client(clients_payee_obj[0].client_id).name
                client_id = clients_payee_obj[0].client_id
            else:
                client_name = None
                client_id = None
                
            payee["client_id"] = client_id
            payee["client_name"] = client_name

        return payee_results

    def get_paginated_payees(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        start_date = kwargs.get("start_date", None)
        end_date = kwargs.get("end_date", None)
        control_account = kwargs.get("control_account", None)
        stage = kwargs.get("stage", None)
        active = kwargs.get("active", None)
        dashboard = kwargs.get("dashboard", False)
        client_id_list = kwargs.get("client_ids", None)
        user_role = kwargs.get("user_role", None)
        business_control_accounts = kwargs.get("business_control_accounts", [])
        
        from src.models import (
            Payee,
            Client,
            ClientPayee,
            ControlAccount,
            ClientControlAccounts,
        )
        from src.resources.v2.schemas import (
            PayeeClientSchema,
            PayeeDashboardSchema
        )
        payee_client_schema = PayeeClientSchema(many=True)

        if not dashboard:
            # Organization
            get_locations = Organization.get_locations()
            client_id_list = get_locations["client_list"]

            # user role
            user_role = get_locations["user_role"]
            
            # control accounts
            business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        if dashboard:
            payee_client_schema = PayeeDashboardSchema(many=True)
            
            payee_client_query = (
                Payee.query.filter(
                    ClientPayee.payee_id == Payee.id,
                    Client.id == ClientPayee.client_id,
                    Payee.is_deleted == False,
                    ClientPayee.is_deleted == False,
                    Client.id.in_(client_id_list),
                    Client.is_deleted == False,
                    Client.is_active == True,
                    ControlAccount.is_deleted == False,
                    ClientControlAccounts.is_deleted == False,           
                    not_(
                        Payee.status.in_(
                            [
                                "action_required_by_client",
                                "client_draft",
                                "principal_rejection",
                            ]
                        )
                    ),
                    ClientControlAccounts.client_id == Client.id,
                    ControlAccount.id == ClientControlAccounts.control_account_id,
                    ControlAccount.name.in_(business_control_accounts),
                )
                .group_by(Payee.id)
            )
        else:
            payee_client_query = (
                db.session.query(
                    Payee.id,
                    Payee.first_name,
                    Payee.last_name,
                    Payee.account_nickname,
                    Payee.status,
                    Payee.address_line_1,
                    # Payee.address_line_2,
                    Payee.city,
                    Payee.state_or_province,
                    Payee.country,
                    Payee.postal_code,
                    Payee.phone,
                    Payee.alt_phone,
                    Payee.email,
                    Payee.notes,
                    Payee.is_new,
                    Payee.is_active,
                    Payee.last_processed_at,
                    Payee.created_at,
                    Payee.updated_at,
                    Client.id.label("client_id"),
                    Client.name.label("client_name"),
                    ClientPayee.ref_type.label("ref_type"),
                    ClientPayee.payment_status.label("payment_status"),
                )
                .filter(
                    ClientPayee.payee_id == Payee.id,
                    Client.id == ClientPayee.client_id,
                    Payee.is_deleted == False,
                    ClientPayee.is_deleted == False,
                    Client.id.in_(client_id_list),
                    Client.is_deleted == False,
                    Client.is_active == True,
                    ControlAccount.is_deleted == False,
                    ClientControlAccounts.is_deleted == False, 
                    not_(
                        Payee.status.in_(
                            [
                                "action_required_by_client",
                                "client_draft",
                                "principal_rejection",
                            ]
                        )
                    ),
                    ClientControlAccounts.client_id == Client.id,
                    ControlAccount.id == ClientControlAccounts.control_account_id,
                    ControlAccount.name.in_(business_control_accounts),
                )
                .group_by(Payee.id)
            )

        # get payee having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            payee_client_query = payee_client_query.filter(
                Payee.status != "client_submission"
            )

        # filter by control_account
        if control_account:
            payee_client_query = payee_client_query.filter(
                ControlAccount.id == control_account
            )

        # filter by is_active
        if active is not None:
            if active == "active":
                payee_client_query = payee_client_query.filter(Payee.is_active == True)
            
            if active == "inactive":
                payee_client_query = payee_client_query.filter(Payee.is_active == False)

        # filter for status
        if stage:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                payee_client_query = payee_client_query.filter(
                    Payee.status.in_(stages_split)
                )
            else:
                if stage == "archived":
                    payee_client_query = payee_client_query.filter(
                        or_(
                            Payee.status == "approved"
                        )
                    )
                elif stage == "rejected":
                    payee_client_query = payee_client_query.filter(
                        Payee.status == "rejected"
                    )
                elif stage == "approved":
                    from src.resources.v2.helpers.convert_datetime import date_concat_time
                    # current est date: for comparing with last_processed_at(utc)
                    today = date_concat_time(date_concat="current")
                    next_day = date_concat_time(date_concat="next")

                    payee_client_query = payee_client_query.filter(
                        Payee.status == "approved",
                        cast(Payee.last_processed_at, DateTime) >= today,
                        cast(Payee.last_processed_at, DateTime) <= next_day,
                    )
                else:
                    payee_client_query = payee_client_query.filter(
                        Payee.status == stage
                    )

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                payee_client_query = payee_client_query.filter(
                    Payee.last_processed_at >= start_date,
                    Payee.last_processed_at < (start_date + timedelta(days=1))
                )
            else:
                payee_client_query = payee_client_query.filter(
                    Payee.last_processed_at > start_date,
                    Payee.last_processed_at < (end_date + timedelta(days=1))
                )
        elif start_date:
            payee_client_query = payee_client_query.filter(
                Payee.last_processed_at >= start_date
            )
        elif end_date:
            payee_client_query = payee_client_query.filter(
                Payee.last_processed_at < (end_date + timedelta(days=1))
            )

        # ordering
        if ordering is not None:
            if "date" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.last_processed_at.asc()
                )

            if "-date" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.last_processed_at.desc()
                )

            
            if "status" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.status.asc()
                )

            if "-status" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.status.desc()
                )

            if "account_nickname" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.account_nickname.asc()
                )

            if "-account_nickname" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.account_nickname.desc()
                )

            if "id" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.id.asc()
                )

            if "-id" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Payee.id.desc()
                )

            if "client_name" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Client.name.asc()
                )

            if "-client_name" == ordering:
                payee_client_query = payee_client_query.order_by(
                    Client.name.desc()
                )
        else:
            payee_client_query = payee_client_query.order_by(
                Payee.updated_at.desc()
            )

        # search
        if search is not None:
            payee_client_query = payee_client_query.filter(
                (Payee.account_nickname.like("%" + search + "%"))
                | (Payee.id.like("%" + search + "%"))
                | (Client.name.like("%" + search + "%"))
            )

        # pagination
        payee_objects_queryset = payee_client_query.paginate(page, rpp, False)
        total_pages = math.ceil(payee_objects_queryset.total / rpp)
        payee_data_list = payee_client_schema.dump(payee_objects_queryset.items).data
        total_count = payee_objects_queryset.total
        db.session.commit()

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(payee_data_list) < 1:
            return {
                "msg": get_invalid_page_msg,
                "per_page": rpp,
                "current_page": page,
                "total_pages": 0,
                "total_count": 0,
                "data": [],
            }

        return {
            "msg": "Records found",
            "per_page": rpp,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "data": payee_data_list,
        }
