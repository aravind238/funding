from src import db
import enum
from datetime import datetime, timedelta
from src.models import *
from src.middleware.organization import Organization
from sqlalchemy import cast, Date, and_, or_, not_, DateTime
from src.middleware.permissions import Permissions


class GenericRequestCategoryStatus(enum.Enum):
    adjustment = "adjustment"
    chargeback = "chargeback"
    credit_note = "credit_note"
    other = "other"
    transfer = "transfer"


class GenericRequestStatus(enum.Enum):
    approved = "approved"
    draft = "draft"
    rejected = "rejected"
    submitted = "submitted"


class GenericRequest(db.Model):
    """Generic Request model"""

    __tablename__ = "lc_generic_request"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    category = db.Column(
        db.Enum(GenericRequestCategoryStatus),
        default=GenericRequestCategoryStatus.adjustment.value,
        server_default=GenericRequestCategoryStatus.adjustment.value,
    )
    status = db.Column(
        db.Enum(GenericRequestStatus),
        default=GenericRequestStatus.draft.value,
        server_default=GenericRequestStatus.draft.value,
    )
    notes = db.Column(db.Text, nullable=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.category = data.get("category")
        self.status = data.get("status")
        self.notes = data.get("notes")
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

    @staticmethod
    def get_all():
        return GenericRequest.query.filter(GenericRequest.deleted_at == None)

    @staticmethod
    def get_one(id):
        return GenericRequest.query.filter(
            GenericRequest.id == id, GenericRequest.deleted_at == None
        ).first()

    @staticmethod
    def get_one_based_off_control_accounts(id, active_client=False):
        from src.models import (
            Client,
            ControlAccount,
            ClientControlAccounts,
        )

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        generic_request = GenericRequest.query.filter(
            Client.id == GenericRequest.client_id,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            ClientControlAccounts.client_id == Client.id,
            ControlAccount.id == ClientControlAccounts.control_account_id,
            ControlAccount.name.in_(business_control_accounts),
            GenericRequest.id == id,
        )

        if active_client:
            generic_request = generic_request.filter(Client.is_active == True)

        generic_request = generic_request.first()
        return generic_request

    def object_as_string(self):
        return "Generic Request"

    def request_created_by_principal(self):
        from src.models import GenericRequestApprovalsHistory

        return GenericRequestApprovalsHistory.query.filter_by(
            generic_request_id=self.id, key="created_at", deleted_at=None
        ).first()

    def request_submitted_by_principal(self):
        from src.models import GenericRequestApprovalsHistory

        return GenericRequestApprovalsHistory.query.filter_by(
            generic_request_id=self.id, key="submitted_at", deleted_at=None
        ).first()

    def request_rejected_by_ae(self):
        from src.models import GenericRequestApprovalsHistory

        return (
            GenericRequestApprovalsHistory.query.filter_by(
                generic_request_id=self.id, key="rejected_at", deleted_at=None
            )
            .order_by(GenericRequestApprovalsHistory.id.desc())
            .first()
        )

    def request_approved_by_ae(self):
        from src.models import GenericRequestApprovalsHistory

        return (
            GenericRequestApprovalsHistory.query.filter_by(
                generic_request_id=self.id, key="approved_at", deleted_at=None
            )
            .order_by(GenericRequestApprovalsHistory.id.desc())
            .first()
        )

    def get_gn_reference(self):
        ref_client_no = self.client.ref_client_no if self.client else None
        cl_ref = f"{ref_client_no}-GNID{self.id}"
        return cl_ref

    def get_client_name(self):
        return self.client.name if self.client else None

    def get_approval_history(self):
        approval_history = {}
        if self.status.value == "draft":
            approval_history = self.request_created_by_principal()
        if self.status.value == "submitted":
            approval_history = self.request_submitted_by_principal()
        if self.status.value == "rejected":
            approval_history = self.request_rejected_by_ae()
        if self.status.value == "approved":
            approval_history = self.request_approved_by_ae()
        
        return approval_history

    def gn_approvals_history(self):
        from src.resources.v2.models.generic_request_approvals_history_model import (
            GenericRequestApprovalsHistory,
        )
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        submission_activity = []
        approvals_history = GenericRequestApprovalsHistory.query.filter_by(
            generic_request_id=self.id,
        )

        if approvals_history:
            submitted_by_client = 0
            submitted_by_principal = 0
            for each_history in approvals_history:
                history_status = None

                if each_history.key == "approved_at":
                    history_status = "Approved by AE"

                if (
                    self.status.value == "client_draft" or self.status.value == "draft"
                ) and (
                    each_history.key == "client_created_at"
                    or each_history.key == "created_at"
                ):
                    history_status = "Created by"

                if each_history.key == "client_submission_at":
                    history_status = "Submitted by Client"
                    submitted_by_client += 1

                if each_history.key == "submitted_at":
                    history_status = "Submitted by Principal"
                    submitted_by_principal += 1

                if each_history.key == "rejected_at":
                    history_status = "Rejected by AE"

                if (
                    submitted_by_client > 1
                    and each_history.key == "client_submission_at"
                ):
                    history_status = "Resubmitted by Client"

                if submitted_by_principal > 1 and each_history.key == "submitted_at":
                    history_status = "Resubmitted by Principal"

                # submission activity
                if history_status and each_history.key in [
                    "client_created_at",
                    "created_at",
                    "client_submission_at",
                    "submitted_at",
                    "approved_at",
                ]:
                    # not to add resubmitted request
                    if history_status not in [
                        "Resubmitted by Client",
                        "Resubmitted by Principal",
                    ]:
                        submission_activity.append(
                            {
                                "added_at": utc_to_local(
                                    dt=each_history.created_at.isoformat()
                                ),
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
                    generic_request_created_by = {
                        "added_at": utc_to_local(
                            dt=each_history.created_at.isoformat()
                        ),
                        "user": each_history.user,
                    }

                if history_status:
                    activity_log.append(
                        {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "description": history_status,
                            "user": each_history.user,
                        }
                    )

                if (
                    each_history.key == "client_submission_at"
                    or each_history.key == "submitted_at"
                ):
                    if (
                        submitted_by_client == 1
                        and submitted_by_principal == 0
                        or submitted_by_client == 0
                        and submitted_by_principal == 1
                    ):
                        generic_request_submitted_by = {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "user": each_history.user,
                        }

        return {
            "activity_log": activity_log,
            "submission_activity": submission_activity,
        }

    def comments(self):
        from src.resources.v2.models.comments_model import Comments

        generic_request_comments = Comments.query.filter_by(
            generic_request_id=self.id, is_deleted=False
        ).all()

        return generic_request_comments

    def supporting_documents(self):
        from src.resources.v2.models.supporting_documents_model import (
            SupportingDocuments,
        )

        supporting_documents = SupportingDocuments.query.filter_by(
            generic_request_id=self.id, is_deleted=False
        ).all()

        return supporting_documents

    def reasons(self):
        from src.resources.v2.models.generic_request_approvals_history_model import (
            GenericRequestApprovalsHistory,
        )

        reasons = GenericRequestApprovalsHistory.query.filter(
            GenericRequestApprovalsHistory.generic_request_id == self.id,
            GenericRequestApprovalsHistory.deleted_at == None,
            GenericRequestApprovalsHistory.key == "rejected_at",
        ).all()

        return reasons


class GenericRequestListing:
    def get_all():
        from src.models import (
            GenericRequest,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import GenericRequestRefSchema

        generic_request_schema = GenericRequestRefSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        generic_request = (
            GenericRequest.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                GenericRequest.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                GenericRequest.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts),
            )
            .order_by(GenericRequest.updated_at.desc())
            .all()
        )

        data_results = generic_request_schema.dump(generic_request, many=True).data

        return data_results

    def get_paginated(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        start_date = kwargs.get("start_date", None)
        end_date = kwargs.get("end_date", None)
        control_account = kwargs.get("control_account", None)
        stage = kwargs.get("stage", None)
        dashboard = kwargs.get("dashboard", False)
        client_ids = kwargs.get("client_ids", None)
        user_role = kwargs.get("user_role", None)
        business_control_accounts = kwargs.get("business_control_accounts", [])

        from src.models import (
            GenericRequest,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import (
            GenericRequestRefSchema,
            GenericRequestDashboardSchema,
        )

        generic_request_schema = GenericRequestDashboardSchema(many=True)

        if not dashboard:
            # client ids
            get_locations = Organization.get_locations()
            client_ids = get_locations["client_list"]

            # user role
            user_role = get_locations["user_role"]

            # control accounts
            business_control_accounts = Permissions.get_business_settings()[
                "control_accounts"
            ]

        generic_request = GenericRequest.query.join(
            Client, ClientControlAccounts, ControlAccount
        ).filter(
            GenericRequest.deleted_at == None,
            Client.is_deleted == False,
            Client.is_active == True,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            GenericRequest.client_id.in_(client_ids),
            ControlAccount.name.in_(business_control_accounts),
        )

        # get generic request having status == draft only for principal
        if user_role and user_role.lower() != "principal":
            generic_request = generic_request.filter(
                not_(
                    GenericRequest.status.in_(
                        [
                            "draft",
                        ]
                    )
                ),
            )

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                generic_request = generic_request.filter(
                    GenericRequest.last_processed_at >= start_date,
                    GenericRequest.last_processed_at < (start_date + timedelta(days=1)),
                )
            else:
                generic_request = generic_request.filter(
                    GenericRequest.last_processed_at > start_date,
                    GenericRequest.last_processed_at < (end_date + timedelta(days=1)),
                )
        elif start_date:
            generic_request = generic_request.filter(GenericRequest.last_processed_at >= start_date)
        elif end_date:
            generic_request = generic_request.filter(
                GenericRequest.last_processed_at < (end_date + timedelta(days=1))
            )

        # search filter
        if search:
            if "-GNID" in search.upper():
                ref_client_no = search.upper().split("-GNID")[0]
                gn_id = search.upper().split("-GNID")[1]
                generic_request = generic_request.filter(
                    and_(
                        Client.ref_client_no.like("%" + ref_client_no + "%"),
                        GenericRequest.id.like(gn_id + "%"),
                    )
                )
            elif "GNID" in search.upper():
                gn_id = search.upper().split("GNID")[1]
                generic_request = generic_request.filter(GenericRequest.id.like(gn_id + "%"))
            elif "GN" in search.upper():
                gn_id = search.upper().split("GN")[1]
                if gn_id:
                    generic_request = generic_request.filter(GenericRequest.id.like(gn_id + "%"))
            else:
                generic_request = generic_request.filter(
                    or_(
                        Client.name.like("%" + search + "%"),
                        GenericRequest.id.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%"),
                    )
                )

        # filter for status
        if stage:
            stages_split = stage.split(",")
            
            # ToDo: Need to be fixed from frontend("client_submission" to be removed from frontend)
            if (
                len(stages_split) == 2 
                and "pending" in stages_split 
                and "client_submission" in stages_split
            ):
                stage = "pending"
                stages_split = stage.split(",")

            if len(stages_split) > 1:
                generic_request = generic_request.filter(GenericRequest.status.in_(stages_split))
            else:
                if stage == "pending":
                    generic_request = generic_request.filter(
                        or_(
                            GenericRequest.status == "submitted",
                        )
                    )
                else:
                    generic_request = generic_request.filter(GenericRequest.status == stage)

        # filter by control_account
        if control_account:
            generic_request = generic_request.filter(ControlAccount.name == control_account)

        # ordering(sorting)
        if ordering:
            if "date" == ordering:
                generic_request = generic_request.order_by(GenericRequest.last_processed_at.asc())

            if "-date" == ordering:
                generic_request = generic_request.order_by(GenericRequest.last_processed_at.desc())

            if "status" == ordering:
                generic_request = generic_request.order_by(GenericRequest.status.asc())

            if "-status" == ordering:
                generic_request = generic_request.order_by(GenericRequest.status.desc())

            if "client_name" == ordering:
                generic_request = generic_request.order_by(Client.name.asc())

            if "-client_name" == ordering:
                generic_request = generic_request.order_by(Client.name.desc())

            if "created_at" == ordering:
                generic_request = generic_request.order_by(GenericRequest.created_at.asc())

            if "-created_at" == ordering:
                generic_request = generic_request.order_by(GenericRequest.created_at.desc())

            if "gn_reference" == ordering:
                generic_request = generic_request.order_by(GenericRequest.id.asc())

            if "-gn_reference" == ordering:
                generic_request = generic_request.order_by(GenericRequest.id.desc())
        else:
            generic_request = generic_request.order_by(GenericRequest.updated_at.desc())

        # pagination
        generic_request = generic_request.paginate(page, rpp, False)
        total_pages = generic_request.pages
        generic_request_results = generic_request_schema.dump(generic_request.items).data
        total_count = generic_request.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(generic_request_results) < 1:
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
            "data": generic_request_results,
        }
