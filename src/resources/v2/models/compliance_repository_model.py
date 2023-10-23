from src import db
import enum
from datetime import datetime, timedelta
from src.models import *
from src.middleware.permissions import Permissions
from src.middleware.organization import Organization
from sqlalchemy import and_, or_, not_, cast, DateTime


cr_document_type_list = [
    "Annual Income Tax Return",
    "AP Detail Aging",
    "AR Detail Aging",
    "Bank Statement",
    "Financial Statement",
    "Insurance Certificate",
    "Lien Waiver",
    "Loan Related Collateral",
    "Notice of Assessment",
    "Other",
    "Separate Priority/Lienable Payables List",
    "Source Deduction Details"
]

cr_frequency_list = [
    "Annual",
    "Monthly",
    "Other / NA",
    "Quarterly",
]

# class ComplianceRepositoryDocumentType(enum.Enum):
#     annual_income_tax_return = "Annual Income Tax Return"
#     ap_detail_aging = "AP Detail Aging"
#     ar_detail_aging = "AR Detail Aging"
#     bank_statement = "Bank Statement"
#     financial_statement = "Financial Statement"
#     insurance_certificate = "Insurance Certificate"
#     lien_waiver = "Lien Waiver"
#     loan_related_collateral = "Loan Related Collateral"
#     notice_of_assessment = "Notice of Assessment"
#     other = "Other"
#     separate_priority_or_lienable_payables_list = "Separate Priority/Lienable Payables List"
#     source_deduction_details = "Source Deduction Details"


# class ComplianceRepositoryFrequency(enum.Enum):
#     annual = "Annual"
#     monthly = "Monthly"
#     other_or_na = "Other / NA"
#     quarterly = "Quarterly"


class ComplianceRepositoryStatus(enum.Enum):
    approved = "approved"
    client_draft = "client_draft"
    client_submission = "client_submission"
    draft = "draft"
    principal_rejection = "principal_rejection"
    submitted = "submitted"


class ComplianceRepository(db.Model):
    """Compliance Repository model"""

    __tablename__ = "lc_compliance_repository"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    document_type = db.Column(db.String(255), nullable=True)
    period_end_date = db.Column(db.Date, nullable=True)
    frequency = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum(ComplianceRepositoryStatus),
        nullable=True
    )
    last_processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.document_type = data.get("document_type")
        self.period_end_date = data.get("period_end_date")
        self.frequency = data.get("frequency")
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
        return ComplianceRepository.query.filter(ComplianceRepository.deleted_at == None)

    @staticmethod
    def get_one(id):
        return ComplianceRepository.query.filter(
            ComplianceRepository.id == id, ComplianceRepository.deleted_at == None
        ).first()

    @staticmethod
    def get_one_based_off_control_accounts(id):
        from src.models import (
            Client,
            ControlAccount,
            ClientControlAccounts,
        )

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        return ComplianceRepository.query.filter(
            Client.id == ComplianceRepository.client_id,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            ClientControlAccounts.client_id == Client.id,
            ControlAccount.id == ClientControlAccounts.control_account_id,
            ControlAccount.name.in_(business_control_accounts),
            ComplianceRepository.id == id,
            ComplianceRepository.deleted_at == None,
        ).first()

    def object_as_string(self):
        return "Compliance Repository"

    def request_created_by_principal(self):
        from src.models import ComplianceRepositoryApprovalsHistory

        return ComplianceRepositoryApprovalsHistory.query.filter_by(
            compliance_repository_id=self.id, key="created_at", deleted_at=None
        ).first()

    def request_submitted_by_principal(self):
        from src.models import ComplianceRepositoryApprovalsHistory

        return ComplianceRepositoryApprovalsHistory.query.filter_by(
            compliance_repository_id=self.id, key="submitted_at", deleted_at=None
        ).first()

    def request_created_by_client(self):
        from src.models import ComplianceRepositoryApprovalsHistory

        return ComplianceRepositoryApprovalsHistory.query.filter_by(
            compliance_repository_id=self.id, key="client_created_at", deleted_at=None
        ).first()

    def request_submitted_by_client(self):
        from src.models import ComplianceRepositoryApprovalsHistory

        return (
            ComplianceRepositoryApprovalsHistory.query.filter_by(
                compliance_repository_id=self.id,
                key="client_submission_at",
                deleted_at=None,
            )
            .order_by(ComplianceRepositoryApprovalsHistory.id.desc())
            .first()
        )

    def request_approved_by_principal(self):
        from src.models import ComplianceRepositoryApprovalsHistory

        return (
            ComplianceRepositoryApprovalsHistory.query.filter_by(
                compliance_repository_id=self.id, key="approved_at", deleted_at=None
            )
            .order_by(ComplianceRepositoryApprovalsHistory.id.desc())
            .first()
        )

    def request_rejected_by_principal(self):
        from src.models import ComplianceRepositoryApprovalsHistory

        return (
            ComplianceRepositoryApprovalsHistory.query.filter_by(
                compliance_repository_id=self.id, key="principal_rejection_at", deleted_at=None
            )
            .order_by(ComplianceRepositoryApprovalsHistory.id.desc())
            .first()
        )
    
    def had_client_submitted(self):
        from src.models import ComplianceRepositoryApprovalsHistory

        return ComplianceRepositoryApprovalsHistory.query.filter_by(
            compliance_repository_id=self.id, key="client_submission_at", deleted_at=None
        ).count()

    def get_cr_reference(self):
        ref_client_no = self.client.ref_client_no if self.client else None
        cr_ref = f"{ref_client_no}-CRID{self.id}"
        return cr_ref

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
        elif self.status.value == "principal_rejection":
            approval_history = self.request_rejected_by_principal()
        elif self.status.value == "approved":
            approval_history = self.request_approved_by_principal()
        else:
            approval_history = {}
        return approval_history

    def cr_approvals_history(self):
        from src.resources.v2.models.compliance_repository_approvals_history_model import (
            ComplianceRepositoryApprovalsHistory,
        )
        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        submission_activity = []
        approvals_history = ComplianceRepositoryApprovalsHistory.query.filter_by(
            compliance_repository_id=self.id,
        )

        if approvals_history:
            submitted_by_client = 0
            submitted_by_principal = 0
            for each_history in approvals_history:
                history_status = None

                if each_history.key == "approved_at":
                    history_status = "Approved by Principal"

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

                if each_history.key == "principal_rejection_at":
                    history_status = "Rejected by Principal"

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
                    cr_created_by = {
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
                        cr_submitted_by = {
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

        compliance_repository_comments = Comments.query.filter_by(
            compliance_repository_id=self.id, is_deleted=False
        ).all()

        return compliance_repository_comments

    def supporting_documents(self):
        from src.resources.v2.models.supporting_documents_model import (
            SupportingDocuments,
        )

        supporting_documents = SupportingDocuments.query.filter_by(
            compliance_repository_id=self.id, is_deleted=False
        ).all()

        return supporting_documents

    def reasons(self):
        from src.resources.v2.models.compliance_repository_approvals_history_model import (
            ComplianceRepositoryApprovalsHistory,
        )

        reasons = ComplianceRepositoryApprovalsHistory.query.filter(
            ComplianceRepositoryApprovalsHistory.compliance_repository_id == self.id,
            ComplianceRepositoryApprovalsHistory.deleted_at == None,
            ComplianceRepositoryApprovalsHistory.key == "principal_rejection_at",
        ).all()

        return reasons


class ComplianceRepositoryListing:
    def get_all():
        from src.models import (
            ComplianceRepository,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import ComplianceRepositoryRefSchema

        compliance_repository_schema = ComplianceRepositoryRefSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        compliance_repository = (
            ComplianceRepository.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                ComplianceRepository.deleted_at == None,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                ComplianceRepository.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts),
            )
            .order_by(ComplianceRepository.updated_at.desc())
            .all()
        )

        data_results = compliance_repository_schema.dump(compliance_repository, many=True).data

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
        document_type = kwargs.get("document_type", None)
        stage = kwargs.get("stage", None)
        dashboard = kwargs.get("dashboard", False)
        client_ids = kwargs.get("client_ids", None)
        user_role = kwargs.get("user_role", None)
        business_control_accounts = kwargs.get("business_control_accounts", [])

        from src.models import (
            ComplianceRepository,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import (
            ComplianceRepositoryRefSchema,
            ComplianceRepositoryDashboardSchema,
        )

        compliance_repository_schema = ComplianceRepositoryDashboardSchema(many=True)

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

            compliance_repository_schema = ComplianceRepositoryRefSchema(many=True)

        compliance_repository = ComplianceRepository.query.join(
            Client, ClientControlAccounts, ControlAccount
        ).filter(
            ComplianceRepository.deleted_at == None,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            not_(
                ComplianceRepository.status.in_(
                    [
                        "client_draft",
                    ]
                )
            ),
            ComplianceRepository.client_id.in_(client_ids),
            ControlAccount.name.in_(business_control_accounts),
        )

        # only show active clients requests in dashboard
        if dashboard:
            compliance_repository = compliance_repository.filter(Client.is_active == True)

        # get compliance_repository having status == draft only for principal
        if user_role and user_role.lower() != "principal":
            compliance_repository = compliance_repository.filter(
                not_(
                    ComplianceRepository.status.in_(
                        [
                            "draft",
                        ]
                    )
                ),
            )

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                compliance_repository = compliance_repository.filter(
                    ComplianceRepository.last_processed_at >= start_date,
                    ComplianceRepository.last_processed_at < (start_date + timedelta(days=1)),
                )
            else:
                compliance_repository = compliance_repository.filter(
                    ComplianceRepository.last_processed_at > start_date,
                    ComplianceRepository.last_processed_at < (end_date + timedelta(days=1)),
                )
        elif start_date:
            compliance_repository = compliance_repository.filter(ComplianceRepository.last_processed_at >= start_date)
        elif end_date:
            compliance_repository = compliance_repository.filter(
                ComplianceRepository.last_processed_at < (end_date + timedelta(days=1))
            )

        # search filter
        if search:
            if "-CRID" in search.upper():
                ref_client_no = search.upper().split("-CRID")[0]
                cr_id = search.upper().split("-CRID")[1]
                compliance_repository = compliance_repository.filter(
                    and_(
                        Client.ref_client_no.like("%" + ref_client_no + "%"),
                        ComplianceRepository.id.like(cr_id + "%"),
                    )
                )
            elif "CRID" in search.upper():
                cr_id = search.upper().split("CRID")[1]
                compliance_repository = compliance_repository.filter(ComplianceRepository.id.like(cr_id + "%"))
            elif "CR" in search.upper():
                cr_id = search.upper().split("CR")[1]
                if cr_id:
                    compliance_repository = compliance_repository.filter(ComplianceRepository.id.like(cr_id + "%"))
            else:
                compliance_repository = compliance_repository.filter(
                    or_(
                        Client.name.like("%" + search + "%"),
                        ComplianceRepository.id.like("%" + search + "%"),
                        ComplianceRepository.document_type.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%"),
                    )
                )

        # filter for status
        if stage:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                compliance_repository = compliance_repository.filter(
                    ComplianceRepository.status.in_(stages_split)
                )
            else:
                if stage == "pending":
                    compliance_repository = compliance_repository.filter(
                        or_(
                            ComplianceRepository.status == "submitted",
                            ComplianceRepository.status == "client_submission",
                        )
                    )
                elif stage == "archived":
                    compliance_repository = compliance_repository.filter(
                        or_(
                            ComplianceRepository.status == "approved"
                        )
                    )
                elif stage == "rejected":
                    compliance_repository = compliance_repository.filter(
                        ComplianceRepository.status == "principal_rejected"
                    )
                # elif stage == "approved":
                #     from src.resources.v2.helpers.convert_datetime import date_concat_time
                #     # current est date: for comparing with last_processed_at(utc)
                #     today = date_concat_time(date_concat="current")
                #     next_day = date_concat_time(date_concat="next")

                #     compliance_repository = compliance_repository.filter(
                #         ComplianceRepository.status == "approved",
                #         cast(ComplianceRepository.last_processed_at, DateTime) >= today,
                #         cast(ComplianceRepository.last_processed_at, DateTime) <= next_day
                #     )
                else:
                    compliance_repository = compliance_repository.filter(
                        ComplianceRepository.status == stage
                    )

        # filter by control_account
        if control_account:
            compliance_repository = compliance_repository.filter(ControlAccount.name == control_account)

        # filter by document_type
        if document_type:
            compliance_repository = compliance_repository.filter(ComplianceRepository.document_type == document_type)

        # ordering(sorting)
        if ordering:
            if "date" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.last_processed_at.asc())

            if "-date" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.last_processed_at.desc())

            if "status" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.status.asc())

            if "-status" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.status.desc())

            if "client_name" == ordering:
                compliance_repository = compliance_repository.order_by(Client.name.asc())

            if "-client_name" == ordering:
                compliance_repository = compliance_repository.order_by(Client.name.desc())

            if "created_at" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.created_at.asc())

            if "-created_at" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.created_at.desc())

            if "cr_reference" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.id.asc())

            if "-cr_reference" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.id.desc())

            if "document_type" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.document_type.asc())

            if "-document_type" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.document_type.desc())

            if "frequency" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.frequency.asc())

            if "-frequency" == ordering:
                compliance_repository = compliance_repository.order_by(ComplianceRepository.frequency.desc())
        else:
            compliance_repository = compliance_repository.order_by(ComplianceRepository.updated_at.desc())

        # pagination
        compliance_repository = compliance_repository.paginate(page, rpp, False)
        total_pages = compliance_repository.pages
        compliance_repository_results = compliance_repository_schema.dump(compliance_repository.items).data
        total_count = compliance_repository.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(compliance_repository_results) < 1:
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
            "data": compliance_repository_results,
        }
