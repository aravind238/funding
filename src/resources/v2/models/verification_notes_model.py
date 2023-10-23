from src import db
import enum
from datetime import datetime, timedelta
from src.models import *
from src.middleware.permissions import Permissions
from src.middleware.organization import Organization
from sqlalchemy import and_, or_, not_, cast, DateTime


verification_type_or_method_list = [
    "DENIDED",
    "DENIED - Invoice Paid",
    "Pending",
    "Unable to Contact for Verification",
    "Pending Additional Documentation",
    "Disputed by Debtor",
    "TruckerCloud Verification Failed",
    "Verified",
    "Verified with supporting documentation",
    "Verified by Phone",
    "Verified by Email",
    "Verified by Portal",
    "Verified by TruckerCloud"
]

class VerificationNotesStatus(enum.Enum):
    client_draft = "client_draft"
    client_submission = "client_submission"
    draft = "draft"
    submitted = "submitted"


class VerificationNotes(db.Model):
    """Verification Notes model"""

    __tablename__ = "lc_verification_notes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id = db.Column(
        db.Integer, db.ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id = db.Column(
        db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    soa_id = db.Column(
        db.Integer, db.ForeignKey("soa.id", ondelete="CASCADE"), nullable=False
    )
    verification_type_or_method = db.Column(db.String(255), nullable=True)
    contact = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(VerificationNotesStatus), nullable=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    # back relation field
    invoice = db.relationship("Invoice", backref="verification_notes")

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.debtor_id = data.get("debtor_id")
        self.invoice_id = data.get("invoice_id")
        self.soa_id = data.get("soa_id")
        self.verification_type_or_method = data.get("verification_type_or_method")
        self.contact = data.get("contact")
        self.notes = data.get("notes")
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
        return VerificationNotes.query.filter(
            VerificationNotes.deleted_at == None,
            VerificationNotes.client_id.in_(client_ids),
        )

    @staticmethod
    def get_one(id):
        return VerificationNotes.query.filter(
            VerificationNotes.id == id,
            VerificationNotes.deleted_at == None,
        ).first()

    @staticmethod
    def get_one_based_off_control_accounts(id):
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

        return (
            VerificationNotes.query.join(
                Debtor, Client, ClientControlAccounts, ControlAccount
            )
            .filter(
                VerificationNotes.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                ControlAccount.name.in_(business_control_accounts),
                VerificationNotes.id == id,
            )
            .first()
        )

    def request_created_by_principal(self):
        from src.models import VerificationNotesApprovalHistory

        return VerificationNotesApprovalHistory.query.filter_by(
            verification_notes_id=self.id, key="created_at", deleted_at=None
        ).first()

    def request_created_by_client(self):
        from src.models import VerificationNotesApprovalHistory

        return VerificationNotesApprovalHistory.query.filter_by(
            verification_notes_id=self.id, key="client_created_at", deleted_at=None
        ).first()

    def request_submitted_by_client(self):
        from src.models import VerificationNotesApprovalHistory

        return (
            VerificationNotesApprovalHistory.query.filter_by(
                verification_notes_id=self.id,
                key="client_submission_at",
                deleted_at=None,
            )
            .order_by(VerificationNotesApprovalHistory.id.desc())
            .first()
        )

    def request_submitted_by_principal(self):
        from src.models import VerificationNotesApprovalHistory

        return VerificationNotesApprovalHistory.query.filter_by(
            verification_notes_id=self.id, key="submitted_at", deleted_at=None
        ).first()

    def has_client_submitted(self):
        from src.models import VerificationNotesApprovalHistory

        return VerificationNotesApprovalHistory.query.filter_by(
            verification_notes_id=self.id,
            key="client_submission_at",
            deleted_at=None,
        ).count()

    def get_vn_reference(self):
        ref_client_no = self.client.ref_client_no if self.client else None
        vn_ref = f"{ref_client_no}-VNID{self.id}"
        return vn_ref

    def get_invoice_number(self):
        return self.invoice.invoice_number if self.invoice else None

    def get_debtor_name(self):
        return self.debtor.name if self.debtor else None

    def get_debtor_ref_key(self):
        return self.debtor.ref_key if self.debtor else None

    def get_client_name(self):
        return self.client.name if self.client else None

    def get_approval_history(self):
        if self.status.value == "client_draft":
            approval_history = self.request_created_by_client()
        elif self.status.value == "client_submission":
            approval_history = self.request_submitted_by_client()
        elif self.status.value == "draft":
            approval_history = self.request_created_by_principal()
        elif self.status.value == "submitted":
            approval_history = self.request_submitted_by_principal()
        else:
            approval_history = {}
        return approval_history


    def object_as_string(self):
        return "Verification Notes"


    def vn_approvals_history(self):
        from src.resources.v2.models.verification_notes_approval_history_model import (
            VerificationNotesApprovalHistory,
        )
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        submission_activity = []
        approvals_history = VerificationNotesApprovalHistory.query.filter_by(
            verification_notes_id=self.id,
        ).all()

        if approvals_history:
            submitted_by_client = 0
            submitted_by_principal = 0
            for each_history in approvals_history:
                history_status = None

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
                    vn_created_by = {
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
                        vn_submitted_by = {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "user": each_history.user,
                        }

        return {
            "activity_log": activity_log,
            "submission_activity": submission_activity,
        }


class VerificationNotesListing:
    def get_all():
        from src.models import (
            VerificationNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import VerificationNotesRefSchema

        verification_notes_schema = VerificationNotesRefSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        verification_notes = (
            VerificationNotes.query.join(
                Debtor, Client, ClientControlAccounts, ControlAccount
            )
            .filter(
                VerificationNotes.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                VerificationNotes.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts),
            )
            .order_by(VerificationNotes.updated_at.desc())
            .all()
        )

        data_results = verification_notes_schema.dump(verification_notes, many=True).data

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
            VerificationNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import (
            VerificationNotesRefSchema,
            VerificationNotesDashboardSchema,
        )

        verification_notes_schema = VerificationNotesDashboardSchema(many=True)

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

            verification_notes_schema = VerificationNotesRefSchema(many=True)

        verification_notes = VerificationNotes.query.join(
            Debtor, Client, ClientControlAccounts, ControlAccount
        ).filter(
            VerificationNotes.deleted_at == None,
            Debtor.is_deleted == False,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            not_(
                VerificationNotes.status.in_(
                    [
                        "client_draft",
                    ]
                )
            ),
            VerificationNotes.client_id.in_(client_ids),
            ControlAccount.name.in_(business_control_accounts),
        )

        # get verification_notes having status == draft only for principal
        if user_role and user_role.lower() != "principal":
            verification_notes = verification_notes.filter(
                not_(
                    VerificationNotes.status.in_(
                        [
                            "draft",
                        ]
                    )
                ),
            )

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                verification_notes = verification_notes.filter(
                    VerificationNotes.last_processed_at >= start_date,
                    VerificationNotes.last_processed_at
                    < (start_date + timedelta(days=1)),
                )
            else:
                verification_notes = verification_notes.filter(
                    VerificationNotes.last_processed_at > start_date,
                    VerificationNotes.last_processed_at
                    < (end_date + timedelta(days=1)),
                )
        elif start_date:
            verification_notes = verification_notes.filter(
                VerificationNotes.last_processed_at >= start_date
            )
        elif end_date:
            verification_notes = verification_notes.filter(
                VerificationNotes.last_processed_at < (end_date + timedelta(days=1))
            )

        # search filter
        if search:
            if "-VNID" in search.upper():
                ref_client_no = search.upper().split("-VNID")[0]
                vn_id = search.upper().split("-VNID")[1]
                verification_notes = verification_notes.filter(
                    and_(
                        Client.ref_client_no.like("%" + ref_client_no + "%"),
                        VerificationNotes.id.like(vn_id + "%"),
                    )
                )
            elif "VNID" in search.upper():
                vn_id = search.upper().split("VNID")[1]
                verification_notes = verification_notes.filter(
                    VerificationNotes.id.like(vn_id + "%")
                )
            elif "VN" in search.upper():
                vn_id = search.upper().split("VN")[1]
                if vn_id:
                    verification_notes = verification_notes.filter(
                        VerificationNotes.id.like(vn_id + "%")
                    )
            else:
                verification_notes = verification_notes.filter(
                    or_(
                        Debtor.name.like("%" + search + "%"),
                        VerificationNotes.id.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%"),
                    )
                )

        # filter for status
        if stage:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                verification_notes = verification_notes.filter(
                    VerificationNotes.status.in_(stages_split)
                )
            else:
                if stage == "pending":
                    verification_notes = verification_notes.filter(
                        or_(
                            VerificationNotes.status == "submitted",
                            VerificationNotes.status == "client_submission",
                        )
                    )
                else:
                    verification_notes = verification_notes.filter(
                        VerificationNotes.status == stage
                    )

        # filter by control_account
        if control_account:
            verification_notes = verification_notes.filter(
                ControlAccount.name == control_account
            )

        # ordering(sorting)
        if ordering:
            if "date" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.last_processed_at.asc()
                )

            if "-date" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.last_processed_at.desc()
                )

            if "status" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.status.asc()
                )

            if "-status" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.status.desc()
                )

            if "debtor_name" == ordering:
                verification_notes = verification_notes.order_by(
                    Debtor.name.asc()
                )

            if "-debtor_name" == ordering:
                verification_notes = verification_notes.order_by(
                    Debtor.name.desc()
                )

            if "created_at" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.created_at.asc()
                )

            if "-created_at" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.created_at.desc()
                )

            if "vn_reference" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.id.asc()
                )

            if "-vn_reference" == ordering:
                verification_notes = verification_notes.order_by(
                    VerificationNotes.id.desc()
                )
        else:
            verification_notes = verification_notes.order_by(
                VerificationNotes.updated_at.desc()
            )

        # pagination
        verification_notes = verification_notes.paginate(page, rpp, False)
        total_pages = verification_notes.pages
        vn_results = verification_notes_schema.dump(verification_notes.items).data
        total_count = verification_notes.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(vn_results) < 1:
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
            "data": vn_results,
        }
