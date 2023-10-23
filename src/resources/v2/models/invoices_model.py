from src import db
import enum
from datetime import datetime
from decimal import Decimal
from src.middleware.organization import Organization
from src.middleware.permissions import Permissions
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property


class InvoiceStatus(enum.Enum):
    approved = "approved"
    client_submission = "client_submission"
    pending = "pending"
    release_from_reserves = "release_from_reserves"
    reviewing = "reviewing"


class InvoiceActions(enum.Enum):
    include_in_advance = "include_in_advance"
    hold_in_reserves = "hold_in_reserves"
    non_factored = "non_factored"


class Invoice(db.Model):
    """ Invoice model """

    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    soa_id = db.Column(
        db.Integer, db.ForeignKey("soa.id", ondelete="CASCADE"), nullable=False
    )
    debtor = db.Column(
        db.Integer, db.ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False
    )
    invoice_number = db.Column(db.String(255))
    invoice_date = db.Column(db.Date)
    amount = db.Column(db.Numeric(10, 2), nullable=True)
    po_number = db.Column(db.String(64), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    added_by = db.Column(db.String(255))
    verified_by = db.Column(db.String(255))
    status = db.Column(db.Enum(InvoiceStatus), default=InvoiceStatus.pending.value)
    terms = db.Column(db.Integer)
    is_credit_insured = db.Column(db.Boolean, default=False)
    actions = db.Column(
        db.Enum(InvoiceActions), default=InvoiceActions.include_in_advance.value
    )
    is_release_from_reserve = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)
    
    # Indexes
    __table_args__ = (
        db.Index("idx_invoice_number", "invoice_number"),
    )

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.soa_id = data.get("soa_id")
        self.debtor = data.get("debtor")
        self.invoice_number = data.get("invoice_number")
        self.invoice_date = data.get("invoice_date")
        self.amount = data.get("amount")
        self.po_number = data.get("po_number")
        self.notes = data.get("notes")
        self.added_by = data.get("added_by")
        self.verified_by = data.get("verified_by")
        self.status = data.get("status")
        self.terms = data.get("terms")
        self.is_credit_insured = data.get("is_credit_insured")
        self.actions = data.get("actions")
        self.is_release_from_reserve = data.get("is_release_from_reserve")
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    @hybrid_property
    def invoice_number_lower(self):
        return func.lower(self.invoice_number)

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
    def get_all_invoices():
        return Invoice.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_invoice(id):
        return Invoice.query.filter_by(id=id, is_deleted=False).first()

    @staticmethod
    def get_one_based_off_control_accounts(id):
        from src.models import (
            Client,
            ClientControlAccounts,
            ControlAccount,
        )

        # Permisions
        from src.middleware.permissions import Permissions

        # control accounts
        business_control_accounts = Permissions.get_business_settings()[
            "control_accounts"
        ]

        # invoice
        return (
            Invoice.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                Invoice.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                ControlAccount.name.in_(business_control_accounts),
                Invoice.id == id,
            )
            .first()
        )

    def collection_notes(self, client_id=None):
        from src.models import (
            CollectionNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import CollectionNotesRefSchema

        collection_notes_schema = CollectionNotesRefSchema(many=True)

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
                CollectionNotes.client_id == client_id,
                ControlAccount.name.in_(business_control_accounts),
                CollectionNotes.invoice_id == self.id,
            )
            .order_by(CollectionNotes.id.desc())
            .all()
        )

        if not collection_notes:
            return []
            
        collection_notes_data = collection_notes_schema.dump(collection_notes, many=True).data

        return collection_notes_data

    def cn_approvals_history(self, client_id=None):
        from src.models import (
            CollectionNotes,
            CollectionNotesApprovalHistory,
        )

        collection_notes = (
            CollectionNotes.query.filter(
                CollectionNotes.deleted_at == None,
                CollectionNotes.client_id == client_id,
                CollectionNotes.invoice_id == self.id,
            )
            .order_by(CollectionNotes.id.desc())
            .all()
        )

        if not collection_notes:
            return []

        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        for collection_note in collection_notes:            
            # collection notes approval history
            approvals_history = CollectionNotesApprovalHistory.query.filter(
                CollectionNotesApprovalHistory.deleted_at == None,
                CollectionNotesApprovalHistory.collection_notes_id == collection_note.id,
            ).order_by(CollectionNotesApprovalHistory.updated_at.asc()).all()

            if approvals_history:
                for each_history in approvals_history:
                    history_status = None

                    if (
                        each_history.key == "client_created_at"
                        or each_history.key == "created_at"
                    ):
                        history_status = "Created by"

                    if each_history.key == "client_submission_at":
                        history_status = "Submitted by Client"

                    if each_history.key == "submitted_at":
                        history_status = "Submitted by Principal"
                    
                    ref_client_no = collection_note.client.ref_client_no if collection_note.client else None
                    cn_reference = f"{ref_client_no}-CNID{collection_note.id}"

                    # activity log
                    if history_status:
                        activity_log.append(
                            {   
                                "id": each_history.id,
                                "collection_notes_id": collection_note.id,
                                "added_at": utc_to_local(
                                    dt=each_history.created_at.isoformat()
                                ),
                                "description": history_status,
                                "user": each_history.user,
                                "cn_reference": cn_reference,
                            }
                        )
        return {
            "activity_log": activity_log,
        }

    def get_verification_notes(self):
        from src.models import (
            VerificationNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import VerificationNotesRefSchema

        verification_notes_schema = VerificationNotesRefSchema()

        # # control accounts
        # business_control_accounts = Permissions.get_business_settings()[
        #     "control_accounts"
        # ]

        verification_notes = (
            VerificationNotes.query.join(
                Debtor, Client
            )
            .filter(
                VerificationNotes.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                VerificationNotes.invoice_id == self.id,
            )
            .order_by(VerificationNotes.id.desc())
            .first()
        )
        # verification_notes = (
        #     VerificationNotes.query.join(
        #         Debtor, Client, ClientControlAccounts, ControlAccount
        #     )
        #     .filter(
        #         VerificationNotes.deleted_at == None,
        #         Debtor.is_deleted == False,
        #         Client.is_deleted == False,
        #         ControlAccount.is_deleted == False,
        #         ClientControlAccounts.is_deleted == False,
        #         VerificationNotes.client_id == client_id,
        #         ControlAccount.name.in_(business_control_accounts),
        #         VerificationNotes.invoice_id == self.id,
        #     )
        #     .order_by(VerificationNotes.id.desc())
        #     .all()
        # )

        if not verification_notes:
            return []

        verification_notes_data = verification_notes_schema.dump(verification_notes).data

        return verification_notes_data

    def vn_approvals_history(self, client_id=None):
        from src.models import (
            VerificationNotes,
            VerificationNotesApprovalHistory,
        )

        verification_notes = (
            VerificationNotes.query.filter(
                VerificationNotes.deleted_at == None,
                VerificationNotes.client_id == client_id,
                VerificationNotes.invoice_id == self.id,
            )
            .order_by(VerificationNotes.id.desc())
            .first()
        )

        if not verification_notes:
            return []

        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []     
        # verification notes approval history
        approvals_history = VerificationNotesApprovalHistory.query.filter(
            VerificationNotesApprovalHistory.deleted_at == None,
            VerificationNotesApprovalHistory.verification_notes_id == verification_notes.id,
        ).order_by(VerificationNotesApprovalHistory.updated_at.asc()).all()

        if approvals_history:
            for each_history in approvals_history:
                history_status = None

                if (
                    each_history.key == "client_created_at"
                    or each_history.key == "created_at"
                ):
                    history_status = "Created by"

                if each_history.key == "client_submission_at":
                    history_status = "Submitted by Client"

                if each_history.key == "submitted_at":
                    history_status = "Submitted by Principal"

                ref_client_no = verification_notes.client.ref_client_no if verification_notes.client else None
                vn_reference = f"{ref_client_no}-VNID{verification_notes.id}"

                # activity log
                if history_status:
                    activity_log.append(
                        {   
                            "id": each_history.id,
                            "verification_notes_id": verification_notes.id,
                            "added_at": utc_to_local(
                                dt=each_history.created_at.isoformat()
                            ),
                            "description": history_status,
                            "user": each_history.user,
                            "vn_reference": vn_reference,
                        }
                    )
        return {
            "activity_log": activity_log,
        }

    def get_invoice_supporting_documents(self):
        from src.models import (
            InvoiceSupportingDocuments,
            Debtor,
            Client,
        )
        from src.resources.v2.schemas import InvoiceSupportingDocumentsRefSchema

        invoice_supporting_documents_schema = InvoiceSupportingDocumentsRefSchema()

        invoice_supporting_documents = (
            InvoiceSupportingDocuments.query.join(
                Debtor, Client
            )
            .filter(
                InvoiceSupportingDocuments.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                InvoiceSupportingDocuments.invoice_id == self.id,
            )
            .order_by(InvoiceSupportingDocuments.id.desc())
            .all()
        )

        if not invoice_supporting_documents:
            return []

        invoice_supporting_documents_data = invoice_supporting_documents_schema.dump(invoice_supporting_documents, many=True).data

        return invoice_supporting_documents_data

    
class InvoicesListing:

    def get_all():
        from src.models import (
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import InvoiceDebtorSchema
        invoice_schema = InvoiceDebtorSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        get_client_ids = get_locations["client_list"]        
        
        # Permisions
        from src.middleware.permissions import Permissions
        user_role = Permissions.get_user_role_permissions()["user_role"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        invoices = Invoice.query.join(Client, ClientControlAccounts, ControlAccount).filter(
            Invoice.is_deleted == False, Invoice.client_id.in_(get_client_ids)
        )
        
        # get invoices having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            invoices = invoices.filter(Invoice.status != "client_submission")

        invoice_results = invoice_schema.dump(invoices).data

        if len(invoice_results) < 1:
            return None

        return invoice_results

    def get_paginated_invoices(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        actions = kwargs.get("actions", None)
        debtor_id = kwargs.get("debtor_id", None)
        client_id = kwargs.get("client_id", None)
        
        from src.models import (
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )

        from src.resources.v2.schemas import InvoiceDebtorSchema
        invoice_schema = InvoiceDebtorSchema(many=True)

        # Organization
        get_locations = Organization.get_locations()
        get_client_ids = get_locations["client_list"]

        # Permisions
        from src.middleware.permissions import Permissions
        user_role = Permissions.get_user_role_permissions()["user_role"]

        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        # invoice
        invoices = Invoice.query.join(Client, ClientControlAccounts, ControlAccount).filter(
            Invoice.is_deleted == False,
            Client.is_deleted == False,
            ControlAccount.is_deleted == False,
            ClientControlAccounts.is_deleted == False,
            Invoice.client_id.in_(get_client_ids),
            ControlAccount.name.in_(business_control_accounts)
        )

        # get invoices having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            invoices = invoices.filter(Invoice.status != "client_submission")

        # invoices action
        if actions is not None:
            if actions == "non_factored":
                invoices = invoices.filter(Invoice.actions == "non_factored")

            if actions == "include_in_advance":
                invoices = invoices.filter(Invoice.actions == "include_in_advance")

        # invoices search
        if search is not None:
            invoices = invoices.join(Invoice.debtors).filter(
                (Invoice.invoice_number.like("%" + search + "%"))
                | (Invoice.amount.like("%" + search + "%"))
                | (Debtor.name.like("%" + search + "%"))
                | (Debtor.ref_key.like("%" + search + "%"))
            )

        # filter by debtor_id
        if debtor_id:
            invoices = invoices.filter(
                Invoice.debtor == debtor_id
            )

        # filter by client_id
        if client_id:
            invoices = invoices.filter(
                Invoice.client_id == client_id
            )

        # ordering(sorting)
        if ordering is not None:
            if "invoice_date" == ordering:
                invoices = invoices.order_by(Invoice.invoice_date.asc())

            if "-invoice_date" == ordering:
                invoices = invoices.order_by(Invoice.invoice_date.desc())

            if "invoice_number" == ordering:
                invoices = invoices.order_by(Invoice.invoice_number.asc())

            if "-invoice_number" == ordering:
                invoices = invoices.order_by(Invoice.invoice_number.desc())

            if "po_number" == ordering:
                invoices = invoices.order_by(Invoice.po_number.asc())

            if "-po_number" == ordering:
                invoices = invoices.order_by(Invoice.po_number.desc())

            if "amount" == ordering:
                invoices = invoices.order_by(Invoice.amount.asc())

            if "-amount" == ordering:
                invoices = invoices.order_by(Invoice.amount.desc())

            if "terms" == ordering:
                invoices = invoices.order_by(Invoice.terms.asc())

            if "-terms" == ordering:
                invoices = invoices.order_by(Invoice.terms.desc())

            if "debtor_name" == ordering:
                invoices = invoices.join(Invoice.debtors).order_by(Debtor.name.asc())

            if "-debtor_name" == ordering:
                invoices = invoices.join(Invoice.debtors).order_by(Debtor.name.desc())

            if "soa" == ordering:
                invoices = invoices.order_by(Invoice.soa_id.asc())

            if "-soa" == ordering:
                invoices = invoices.order_by(Invoice.soa_id.desc())
        else:
            invoices = invoices.order_by(Invoice.updated_at.desc())

        # pagination
        invoices = invoices.paginate(page, rpp, False)
        total_pages = invoices.pages
        invoiceResults = invoice_schema.dump(invoices.items).data
        total_count = invoices.query.count()

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(invoiceResults) < 1:
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
            "data": invoiceResults,
        }
