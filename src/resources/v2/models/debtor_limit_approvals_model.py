from src import db
from flask import abort, json
from enum import Enum
from sqlalchemy import func, or_, and_, cast, Date, not_, DateTime

from datetime import date, datetime, timedelta
from src.middleware.organization import Organization
from decimal import Decimal
from src.middleware.permissions import Permissions


class DebtorLimitApprovalsStatus(Enum):
    approved = "approved"
    client_draft = "client_draft"
    client_submission = "client_submission"
    draft = "draft"
    rejected = "rejected"
    submitted = "submitted"


class DebtorLimitApprovals(db.Model):
    """ DebtorLimitApprovals model """

    __tablename__ = "debtor_limit_approvals"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id = db.Column(
        db.Integer, db.ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False
    )
    credit_limit_requested = db.Column(db.Numeric(12, 2), nullable=False)
    credit_limit_approved = db.Column(db.Numeric(12, 2), nullable=True, default=0)
    status = db.Column(
        db.Enum(DebtorLimitApprovalsStatus),
        default=DebtorLimitApprovalsStatus.draft.value,
        server_default=DebtorLimitApprovalsStatus.draft.value,
    )
    last_processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    # relationship
    approvals_history = db.relationship(
        "DebtorLimitApprovalsHistory", backref="debtor_limit_approvals"
    )

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.debtor_id = data.get("debtor_id")
        self.credit_limit_requested = data.get("credit_limit_requested")
        self.credit_limit_approved = data.get("credit_limit_approved")
        self.status = data.get("status")
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
        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]
        return DebtorLimitApprovals.query.filter(
            DebtorLimitApprovals.deleted_at == None,
            DebtorLimitApprovals.client_id.in_(client_ids),
        )

    @staticmethod
    def get_one(id):
        return DebtorLimitApprovals.query.filter(
            DebtorLimitApprovals.id == id,
            DebtorLimitApprovals.deleted_at == None,
        ).first()

    @staticmethod
    def get_one_based_off_control_accounts(id, active_client=False):
        from src.models import (
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        debtor_limit_approvals = DebtorLimitApprovals.query.join(
                Debtor, Client, ClientControlAccounts, ControlAccount
        ).filter(
            DebtorLimitApprovals.deleted_at == None,
            Debtor.is_deleted == False,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            ControlAccount.name.in_(business_control_accounts),
            DebtorLimitApprovals.id == id,
        )

        if active_client:
            debtor_limit_approvals = debtor_limit_approvals.filter(Client.is_active == True, Debtor.is_active == True)

        debtor_limit_approvals = debtor_limit_approvals.first()
        return debtor_limit_approvals

    def request_created_by_principal(self):
        from src.models import DebtorLimitApprovalsHistory

        return DebtorLimitApprovalsHistory.query.filter_by(
            debtor_limit_approvals_id=self.id, key="created_at", deleted_at=None
        ).first()

    def request_created_by_client(self):
        from src.models import DebtorLimitApprovalsHistory

        return DebtorLimitApprovalsHistory.query.filter_by(
            debtor_limit_approvals_id=self.id, key="client_created_at", deleted_at=None
        ).first()

    def request_submitted_by_client(self):
        from src.models import DebtorLimitApprovalsHistory

        return (
            DebtorLimitApprovalsHistory.query.filter_by(
                debtor_limit_approvals_id=self.id,
                key="client_submission_at",
                deleted_at=None,
            )
            .order_by(DebtorLimitApprovalsHistory.id.desc())
            .first()
        )

    def request_submitted_by_principal(self):
        from src.models import DebtorLimitApprovalsHistory

        return DebtorLimitApprovalsHistory.query.filter_by(
            debtor_limit_approvals_id=self.id, key="submitted_at", deleted_at=None
        ).first()

    def request_rejected_by_ae(self):
        from src.models import DebtorLimitApprovalsHistory

        return (
            DebtorLimitApprovalsHistory.query.filter_by(
                debtor_limit_approvals_id=self.id, key="rejected_at", deleted_at=None
            )
            .order_by(DebtorLimitApprovalsHistory.id.desc())
            .first()
        )

    def request_approved_by_ae(self):
        from src.models import DebtorLimitApprovalsHistory

        return (
            DebtorLimitApprovalsHistory.query.filter_by(
                debtor_limit_approvals_id=self.id, key="approved_at", deleted_at=None
            )
            .order_by(DebtorLimitApprovalsHistory.id.desc())
            .first()
        )

    def has_client_submitted(self):
        from src.models import DebtorLimitApprovalsHistory

        return DebtorLimitApprovalsHistory.query.filter_by(
            debtor_limit_approvals_id=self.id,
            key="client_submission_at",
            deleted_at=None,
        ).count()

    def get_cl_reference(self):
        ref_client_no = self.client.ref_client_no if self.client else None
        cl_ref = f"{ref_client_no}-CLID{self.id}"
        return cl_ref

    def get_debtor_name(self):
        return self.debtor.name if self.debtor else None

    def get_debtor_ref_key(self):
        return self.debtor.ref_key if self.debtor else None

    def get_client_name(self):
        return self.client.name if self.client else None

    # ToDo: Need to add this method in debtor model and get debtor address from there
    def get_debtor_address(self):
        debtor = self.debtor
        address_concat = ""
        if debtor.address_1:
            address_concat = debtor.address_1
        if debtor.address_2:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.address_2
        if debtor.city:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.city
        if debtor.state:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.state
        if debtor.country:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.country
        if debtor.postal_code:
            if address_concat:
                address_concat += ", "
            address_concat += debtor.postal_code
        return address_concat

    def get_approval_history(self):
        if self.status.value == "client_draft":
            approval_history = self.request_created_by_client()
        elif self.status.value == "client_submission":
            approval_history = self.request_submitted_by_client()
        elif self.status.value == "draft":
            approval_history = self.request_created_by_principal()
        elif self.status.value == "submitted":
            approval_history = self.request_submitted_by_principal()
        elif self.status.value == "rejected":
            approval_history = self.request_rejected_by_ae()
        elif self.status.value == "approved":
            approval_history = self.request_approved_by_ae()
        else:
            approval_history = {}
        return approval_history

    def get_previous_credit_limit(self):
        from src.models import ClientDebtor

        previous_credit_limit = float(0)
        get_approval_history = self.get_approval_history()

        if get_approval_history and get_approval_history.attribute:
            previous_credit_limit = (
                float(get_approval_history.attribute["previous_credit_limit"])
                if "previous_credit_limit" in get_approval_history.attribute
                else previous_credit_limit
            )
        else:
            client_debtors = ClientDebtor.query.filter_by(
                is_deleted=False,
                client_id=self.client_id,
                debtor_id=self.debtor_id,
            ).first()
            if client_debtors:
                previous_credit_limit = float(client_debtors.credit_limit)
        return previous_credit_limit

    def object_as_string(self):
        return "Credit Limit"

    def update_client_debtor_credit_limit(self):
        from src.models import ClientDebtor

        client_debtor = ClientDebtor.query.filter_by(
            is_deleted=False,
            client_id=self.client_id,
            debtor_id=self.debtor_id,
        ).first()
        if client_debtor:
            client_debtor.credit_limit = self.credit_limit_approved
            client_debtor.save()

    def dla_approvals_history(self):
        from src.resources.v2.models.debtor_limit_approvals_history_model import (
            DebtorLimitApprovalsHistory,
        )
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        submission_activity = []
        approvals_history = DebtorLimitApprovalsHistory.query.filter_by(
            debtor_limit_approvals_id=self.id,
        )

        if approvals_history:
            submitted_by_client = 0
            submitted_by_principal = 0
            is_request_approved = False
            for each_history in approvals_history:
                history_status = None

                if each_history.key == "approved_at":
                    history_status = "Approved by AE"
                    is_request_approved = True

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
                    dla_created_by = {
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
                        dla_submitted_by = {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "user": each_history.user,
                        }

        return {
            "activity_log": activity_log,
            "submission_activity": submission_activity,
        }

    def dla_comments(self):
        from src.resources.v2.models.comments_model import Comments

        dla_comments = Comments.query.filter_by(
            debtor_limit_approvals_id=self.id, is_deleted=False
        ).all()

        return dla_comments

    def supporting_documents(self):
        from src.resources.v2.models.supporting_documents_model import (
            SupportingDocuments,
        )

        supporting_documents = SupportingDocuments.query.filter_by(
            debtor_limit_approvals_id=self.id, is_deleted=False
        ).all()

        return supporting_documents

    def dla_reasons(self):
        from src.resources.v2.models.debtor_limit_approvals_history_model import (
            DebtorLimitApprovalsHistory,
        )

        dla_reasons = DebtorLimitApprovalsHistory.query.filter(
            DebtorLimitApprovalsHistory.debtor_limit_approvals_id == self.id,
            DebtorLimitApprovalsHistory.deleted_at == None,
            DebtorLimitApprovalsHistory.key == "rejected_at",
        ).all()

        return dla_reasons


class DebtorLimitApprovalsListing:
    def get_all():
        from src.models import (
            DebtorLimitApprovals,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import DebtorLimitApprovalsRefSchema

        debtor_limit_approvals_schema = DebtorLimitApprovalsRefSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        debtor_limit_approvals = (
            DebtorLimitApprovals.query.join(
                Debtor, Client, ClientControlAccounts, ControlAccount
            )
            .filter(
                DebtorLimitApprovals.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                DebtorLimitApprovals.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts),
            )
            .order_by(DebtorLimitApprovals.updated_at.desc())
            .all()
        )

        data_results = debtor_limit_approvals_schema.dump(
            debtor_limit_approvals, many=True
        ).data

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
            DebtorLimitApprovals,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import (
            DebtorLimitApprovalsRefSchema,
            DebtorLimitApprovalsDashboardSchema,
        )

        debtor_limit_approvals_schema = DebtorLimitApprovalsDashboardSchema(many=True)

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

        debtor_limit_approvals = DebtorLimitApprovals.query.join(
            Debtor, Client, ClientControlAccounts, ControlAccount
        ).filter(
            DebtorLimitApprovals.deleted_at == None,
            Debtor.is_deleted == False,
            Debtor.is_active == True,
            Client.is_deleted == False,
            Client.is_active == True,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            not_(
                DebtorLimitApprovals.status.in_(
                    [
                        "client_draft",
                    ]
                )
            ),
            DebtorLimitApprovals.client_id.in_(client_ids),
            ControlAccount.name.in_(business_control_accounts),
        )

        # get debtor_limit_approvals having status == draft only for principal
        if user_role and user_role.lower() != "principal":
            debtor_limit_approvals = debtor_limit_approvals.filter(
                not_(
                    DebtorLimitApprovals.status.in_(
                        [
                            "draft",
                        ]
                    )
                ),
            )

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                debtor_limit_approvals = debtor_limit_approvals.filter(
                    DebtorLimitApprovals.last_processed_at >= start_date,
                    DebtorLimitApprovals.last_processed_at
                    < (start_date + timedelta(days=1)),
                )
            else:
                debtor_limit_approvals = debtor_limit_approvals.filter(
                    DebtorLimitApprovals.last_processed_at > start_date,
                    DebtorLimitApprovals.last_processed_at
                    < (end_date + timedelta(days=1)),
                )
        elif start_date:
            debtor_limit_approvals = debtor_limit_approvals.filter(
                DebtorLimitApprovals.last_processed_at >= start_date
            )
        elif end_date:
            debtor_limit_approvals = debtor_limit_approvals.filter(
                DebtorLimitApprovals.last_processed_at < (end_date + timedelta(days=1))
            )

        # search filter
        if search:
            if "-CLID" in search.upper():
                ref_client_no = search.upper().split("-CLID")[0]
                cl_id = search.upper().split("-CLID")[1]
                debtor_limit_approvals = debtor_limit_approvals.filter(
                    and_(
                        Client.ref_client_no.like("%" + ref_client_no + "%"),
                        DebtorLimitApprovals.id.like(cl_id + "%"),
                    )
                )
            elif "CLID" in search.upper():
                cl_id = search.upper().split("CLID")[1]
                debtor_limit_approvals = debtor_limit_approvals.filter(
                    DebtorLimitApprovals.id.like(cl_id + "%")
                )
            elif "CL" in search.upper():
                cl_id = search.upper().split("CL")[1]
                if cl_id:
                    debtor_limit_approvals = debtor_limit_approvals.filter(
                        DebtorLimitApprovals.id.like(cl_id + "%")
                    )
            else:
                debtor_limit_approvals = debtor_limit_approvals.filter(
                    or_(
                        Debtor.name.like("%" + search + "%"),
                        DebtorLimitApprovals.id.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%"),
                    )
                )

        # filter for status
        if stage:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                debtor_limit_approvals = debtor_limit_approvals.filter(
                    DebtorLimitApprovals.status.in_(stages_split)
                )
            else:
                if stage == "pending":
                    debtor_limit_approvals = debtor_limit_approvals.filter(
                        or_(
                            DebtorLimitApprovals.status == "submitted",
                            DebtorLimitApprovals.status == "client_submission",
                        )
                    )
                else:
                    debtor_limit_approvals = debtor_limit_approvals.filter(
                        DebtorLimitApprovals.status == stage
                    )

        # filter by control_account
        if control_account:
            debtor_limit_approvals = debtor_limit_approvals.filter(
                ControlAccount.name == control_account
            )

        # ordering(sorting)
        if ordering:
            if "date" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.last_processed_at.asc()
                )

            if "-date" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.last_processed_at.desc()
                )

            if "status" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.status.asc()
                )

            if "-status" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.status.desc()
                )

            if "debtor_name" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    Debtor.name.asc()
                )

            if "-debtor_name" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    Debtor.name.desc()
                )

            if "created_at" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.created_at.asc()
                )

            if "-created_at" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.created_at.desc()
                )

            if "credit_limit" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.credit_limit_requested.asc()
                )

            if "-credit_limit" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.credit_limit_requested.desc()
                )

            if "credit_limit_requested" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.credit_limit_requested.asc()
                )

            if "-credit_limit_requested" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.credit_limit_requested.desc()
                )

            if "credit_limit_approved" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.credit_limit_approved.asc()
                )

            if "-credit_limit_approved" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.credit_limit_approved.desc()
                )

            if "cl_reference" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.id.asc()
                )

            if "-cl_reference" == ordering:
                debtor_limit_approvals = debtor_limit_approvals.order_by(
                    DebtorLimitApprovals.id.desc()
                )
        else:
            debtor_limit_approvals = debtor_limit_approvals.order_by(
                DebtorLimitApprovals.updated_at.desc()
            )

        # pagination
        debtor_limit_approvals = debtor_limit_approvals.paginate(page, rpp, False)
        total_pages = debtor_limit_approvals.pages
        dla_results = debtor_limit_approvals_schema.dump(
            debtor_limit_approvals.items
        ).data
        total_count = debtor_limit_approvals.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(dla_results) < 1:
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
            "data": dla_results,
        }
