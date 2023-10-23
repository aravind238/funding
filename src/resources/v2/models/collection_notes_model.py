from src import db
import enum
from datetime import datetime, timedelta
from src.models import *
from src.middleware.permissions import Permissions
from src.middleware.organization import Organization
from sqlalchemy import and_, or_, not_, cast, DateTime


CollectionStatus = [
    "Customer Dispute (Escalate)",
    "Do Not Call (Escalate)",
    "Double Brokered (Escalate)",
    "Duplicate Billing (Escalate)",
    "Financial Distress (Escalate)",
    "Future Payment Date",
    "General Escalate (Escalate)",
    "Incorrect Carrier (Escalate)",
    "In Process / Pending",
    "Invoice Not Received",
    "Misdirected Pay (Escalate)",
    "Open Short Pay (Escalate)",
    "Paperwork Issue",
    "Pending Charge Back (Escalate)",
    "PR Confirmed",
    "PIR Elapsed",
    "Settlement Claim (Escalate)",
    "Unable to Contact",
    "Will Pay"
]

CollectionNotesContactMethod = [
    "Email",
    "Fax",
    "Online System",
    "Phone"
]

class CollectionNotesStatus(enum.Enum):
    client_draft = "client_draft"
    client_submission = "client_submission"
    draft = "draft"
    submitted = "submitted"


class CollectionNotes(db.Model):
    """Collection Notes model"""

    __tablename__ = "lc_collection_notes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    debtor_id = db.Column(
        db.Integer, db.ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id = db.Column(
        db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=True
    )
    collection_status = db.Column(db.String(255), nullable=True)
    ineligible = db.Column(db.Boolean, default=False)
    disputed = db.Column(db.Boolean, default=False)
    call_back_date = db.Column(db.Date, nullable=True)
    expected_pay_date = db.Column(db.Date, nullable=True)
    contact = db.Column(db.String(255), nullable=True)
    contact_method = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(CollectionNotesStatus), nullable=True)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.debtor_id = data.get("debtor_id")
        self.invoice_id = data.get("invoice_id")
        self.collection_status = data.get("collection_status")
        self.ineligible = data.get("ineligible")
        self.disputed = data.get("disputed")
        self.call_back_date = data.get("call_back_date")
        self.expected_pay_date = data.get("expected_pay_date")
        self.contact = data.get("contact")
        self.contact_method = data.get("contact_method")
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
        return CollectionNotes.query.filter(
            CollectionNotes.deleted_at == None,
            CollectionNotes.client_id.in_(client_ids),
        )

    @staticmethod
    def get_one(id):
        return CollectionNotes.query.filter(
            CollectionNotes.id == id,
            CollectionNotes.deleted_at == None,
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

        collection_notes = CollectionNotes.query.join(
            Debtor, Client, ClientControlAccounts, ControlAccount
        ).filter(
            CollectionNotes.deleted_at == None,
            Debtor.is_deleted == False,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            ControlAccount.name.in_(business_control_accounts),
            CollectionNotes.id == id,
        )

        if active_client:
            collection_notes = collection_notes.filter(Client.is_active == True, Debtor.is_active == True)

        collection_notes = collection_notes.first()
        return collection_notes

    def request_created_by_principal(self):
        from src.models import CollectionNotesApprovalHistory

        return CollectionNotesApprovalHistory.query.filter_by(
            collection_notes_id=self.id, key="created_at", deleted_at=None
        ).first()

    def request_created_by_client(self):
        from src.models import CollectionNotesApprovalHistory

        return CollectionNotesApprovalHistory.query.filter_by(
            collection_notes_id=self.id, key="client_created_at", deleted_at=None
        ).first()

    def request_submitted_by_client(self):
        from src.models import CollectionNotesApprovalHistory

        return (
            CollectionNotesApprovalHistory.query.filter_by(
                collection_notes_id=self.id,
                key="client_submission_at",
                deleted_at=None,
            )
            .order_by(CollectionNotesApprovalHistory.id.desc())
            .first()
        )

    def request_submitted_by_principal(self):
        from src.models import CollectionNotesApprovalHistory

        return CollectionNotesApprovalHistory.query.filter_by(
            collection_notes_id=self.id, key="submitted_at", deleted_at=None
        ).first()

    def has_client_submitted(self):
        from src.models import CollectionNotesApprovalHistory

        return CollectionNotesApprovalHistory.query.filter_by(
            collection_notes_id=self.id,
            key="client_submission_at",
            deleted_at=None,
        ).count()

    def get_cn_reference(self):
        ref_client_no = self.client.ref_client_no if self.client else None
        cn_ref = f"{ref_client_no}-CNID{self.id}"
        return cn_ref

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
        return "Collection Notes"


    def cn_approvals_history(self):
        from src.resources.v2.models.collection_notes_approval_history_model import (
            CollectionNotesApprovalHistory,
        )
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        submission_activity = []
        approvals_history = CollectionNotesApprovalHistory.query.filter_by(
            collection_notes_id=self.id,
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
                    cn_created_by = {
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
                        cn_submitted_by = {
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "user": each_history.user,
                        }

        return {
            "activity_log": activity_log,
            "submission_activity": submission_activity,
        }


class CollectionNotesListing:
    def get_all():
        from src.models import (
            CollectionNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import CollectionNotesRefSchema

        collection_notes_schema = CollectionNotesRefSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        collection_notes = (
            CollectionNotes.query.join(
                Debtor, Client, ClientControlAccounts, ControlAccount
            )
            .filter(
                CollectionNotes.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                CollectionNotes.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts),
            )
            .order_by(CollectionNotes.updated_at.desc())
            .all()
        )

        data_results = collection_notes_schema.dump(collection_notes, many=True).data

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
            CollectionNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import (
            CollectionNotesRefSchema,
            CollectionNotesDashboardSchema,
        )

        collection_notes_schema = CollectionNotesDashboardSchema(many=True)

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

            collection_notes_schema = CollectionNotesRefSchema(many=True)

        collection_notes = CollectionNotes.query.join(
            Debtor, Client, ClientControlAccounts, ControlAccount
        ).filter(
            CollectionNotes.deleted_at == None,
            Debtor.is_deleted == False,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            not_(
                CollectionNotes.status.in_(
                    [
                        "client_draft",
                    ]
                )
            ),
            CollectionNotes.client_id.in_(client_ids),
            ControlAccount.name.in_(business_control_accounts),
        )

        # get collection_notes having status == draft only for principal
        if user_role and user_role.lower() != "principal":
            collection_notes = collection_notes.filter(
                not_(
                    CollectionNotes.status.in_(
                        [
                            "draft",
                        ]
                    )
                ),
            )

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                collection_notes = collection_notes.filter(
                    CollectionNotes.last_processed_at >= start_date,
                    CollectionNotes.last_processed_at
                    < (start_date + timedelta(days=1)),
                )
            else:
                collection_notes = collection_notes.filter(
                    CollectionNotes.last_processed_at > start_date,
                    CollectionNotes.last_processed_at
                    < (end_date + timedelta(days=1)),
                )
        elif start_date:
            collection_notes = collection_notes.filter(
                CollectionNotes.last_processed_at >= start_date
            )
        elif end_date:
            collection_notes = collection_notes.filter(
                CollectionNotes.last_processed_at < (end_date + timedelta(days=1))
            )

        # search filter
        if search:
            if "-CNID" in search.upper():
                ref_client_no = search.upper().split("-CNID")[0]
                cn_id = search.upper().split("-CNID")[1]
                collection_notes = collection_notes.filter(
                    and_(
                        Client.ref_client_no.like("%" + ref_client_no + "%"),
                        CollectionNotes.id.like(cn_id + "%"),
                    )
                )
            elif "CNID" in search.upper():
                cn_id = search.upper().split("CNID")[1]
                collection_notes = collection_notes.filter(
                    CollectionNotes.id.like(cn_id + "%")
                )
            elif "CN" in search.upper():
                cn_id = search.upper().split("CN")[1]
                if cn_id:
                    collection_notes = collection_notes.filter(
                        CollectionNotes.id.like(cn_id + "%")
                    )
            else:
                collection_notes = collection_notes.filter(
                    or_(
                        Debtor.name.like("%" + search + "%"),
                        CollectionNotes.id.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%"),
                    )
                )

        # filter for status
        if stage:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                collection_notes = collection_notes.filter(
                    CollectionNotes.status.in_(stages_split)
                )
            else:
                if stage == "pending":
                    collection_notes = collection_notes.filter(
                        or_(
                            CollectionNotes.status == "submitted",
                            CollectionNotes.status == "client_submission",
                        )
                    )
                else:
                    collection_notes = collection_notes.filter(
                        CollectionNotes.status == stage
                    )

        # filter by control_account
        if control_account:
            collection_notes = collection_notes.filter(
                ControlAccount.name == control_account
            )

        # ordering(sorting)
        if ordering:
            if "date" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.last_processed_at.asc()
                )

            if "-date" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.last_processed_at.desc()
                )

            if "status" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.status.asc()
                )

            if "-status" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.status.desc()
                )

            if "debtor_name" == ordering:
                collection_notes = collection_notes.order_by(
                    Debtor.name.asc()
                )

            if "-debtor_name" == ordering:
                collection_notes = collection_notes.order_by(
                    Debtor.name.desc()
                )

            if "created_at" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.created_at.asc()
                )

            if "-created_at" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.created_at.desc()
                )

            if "cn_reference" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.id.asc()
                )

            if "-cn_reference" == ordering:
                collection_notes = collection_notes.order_by(
                    CollectionNotes.id.desc()
                )
        else:
            collection_notes = collection_notes.order_by(
                CollectionNotes.updated_at.desc()
            )

        # pagination
        collection_notes = collection_notes.paginate(page, rpp, False)
        total_pages = collection_notes.pages
        cn_results = collection_notes_schema.dump(collection_notes.items).data
        total_count = collection_notes.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(cn_results) < 1:
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
            "data": cn_results,
        }
