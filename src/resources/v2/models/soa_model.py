# from src.resources.v2.schemas import client_settings_schema
from src.resources.v2.models.client_control_accounts_model import ClientControlAccounts
from src import db
from flask import abort, json
import enum
from sqlalchemy import func, or_, and_, cast, Date, not_, DateTime

import math
from datetime import date, datetime, timedelta
from src.middleware.organization import Organization
from decimal import Decimal
from src.middleware.permissions import Permissions



class SOAStatus(enum.Enum):
    action_required = "action_required"
    action_required_by_client = "action_required_by_client"
    approved = "approved"
    client_draft = "client_draft"
    client_submission = "client_submission"
    completed = "completed"
    draft = "draft"
    pending = "pending"
    principal_rejection = "principal_rejection"
    rejected = "rejected"
    reviewed = "reviewed"
    submitted = "submitted"


class SOA(db.Model):
    """ SOA model """

    __tablename__ = "soa"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )  # need to check this
    soa_ref_id = db.Column(db.Integer, nullable=True, default=0)
    reference_number = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(SOAStatus), default=SOAStatus.draft.value)
    uploaded_supporting_docs = db.Column(db.Boolean, default=False)
    verification_calls = db.Column(db.Boolean, default=False)
    verification_call_notes = db.Column(db.Boolean, default=False)
    debtor_approval_emails = db.Column(db.Boolean, default=False)
    estoppel_letters = db.Column(db.Boolean, default=False)
    email_verification = db.Column(db.Boolean, default=False)
    po_verification = db.Column(db.Boolean, default=False)
    proof_of_delivery = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    invoice_total = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    invoice_cash_reserve_release = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    disclaimer_id = db.Column(
        db.Integer, db.ForeignKey("disclaimers.id", ondelete="CASCADE"), nullable=True
    )
    discount_fees = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    credit_insurance_total = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    reserves_withheld = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    additional_cash_reserve_held = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    miscellaneous_adjustment = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    reason_miscellaneous_adj = db.Column(db.Text, nullable=True)
    fee_adjustment = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    reason_fee_adj = db.Column(db.String(255), nullable=True)
    additional_cash_reserve_release = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    advance_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    high_priority = db.Column(db.Boolean, default=False)
    ar_balance = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    additional_notes = db.Column(db.Text, nullable=True)
    adjustment_from_ae = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    reason_adjustment_from_ae = db.Column(db.Text, nullable=True)
    subtotal_discount_fees = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    total_fees_to_client = db.Column(db.Numeric(12, 5), nullable=True, default=0)
    total_third_party_fees = db.Column(db.Numeric(12, 5), nullable=True, default=0)
    disbursement_amount = db.Column(db.Numeric(12, 2), nullable=True, default=0)
    last_processed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime)


    invoice = db.relationship("Invoice", backref="soa")
    approvals_history = db.relationship("ApprovalsHistory", backref="soa")
    verification_notes = db.relationship("VerificationNotes", backref="soa")
    invoice_supporting_documents = db.relationship("InvoiceSupportingDocuments", backref="soa")
    
    # Indexes
    __table_args__ = (
        db.Index("idx_soa_ref_id", "soa_ref_id"),
    )

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.soa_ref_id = data.get("soa_ref_id")
        self.reference_number = data.get("reference_number")
        self.status = data.get("status")
        self.institution_name = data.get("institution_name")
        self.uploaded_supporting_docs = data.get("uploaded_supporting_docs")
        self.verification_calls = data.get("verification_calls")
        self.verification_call_notes = data.get("verification_call_notes")
        self.debtor_approval_emails = data.get("debtor_approval_emails")
        self.estoppel_letters = data.get("estoppel_letters")
        self.email_verification = data.get("email_verification")
        self.po_verification = data.get("po_verification")
        self.proof_of_delivery = data.get("proof_of_delivery")
        self.notes = data.get("notes")
        self.invoice_total = data.get("invoice_total")
        self.invoice_cash_reserve_release = data.get("invoice_cash_reserve_release")
        self.disclaimer_id = data.get("disclaimer_id")
        self.discount_fees = data.get("discount_fees")
        self.credit_insurance_total = data.get("credit_insurance_total")
        self.reserves_withheld = data.get("reserves_withheld")
        self.additional_cash_reserve_held = data.get("additional_cash_reserve_held")
        self.miscellaneous_adjustment = data.get("miscellaneous_adjustment")
        self.reason_miscellaneous_adj = data.get("reason_miscellaneous_adj")
        self.fee_adjustment = data.get("fee_adjustment")
        self.reason_fee_adj = data.get("reason_fee_adj")
        self.additional_cash_reserve_release = data.get(
            "additional_cash_reserve_release"
        )
        self.advance_amount = data.get("advance_amount")
        self.high_priority = data.get("high_priority")
        self.ar_balance = data.get("ar_balance")
        self.additional_notes = data.get("additional_notes")
        self.adjustment_from_ae = data.get("adjustment_from_ae")
        self.reason_adjustment_from_ae = data.get("reason_adjustment_from_ae")
        self.subtotal_discount_fees = data.get("subtotal_discount_fees")
        self.total_fees_to_client = data.get("total_fees_to_client")
        self.total_third_party_fees = data.get("total_third_party_fees")
        self.disbursement_amount = data.get("disbursement_amount")
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
        from src.models import (
            Invoice,
            ApprovalsHistory,
            Comments,
            Disbursements,
            Reasons,
            SupportingDocuments,
        )
        # soft delete invoices, approvals history, comments, disbursements, reasons and supporting documents
        Invoice.query.filter_by(soa_id=self.id, is_deleted=False).update(
            {
                Invoice.is_deleted: True, 
                Invoice.deleted_at: datetime.utcnow()
            },
            synchronize_session=False,
        )

        ApprovalsHistory.query.filter_by(soa_id=self.id, is_deleted=False).update(
            {
                ApprovalsHistory.is_deleted: True,
                ApprovalsHistory.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )

        Comments.query.filter_by(soa_id=self.id, is_deleted=False).update(
            {
                Comments.is_deleted: True, 
                Comments.deleted_at: datetime.utcnow()
            },
            synchronize_session=False,
        )

        Disbursements.query.filter_by(soa_id=self.id, is_deleted=False).update(
            {
                Disbursements.is_deleted: True,
                Disbursements.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )

        Reasons.query.filter_by(soa_id=self.id, is_deleted=False).update(
            {
                Reasons.is_deleted: True, 
                Reasons.deleted_at: datetime.utcnow()
            },
            synchronize_session=False,
        )

        SupportingDocuments.query.filter_by(soa_id=self.id, is_deleted=False).update(
            {
                SupportingDocuments.is_deleted: True,
                SupportingDocuments.deleted_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )

        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.save()
        db.session.commit()

    @staticmethod
    def get_all_soa():
        return SOA.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_soa(id):
        return SOA.query.filter_by(id=id, is_deleted=False).first()

    @staticmethod
    def get_one_based_off_control_accounts(id):
        from src.models import (
            Client,
            ClientControlAccounts, 
            ControlAccount
        )

        # control accounts
        business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        # soa
        return (
            SOA.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                SOA.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                SOA.id == id,
                ControlAccount.name.in_(business_control_accounts),
            )
            .first()
        )

    def get_control_account(self):
        control_account = None
        clients_control_account = self.client.clients_control_account if self.client else None
        if clients_control_account:
            control_account = clients_control_account[0].control_account
        return control_account

    def had_action_required(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            soa_id=self.id, key="action_required", is_deleted=False
        ).count()

    def had_client_submitted(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            soa_id=self.id, key="client_submission_at", is_deleted=False
        ).count()

    def object_as_string(self):
        return "SOA"
        
    def request_created_by_client(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            soa_id=self.id, 
            key="client_created_at", 
            is_deleted=False
        ).first()

    def request_submitted_by_client(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            soa_id=self.id, 
            key="client_submission_at", 
            is_deleted=False
        ).order_by(
            ApprovalsHistory.id.desc()
        ).first()

    def request_created_by_principal(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            soa_id=self.id, key="created_at", is_deleted=False
        ).first()

    def request_submitted_by_principal(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            soa_id=self.id, key="submitted_at", is_deleted=False
        ).first()

    def request_approved_by_ae(self):
        from src.models import ApprovalsHistory

        return (
            ApprovalsHistory.query.filter_by(
                soa_id=self.id, key="approved_at", is_deleted=False
            )
            .order_by(ApprovalsHistory.id.desc())
            .first()
        )

    def request_approved_by_bo(self):
        from src.models import ApprovalsHistory

        return (
            ApprovalsHistory.query.filter_by(
                soa_id=self.id, key="funded_at", is_deleted=False
            )
            .order_by(ApprovalsHistory.id.desc())
            .first()
        )

    def get_selected_disclaimer(self):
        """
        Get disclaimer selected by user
        """
        has_disclaimer = False
        disclaimers_data = {}
        client_settings = {}

        if self.status.value not in ["client_draft", "client_submission", "draft"]:
            disclaimers_data = self.get_saved_disclaimer()
            if disclaimers_data:
                has_disclaimer = True
        
        # checking, if has client settings
        if not has_disclaimer:
            client_settings = self.get_client_settings_disclaimer()
            # checking, if client settings has disclaimer_text
            if (
                client_settings
                and "text" in client_settings[0]
                and client_settings[0]["text"]
            ):
                disclaimers_data.update(
                    {
                        "text": client_settings[0]["text"],
                    }
                )
                has_disclaimer = True

        # checking, if has business settings
        if not has_disclaimer:
            business_settings = self.get_business_settings_disclaimer()
            
            # checking, if business settings has disclaimer_text
            if (
                business_settings
                and "text" in business_settings[0]
                and business_settings[0]["text"]
            ):
                disclaimers_data.update(
                    {
                        "text": business_settings[0]["text"],
                    }
                )
                has_disclaimer = True

        # get disclaimer from disclaimers table, when no disclaimer_text in client settings
        if not has_disclaimer:
            disclaimer = self.get_default_disclaimer()
            if disclaimer:
                disclaimers_data = disclaimer
        
        return disclaimers_data


    def get_saved_disclaimer(self):
        """
        Get saved disclaimer from db for soa
        """
        saved_disclaimer = {}
        has_disclaimer = False

        soa_approved_attribute = self.soa_approved_history()

        # get saved client settings from approval history
        if (
            soa_approved_attribute
            and "client_settings" in soa_approved_attribute
            and soa_approved_attribute["client_settings"]
        ):
            client_settings = soa_approved_attribute["client_settings"]
            if (
                client_settings
                and "disclaimer_text" in client_settings
                and client_settings["disclaimer_text"]
            ):
                saved_disclaimer.update(
                    {
                        "text": client_settings["disclaimer_text"],
                        "name": "Custom Jurisdiction",
                    }
                )
                has_disclaimer = True

        # get saved business settings from approval history
        if (
            not has_disclaimer
            and soa_approved_attribute
            and "business_settings" in soa_approved_attribute
            and soa_approved_attribute["business_settings"]
        ):
            business_settings = soa_approved_attribute["business_settings"]
            if (
                business_settings
                and "disclaimer_text" in business_settings
                and business_settings["disclaimer_text"]
            ):
                saved_disclaimer.update(
                    {
                        "text": business_settings["disclaimer_text"],
                        "name": "Custom Jurisdiction",
                    }
                )
                has_disclaimer = True

        # get disclaimer from disclaimer table
        if not has_disclaimer:
            from src.resources.v2.models.disclaimers_model import Disclaimers
            from src.resources.v2.schemas import DisclaimerOnlySchema

            disclaimer_id = self.disclaimer_id
            if not self.disclaimer_id:
                disclaimer_id = self.client.default_disclaimer_id
                
            disclaimer = Disclaimers.query.filter_by(id=disclaimer_id, is_deleted=False).first()
            if disclaimer:
                disclaimers_data = DisclaimerOnlySchema().dump(disclaimer).data
                saved_disclaimer.update(
                    {
                        "text": disclaimers_data["text"],
                        "name": disclaimers_data["name"],
                    }
                )

        return saved_disclaimer

    def get_disbursements_payment_type(self):
        """
        related to card LC-1594
        """
        from src.models import Disbursements, ClientPayee
        
        return (
            db.session.query(
                Disbursements.payment_method,
                ClientPayee.payment_status
            ).join(
                ClientPayee, ClientPayee.payee_id == Disbursements.payee_id
            ).filter(
                Disbursements.soa_id == self.id,
                Disbursements.is_deleted == False,
                Disbursements.payee_id != None,
            )
            .distinct()
            .all()
        )

    def get_all_invoices_details(self):
        sql = f"SELECT \
        i.* , \
        cd.current_ar as current_ar, \
        cd.credit_limit as credit_limit, \
        cd.is_deleted as client_debtor_is_deleted, \
        d.name as debtor_name, \
        d.source as debtor_source, \
        d.is_deleted as debtor_is_deleted, \
        DATE_FORMAT(i.invoice_date, '%Y-%m-%d') as invoice_date, \
        DATE_FORMAT(i.created_at, '%Y-%m-%dT%H:%i:%S+00:00') as created_at, \
        DATE_FORMAT(i.updated_at, '%Y-%m-%dT%H:%i:%S+00:00') as updated_at, \
        DATEDIFF( CURDATE(), i.invoice_date) AS 'invoice_days' \
        from invoices i, \
        client_debtors cd, \
        debtors d \
        where cd.client_id = i.client_id and i.debtor = cd.debtor_id and d.id = i.debtor and i.soa_id = {self.id}"
        
        if self.status.value not in ["rejected", "principal_rejection"]:
            sql = sql + " and i.is_deleted = False "
        sql = sql + " group by i.id;"
        
        return db.session.execute(db.text(sql))

    def get_invoices(self):
        from src.models import Invoice

        return Invoice.query.filter_by(is_deleted=False, soa_id=self.id).all()

    def update_invoice_total(self):
        from src.models import Invoice
                    
        invoice_total = (
            db.session.query(func.sum(Invoice.amount))
            .select_from(Invoice)
            .filter(
                Invoice.is_deleted == False,
                Invoice.soa_id == self.id,
                Invoice.actions != "non_factored",
            )
        )
        self.invoice_total = invoice_total.scalar()
        db.session.commit()

    def soa_verification_notes(self):
        from src.models import (
            VerificationNotes,
            Debtor,
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import VerificationNotesRefSchema

        verification_notes_schema = VerificationNotesRefSchema(many=True)

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
                VerificationNotes.soa_id == self.id,
            )
            .order_by(VerificationNotes.id.asc())
            .all()
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
        #         VerificationNotes.soa_id == self.id,
        #     )
        #     .order_by(VerificationNotes.id.asc())
        #     .all()
        # )

        if not verification_notes:
            return []
            
        verification_notes_data = verification_notes_schema.dump(verification_notes, many=True).data

        return verification_notes_data

    def update_verification_notes(self):
        """
        Update Verification notes status and added verification_notes approvals history
        """
        from src.models import (
            VerificationNotes,
            VerificationNotesApprovalHistory,
        )
        from src.resources.v2.schemas.verification_notes_schema import VerificationNotesSchema

        # verification_notes
        verification_notes = VerificationNotes.query.filter_by(
            soa_id=self.id, status="draft", deleted_at=None
        ).all()
        if verification_notes:
            
            # get logged user email
            user_email = Permissions.get_user_details()["email"]
            
            for verification_note in verification_notes:
                verification_note.update({"status": "submitted", "last_processed_at": datetime.utcnow()})

                data = VerificationNotesSchema().dump(verification_note).data
                data["request_type"] = Permissions.verification_notes

                # save verification_notes approvals history
                approvals_history_data = {
                    "key": "submitted_at",
                    "value": datetime.utcnow(),
                    "user": user_email,
                    "attribute": data,
                    "verification_notes_id": verification_note.id,
                }
                approvals_history = VerificationNotesApprovalHistory(approvals_history_data)
                approvals_history.save()


    def vn_approvals_history(self, client_id=None):
        from src.models import (
            VerificationNotes,
            VerificationNotesApprovalHistory,
        )

        verification_notes = (
            VerificationNotes.query.filter(
                VerificationNotes.deleted_at == None,
                VerificationNotes.client_id == client_id,
                VerificationNotes.soa_id == self.id,
            )
            .order_by(VerificationNotes.id.desc())
            .all()
        )

        if not verification_notes:
            return []

        from src.resources.v2.helpers.convert_datetime import utc_to_local

        activity_log = []
        for verification_note in verification_notes:          
            # verification notes approval history
            approvals_history = VerificationNotesApprovalHistory.query.filter(
                VerificationNotesApprovalHistory.deleted_at == None,
                VerificationNotesApprovalHistory.verification_notes_id == verification_note.id,
            ).order_by(VerificationNotesApprovalHistory.id.asc()).all()

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

                    # activity log
                    if history_status:
                        activity_log.append(
                            {   
                                "id": each_history.id,
                                "verification_notes_id": verification_note.id,
                                "added_at": utc_to_local(
                                    dt=each_history.created_at.isoformat()
                                ),
                                "description": history_status,
                                "user": each_history.user,
                            }
                        )
        return {
            "activity_log": activity_log,
        }

    def soa_invoice_supporting_documents(self):
        from src.models import (
            InvoiceSupportingDocuments,
            Debtor,
            Client,
        )
        from src.resources.v2.schemas import InvoiceSupportingDocumentsRefSchema

        invoice_supporting_documents_schema = InvoiceSupportingDocumentsRefSchema(many=True)

        invoice_supporting_documents = (
            InvoiceSupportingDocuments.query.join(
                Debtor, Client
            )
            .filter(
                InvoiceSupportingDocuments.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                InvoiceSupportingDocuments.soa_id == self.id,
            )
            .order_by(InvoiceSupportingDocuments.id.desc())
            .all()
        )

        if not invoice_supporting_documents:
            return []
            
        invoice_supporting_documents_data = invoice_supporting_documents_schema.dump(invoice_supporting_documents, many=True).data

        return invoice_supporting_documents_data


    def is_request_updated(self):
        from src.models import ApprovalsHistory

        return ApprovalsHistory.query.filter_by(
            soa_id=self.id, key="updated_at", is_deleted=False
        ).count() 


    def cal_disbursement_total_fees(self):
        """
        Using in SOA update
        """
        from src.models import (
            Disbursements,
            Client,
            ClientSettings,
            ClientPayee,
        )

        fee_to_client = Decimal(0)
        high_priority_fee = Decimal(0)
        same_day_ach_fee = Decimal(0)
        wire_fee = Decimal(0)
        third_party_fee = Decimal(0)

        has_client_settings = False
        total_client_fees = Decimal(0)
        third_party_fee_total = Decimal(0)
        client_fee_total = Decimal(0)
        total_fees_asap = Decimal(0) # for lcra export
        total_amount = Decimal(0)
        high_priority_amount = Decimal(0)
        asap_amount = Decimal(0) # for outstanding amount cal
        
        get_payees = []

        client_settings = self.soa_client_settings()

        # client settings in table
        if client_settings:
            high_priority_fee = Decimal(client_settings["high_priority_fee"])
            same_day_ach_fee = Decimal(client_settings["same_day_ach_fee"])
            wire_fee = Decimal(client_settings["wire_fee"])
            third_party_fee = Decimal(client_settings["third_party_fee"])
            has_client_settings = True
            high_priority_amount = Decimal(client_settings["high_priority_fee"])

        # add high_priority to fee_to_client
        if self.high_priority:
            fee_to_client += high_priority_fee
            total_fees_asap += high_priority_fee
            asap_amount = high_priority_fee
            
            # # if no client settings then add principal's high priority fee
            # if not has_client_settings:
            #     from src.resources.v2.helpers.helper import principal_settings
            # 
            #     fee_to_client += principal_settings()["high_priority_fee"]
            #     total_fees_asap += principal_settings()["high_priority_fee"]
            #     asap_amount = principal_settings()["high_priority_fee"]
            #     high_priority_amount = principal_settings()["high_priority_fee"]
            

        # get total client fees
        total_client_fees = Decimal(0)
        third_party_fee_total = Decimal(0)
        client_fee_total = Decimal(0)

        # Soa disbursements
        get_soa_disbursements = Disbursements.query.filter(
            Disbursements.soa_id == self.id,
            Disbursements.is_deleted == False,
            Client.id == Disbursements.client_id,
            ClientPayee.client_id == Client.id,
            ClientPayee.payee_id == Disbursements.payee_id,
        )
        
        ## Disbursement: client as payee ##
        get_client_fees = get_soa_disbursements.filter(
            ClientPayee.ref_type == "client",
        ).all()
        if get_client_fees:
            for client_fees in get_client_fees:
                # get payees
                get_payees.append(client_fees.payee.id)
                
                # fee_to_client
                if client_fees.payment_method.value == "wire":
                    fee_to_client += wire_fee
                    
                if client_fees.payment_method.value == "same_day_ach":
                    fee_to_client += same_day_ach_fee
                
                third_party_fee_total += (
                    Decimal(client_fees.third_party_fee)
                    if client_fees.third_party_fee is not None
                    else Decimal(0)
                )
                # cal total fee to client(LC-1695) for lcra export
                client_fee_total += (
                    Decimal(client_fees.client_fee)
                    if client_fees.client_fee is not None
                    else Decimal(0)
                )

                # cal total amount of client as payee
                total_amount += Decimal(client_fees.amount)

        total_client_fees = (
            third_party_fee_total + client_fee_total
        )
        
        # cal total fee to client(LC-1695) for lcra export
        total_fees_asap += client_fee_total

        # get total payee fees
        total_payee_fees = Decimal(0)
        third_party_fee_total = Decimal(0)
        client_fee_total = Decimal(0)
        
        ## Disbursement: Third party as payee  ##
        get_payee_fees = get_soa_disbursements.filter(
            ClientPayee.ref_type == "payee",
        ).all()
        if get_payee_fees:
            for payee_fees in get_payee_fees:
                # get payees
                get_payees.append(payee_fees.payee.id)
                
                # fee_to_client
                if payee_fees.payment_method.value == "wire":
                    fee_to_client += wire_fee
                    fee_to_client += third_party_fee
                
                if payee_fees.payment_method.value == "same_day_ach":
                    fee_to_client += same_day_ach_fee
                    fee_to_client += third_party_fee
                
                if payee_fees.payment_method.value == "direct_deposit":
                    fee_to_client += third_party_fee
                
                # cal total fee to client(LC-1695) for lcra export
                third_party_fee_total += (
                    Decimal(payee_fees.third_party_fee)
                    if payee_fees.third_party_fee is not None
                    else Decimal(0)
                )
                # cal total fee to client(LC-1695) for lcra export
                client_fee_total += (
                    Decimal(payee_fees.client_fee)
                    if payee_fees.client_fee is not None
                    else Decimal(0)
                )

                # cal total amount of third party as payee
                total_amount += Decimal(payee_fees.amount)

        # cal fees for payee as third party
        total_payee_fees = (
            third_party_fee_total + client_fee_total
        )
        
        # cal total fee to client(LC-1695) for lcra export
        total_fees_asap += third_party_fee_total + client_fee_total

        # cal disbursement amount
        disbursement_amount = Decimal(self.advance_amount) - total_fees_asap

        # cal outstanding amount
        outstanding_amount = Decimal(self.advance_amount) - Decimal(total_amount + asap_amount)
        
        return {
            "fees_to_client": Decimal(total_client_fees), # total_fees_to_client in soa table 
            "third_party_fees": Decimal(total_payee_fees), # total_third_party_fees in soa table
            "total_fee_to_client": Decimal(fee_to_client), # fees_to_client + third_party_fees + high priority fee
            "total_fees_asap": Decimal(total_fees_asap), # for lcra export
            "get_payees": get_payees,
            "disbursement_amount": Decimal(disbursement_amount),
            "outstanding_amount": Decimal(outstanding_amount),
            "high_priority_amount": Decimal(high_priority_amount),
        }

    def soa_payment_process(self):
        """
        Using for soa payment process(LC-1668)
        """
        from src.models import (
            Disbursements,
            ClientPayee,
        )
        from src.resources.v2.helpers.payment_services import (
            PaymentServices
        )

        if self.status.value != "completed":
            abort(400, f"SOA is not completed")

        clients_control_account = ClientControlAccounts.query.filter_by(
            client_id=self.client_id,
            is_deleted=False,
        ).first()

        control_account_name = None
        currency = None
        if clients_control_account:
            control_account_name = clients_control_account.control_account.name
            currency = clients_control_account.control_account.currency

        # Approved Request for LCEI US Control Account Only(LC-1668)
        if control_account_name != "LCEI. US":
            print(f"Control account is not 'LCEI. US'")
            return

        # Soa disbursements
        disbursements = Disbursements.query.filter(
            Disbursements.ref_type == "soa",
            Disbursements.ref_id == self.id,
            Disbursements.is_deleted == False,
            Disbursements.is_reviewed == True,
        ).all()

        if not disbursements:
            print(f"disbursements not found for soa - {self.id}")
            return

        # payment services
        payment_services = PaymentServices(request_type=self)

        for disbursement in disbursements:
            # only for Client as Payee and/or Third Party as Payee with ACH or Same Day ACH
            if disbursement.payment_method.value in ["direct_deposit", "same_day_ach"]:
                ref_type = None

                # client payee
                client_payee = ClientPayee.query.filter_by(
                    client_id=self.client_id,
                    payee_id=disbursement.payee_id,
                    is_deleted=False,
                ).first()
                if client_payee:
                    ref_type = client_payee.ref_type.value

                data = {
                    "amount": disbursement.cal_net_amount(),
                    "ref_type": ref_type,
                    "ref_id": disbursement.payee_id,
                    "currency": currency,
                    "disbursement_id": disbursement.id,
                }
                payment_services.payment_processing(data=data)


    def soa_approved_history(self):
        """
        Get soa approved history(used in multiple functions)
        """
        # checking soa is pending/approved/completed
        if self.status.value in ["pending", "reviewed"]:
            soa_approved = self.request_submitted_by_principal()
        elif self.status.value == "approved":
            soa_approved = self.request_approved_by_ae()
        elif self.status.value == "completed":
            soa_approved = self.request_approved_by_bo()
        else:
            soa_approved = {}

        soa_approved_attribute = {}
        
        # get soa approval history
        if soa_approved:
            if isinstance(soa_approved.attribute, str):
                soa_approved_attribute = json.loads(
                    soa_approved.attribute
                )
            else:
                soa_approved_attribute = (
                    soa_approved.attribute
                )
        return soa_approved_attribute

    def soa_client_settings(self):
        """
        Get client settings(fees) for soa(used in multiple functions)
        """
        client_settings = {}
        # checking soa is pending/approved/completed
        soa_approved_attribute = self.soa_approved_history()

        # get saved client settings from approval history
        if (
            soa_approved_attribute
            and "client_settings" in soa_approved_attribute
            and soa_approved_attribute["client_settings"]
        ):
            client_settings = soa_approved_attribute["client_settings"]

        # checking, if no saved client settings
        if not client_settings:
            from src.models import (
                ClientSettings,
            )
            # get client settings
            get_client_settings = ClientSettings.query.filter_by(
                client_id=self.client.id, is_deleted=False
            ).first()
            
            # if no client settings in db
            if not get_client_settings:
                # save client settings
                client_settings_obj = {
                    "client_id": self.client_id
                }
                get_client_settings = ClientSettings(client_settings_obj)
                get_client_settings.save()

            # client settings
            if get_client_settings:
                from src.resources.v2.schemas.client_settings_schema import ClientSettingsSchema
                
                client_settings = ClientSettingsSchema().dump(
                    get_client_settings
                ).data

        return client_settings


    def get_client_disclaimer(self):
        """
        LC-1873: updated as per comments in card for system disclaimer flow
        """
        has_disclaimer = False
        client_disclaimer = []

        # checking, if client settings has disclaimer_text
        client_disclaimer = self.get_client_settings_disclaimer()
        if client_disclaimer:
            has_disclaimer = True

        # get disclaimer from business settings(admin portal), when no disclaimer_text in client settings
        if not has_disclaimer:
            client_disclaimer = self.get_business_settings_disclaimer()
            if client_disclaimer:
                has_disclaimer = True
        
        # get disclaimer from disclaimers table, when no disclaimer_text in client settings and business settings(admin portal)
        if not has_disclaimer:
            client_disclaimer = self.get_default_disclaimer()

        return client_disclaimer


    def soa_payment_status(self):
        """
        Using for soa payment status(LC-1669)
        """
        from src.models import (
            Disbursements,
            Payee,
            ClientPayee,
        )
        from src.resources.v2.helpers.payment_services import PaymentServices

        if self.status.value != "completed":
            abort(400, f"SOA is not completed")

        clients_control_account = ClientControlAccounts.query.filter_by(
            client_id=self.client_id,
            is_deleted=False,
        ).first()

        control_account_name = None
        if clients_control_account:
            control_account_name = clients_control_account.control_account.name

        # Soa disbursements
        disbursements = Disbursements.query.filter(
            Disbursements.ref_type == "soa",
            Disbursements.ref_id == self.id,
            Disbursements.is_deleted == False,
            Disbursements.is_reviewed == True,
            Disbursements.payee_id != None,
        ).all()

        if not disbursements:
            abort(404, f"disbursements not found for soa - {self.id}")

        # payment services
        payment_services = PaymentServices(request_type=self)

        disbursement_ids = []
        payment_details = []
        transaction_status = "Manual"
        transaction_id = "N/A"
        payment_method_dict = {
            "same_day_ach": "Same Day ACH",
            "wire": "Wire",
            "direct_deposit": "ACH",
        }
        for disbursement in disbursements:
            account_nickname = None

            # payee
            payee = Payee.query.filter_by(
                id=disbursement.payee_id,
            ).first()
            if payee:
                account_nickname = payee.account_nickname

            # client_payee
            client_payee = ClientPayee.query.filter_by(
                payee_id=disbursement.payee_id,
                client_id=disbursement.client_id,
            ).first()
            if client_payee:
                payment_status = client_payee.payment_status

            # only for Client as Payee and/or Third Party as Payee with ACH or Same Day ACH
            # Approved Request for LCEI US Control Account Only(LC-1668)
            if (
                disbursement.payment_method.value in ["direct_deposit", "same_day_ach"]
                and control_account_name == "LCEI. US"
            ):
                disbursement_ids.append(disbursement.id)
            
            # for showing payment type in frontend
            payment_type = disbursement.payment_method.value
            for k, v in payment_method_dict.items():
                if disbursement and disbursement.payment_method.value == k:
                    payment_type = v

            # transaction info
            payment_details_dict = {
                "ref_id": disbursement.id,
                "account_nickname": account_nickname,
                "payment_type": payment_type,
                "payment_status": payment_status,
                "status": transaction_status,
                "transaction_id": transaction_id,
                "amount": disbursement.cal_net_amount(),
            }
            payment_details.append(payment_details_dict)

        # if approved Request for LCEI US Control Account and payment type with ACH or Same Day ACH 
        if disbursement_ids:
            data = {
                "disbursement_ids": disbursement_ids,
            }
            # get bofa transaction (LC-1669)
            bofa_payment_status = payment_services.transaction_status(data=data)
            
            # On dev and beta, payment services is temporarily disabled
            if bofa_payment_status["status_code"] != 200:
                print(bofa_payment_status["status_code"], bofa_payment_status["msg"])
            
            if (
                bofa_payment_status["status_code"] == 200 
                and "payload" in bofa_payment_status 
                and bofa_payment_status["payload"]
            ):
                for payment_detail in payment_details:
                    # update status and transaction id if disbursement_id == ref_id(from payment services(transactions table))
                    [
                        payment_detail.update(
                            {
                                "status": k["bofa_status"],
                                "transaction_id": k["bofa_transaction_id"],
                            }
                        )
                        for k in bofa_payment_status["payload"]
                        if "disbursement_id" in k
                        and k["disbursement_id"] == payment_detail["ref_id"]
                    ]

        return payment_details


    def get_default_disclaimer(self):
        """
        Get disclaimers from disclaimer table(used in multiple functions)
        """
        from src.resources.v2.models.disclaimers_model import Disclaimers
        from src.resources.v2.schemas import DisclaimerOnlySchema

        default_disclaimer = []
        
        # get client's default disclaimer id
        client_default_disclaimer_id = self.client.default_disclaimer_id
        disclaimers = Disclaimers.query.filter_by(is_deleted=False)

        # if client has default disclaimer
        if client_default_disclaimer_id:
            disclaimers = disclaimers.filter_by(id=client_default_disclaimer_id)

        disclaimers_data = DisclaimerOnlySchema().dump(
            disclaimers, many=True
        ).data
        default_disclaimer.extend(disclaimers_data)

        return default_disclaimer


    def get_client_settings_disclaimer(self):
        """
        Get disclaimer from client settings based off client(used in multiple functions)
        """
        client_settings_disclaimer = []

        # checking, if has client settings
        client_settings = self.soa_client_settings()
            
        # checking, if client settings has disclaimer_text
        if (
            client_settings
            and "disclaimer_text" in client_settings
            and client_settings["disclaimer_text"]
        ):
            client_settings_disclaimer.append(
                {
                    "text": client_settings["disclaimer_text"],
                    "name": "Custom Jurisdiction",
                }
            )

        return client_settings_disclaimer


    def get_business_settings_disclaimer(self):
        """
        Get disclaimer from business settings based off control account(used in multiple functions)
        """
        business_settings_disclaimer = []
        soa_approved_attribute = {}
        has_disclaimer = False

        # checking soa is pending/approved/completed
        soa_approved_attribute = self.soa_approved_history()

        # get saved client settings from approval history
        if (
            soa_approved_attribute
            and "business_settings" in soa_approved_attribute
            and soa_approved_attribute["business_settings"]
        ):
            business_settings = soa_approved_attribute["business_settings"]
            if (
                business_settings 
                and "disclaimer_text" in business_settings 
                and business_settings["disclaimer_text"]
            ):
                business_settings_disclaimer.append(
                    {
                        "text": business_settings["disclaimer_text"],
                        "name": "Custom Jurisdiction",
                    }
                )
                has_disclaimer = True

        # get disclaimer from business settings(admin portal)
        if not has_disclaimer:
            control_accounts = Permissions.get_business_settings()[
                "control_accounts_disclaimer"
            ]
            
            if control_accounts:
                for k, v in control_accounts.items():
                    client_control_account = self.get_control_account()

                    if (
                        client_control_account
                        and client_control_account.name == k
                        and v
                    ):
                        business_settings_disclaimer.append(
                            {
                                "text": v,
                                "name": "Custom Jurisdiction",
                            }
                        )
        return business_settings_disclaimer

class SOAListing:    

    def get_all():
        from src.resources.v2.schemas import SOAResourseSchema
        
        soa_schema = SOAResourseSchema(many=True)

        # ORGANIZATION
        get_locations = Organization.get_locations()
        client_ids = get_locations["client_list"]

        # user role
        user_role = get_locations["user_role"]

        soa = SOA.query.filter(
            SOA.is_deleted == False, 
            and_(
                SOA.status != "action_required_by_client",
                SOA.status != "client_draft",
                SOA.status != "principal_rejection", 
            ), 
            SOA.client_id.in_(client_ids)
        )

        # get soa having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            soa = soa.filter(SOA.status != "client_submission")
            
        soa_results = soa_schema.dump(soa).data

        if len(soa_results) < 1:
            return None

        return soa_results

    def get_paginated_soa(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        ordering = kwargs.get("ordering", None)
        search = kwargs.get("search", None)
        start_date = kwargs.get("start_date", None)
        end_date = kwargs.get("end_date", None)
        control_account = kwargs.get("control_account", None)
        stage = kwargs.get("stage", None)
        use_ref = kwargs.get("use_ref", False)
        high_priority = kwargs.get("high_priority", None)
        dashboard = kwargs.get("dashboard", False)
        client_ids = kwargs.get("client_ids", None)
        user_role = kwargs.get("user_role", None)
        business_control_accounts = kwargs.get("business_control_accounts", [])
        
        from src.models import (
            Client,
            ClientControlAccounts,
            ControlAccount,
        )
        from src.resources.v2.schemas import (
            SOAResourseSchema,
            SOADashboardSchema,
            SOAclientSchema,
        )

        soa_schema = SOAResourseSchema(many=True)
        if dashboard:
            soa_schema = SOADashboardSchema(many=True)
        # Dashboard: get soa based off disbursement: no start_date and no end_date) and not ("client_submission", "completed")
        if (
            dashboard
            and (not stage or stage not in ["client_submission", "completed"])
            and (not start_date and not end_date)
        ):
            # soa_schema = SOADashboardSchema(many=True)
            return SOAListing.get_soa_by_disbursement(**kwargs)
        
        # only for Client's Request lane in principal dashboard
        if (
            dashboard 
            and stage 
            and stage == "client_submission"
        ):
            soa_schema = SOADashboardSchema(many=True)

        # if dashboard=False, get client ids, user_role, business_control_accounts
        if not dashboard:
            # ORGANIZATION
            get_locations = Organization.get_locations()
            client_ids = get_locations["client_list"]

            # user role
            user_role = get_locations["user_role"]

            # control accounts
            business_control_accounts = Permissions.get_business_settings()["control_accounts"]

        # soa
        soa = (
            SOA.query.join(Client, ClientControlAccounts, ControlAccount)
            .filter(
                SOA.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                not_(
                    SOA.status.in_(
                        [
                            "action_required_by_client",
                            "client_draft",
                            "principal_rejection",
                        ]
                    )
                ),
                SOA.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts)
            )
            .group_by(SOA.id)
        )

        # get only completed requests for inactive clients LC-2188
        soa = soa.filter(
            or_(
                Client.is_active == True,
                and_(
                        Client.is_active == False,
                        SOA.status == "completed",
                    )
            )
        )

        # get soa having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            soa = soa.filter(SOA.status != "client_submission")

        # filter by control_account
        if control_account is not None:
            soa = soa.filter(ControlAccount.name == control_account)

        # filter for status
        if stage is not None:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                soa = soa.filter(SOA.status.in_(stages_split))
            else:
                if stage == "archived":
                    soa = soa.filter(
                        or_(
                            SOA.status == "completed"
                        )
                    )
                elif stage == "rejected":
                    soa = soa.filter(
                        SOA.status == "rejected"
                    )
                elif stage == "completed":
                    from src.resources.v2.helpers.convert_datetime import date_concat_time
                    # current est date: for comparing with last_processed_at(utc)
                    today = date_concat_time(date_concat="current")
                    next_day = date_concat_time(date_concat="next")

                    soa = soa.filter(
                        SOA.status == "completed",
                        cast(SOA.last_processed_at, DateTime) >= today,
                        cast(SOA.last_processed_at, DateTime) <= next_day
                    )
                elif stage == "pending":
                    soa = soa.filter(
                        or_(
                            SOA.status == "pending",
                            SOA.status == "reviewed"
                        )
                    )
                else:
                    soa = soa.filter(SOA.status == stage)

        # start_date and end_date filter
        if start_date and end_date:
            if start_date == end_date:
                soa = soa.filter(
                    SOA.last_processed_at >= start_date,
                    SOA.last_processed_at < (start_date + timedelta(days=1))
                )
            else:
                soa = soa.filter(
                    SOA.last_processed_at > start_date,
                    SOA.last_processed_at < (end_date + timedelta(days=1))
                )
        elif start_date:
            soa = soa.filter(
                SOA.last_processed_at >= start_date
            )
        elif end_date:
            soa = soa.filter(
                SOA.last_processed_at < (end_date + timedelta(days=1))
            )

        # soa search
        if search is not None:
            if "-SOAID" in search.upper():
                ref_client_no = search.upper().split("-SOAID")[0]
                soa_ref_id = search.upper().split("-SOAID")[1]
                soa = soa.filter(
                    and_(
                        Client.ref_client_no.like("%" + ref_client_no + "%"),
                        SOA.soa_ref_id.like(soa_ref_id + "%")
                    )
                )
            elif "SOAID" in search.upper():
                soa_ref_id = search.upper().split("SOAID")[1]
                soa = soa.filter(
                    SOA.soa_ref_id.like(soa_ref_id + "%")
                )
            elif "SOA" in search.upper():
                soa_ref_id = search.upper().split("SOA")[1]
                if soa_ref_id:
                    soa = soa.filter(
                        SOA.soa_ref_id.like(soa_ref_id + "%")
                    )
            elif use_ref:
                soa = soa.filter(
                    or_(
                        Client.name.like("%" + search + "%"),
                        SOA.disbursement_amount.like("%" + search + "%"),
                        SOA.invoice_total.like("%" + search + "%"),
                        SOA.soa_ref_id.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%")
                    )
                )
            else:
                soa = soa.filter(
                    or_(
                        Client.name.like("%" + search + "%"),
                        SOA.soa_ref_id.like("%" + search + "%"),
                        SOA.disbursement_amount.like("%" + search + "%"),
                        SOA.invoice_total.like("%" + search + "%"),
                        SOA.reference_number.like("%" + search + "%"),
                        Client.ref_client_no.like("%" + search + "%")
                    )
                )

        # high priority filter
        if high_priority is not None:
            soa = soa.filter(SOA.high_priority == True)

        # ordering(sorting)
        if ordering is not None:
            if "soa_ref_id" == ordering:
                soa = soa.order_by(SOA.soa_ref_id.asc())

            if "-soa_ref_id" == ordering:
                soa = soa.order_by(SOA.soa_ref_id.desc())

            if "date" == ordering:
                soa = soa.order_by(SOA.last_processed_at.asc())

            if "-date" == ordering:
                soa = soa.order_by(SOA.last_processed_at.desc())

            if "advance_amount" == ordering:
                soa = soa.order_by(SOA.advance_amount.asc())

            if "-advance_amount" == ordering:
                soa = soa.order_by(SOA.advance_amount.desc())

            if "status" == ordering:
                soa = soa.order_by(SOA.status.asc())

            if "-status" == ordering:
                soa = soa.order_by(SOA.status.desc())

            if "invoice_total" == ordering:
                soa = soa.order_by(SOA.invoice_total.asc())

            if "-invoice_total" == ordering:
                soa = soa.order_by(SOA.invoice_total.desc())

            if "high_priority" == ordering:
                soa = soa.order_by(SOA.high_priority.asc())

            if "-high_priority" == ordering:
                soa = soa.order_by(SOA.high_priority.desc())

            if "client_name" == ordering:
                soa = soa.order_by(Client.name.asc())

            if "-client_name" == ordering:
                soa = soa.order_by(Client.name.desc())

            if "created_at" == ordering:
                soa = soa.order_by(SOA.created_at.asc())

            if "-created_at" == ordering:
                soa = soa.order_by(SOA.created_at.desc())

            if "disbursement_amount" == ordering:
                soa = soa.order_by(SOA.disbursement_amount.asc())

            if "-disbursement_amount" == ordering:
                soa = soa.order_by(SOA.disbursement_amount.desc())

            if "client_number_soa_id_number" == ordering:
                soa = soa.order_by(SOA.soa_ref_id.asc())

            if "-client_number_soa_id_number" == ordering:
                soa = soa.order_by(SOA.soa_ref_id.desc())
        else:
            soa = soa.order_by(SOA.updated_at.desc())

        # pagination
        soa = soa.paginate(page, rpp, False)
        total_pages = math.ceil(soa.total / rpp)
        soa_results = soa_schema.dump(soa.items).data
        total_count = soa.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )

        # invalid page number
        if len(soa_results) < 1:
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
            "data": soa_results,
        }


    def get_soa_by_disbursement(**kwargs):
        # filters
        page = kwargs.get("page", 1)
        rpp = kwargs.get("rpp", 20)
        # start_date = kwargs.get("start_date", None)
        # end_date = kwargs.get("end_date", None)
        control_account = kwargs.get("control_account", None)
        stage = kwargs.get("stage", None)
        high_priority = kwargs.get("high_priority", None)
        # ordering = kwargs.get("ordering", None)
        dashboard = kwargs.get("dashboard", False)
        client_ids = kwargs.get("client_ids", None)
        user_role = kwargs.get("user_role", None)
        business_control_accounts = kwargs.get("business_control_accounts", [])
        
        from src.models import (
            Client,
            ClientControlAccounts,
            ControlAccount,
            Disbursements,
        )
        from src.resources.v2.schemas import (
            SOADashboardSchema,
        )

        soa_schema = SOADashboardSchema(many=True)

        if not dashboard:
            # ORGANIZATION
            get_locations = Organization.get_locations()
            client_ids = get_locations["client_list"]
            
            # user role
            user_role = get_locations["user_role"]
            
            # control accounts
            business_control_accounts = Permissions.get_business_settings()["control_accounts"]
        
        # soa
        soa = (
            SOA.query.join(Client, ClientControlAccounts, ControlAccount)
            .outerjoin(
                Disbursements,
                and_(
                    Disbursements.ref_type == "soa",
                    Disbursements.ref_id == SOA.id,
                    Disbursements.is_deleted == False,
                    Disbursements.payment_method.in_(
                        ["same_day_ach", "wire", "direct_deposit"]
                    ),
                    Disbursements.payee_id != None,
                ),
            )
            .filter(
                SOA.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                Client.is_deleted == False,
                not_(
                    SOA.status.in_(
                        [
                            "draft",
                            "action_required_by_client",
                            "client_draft",
                            "principal_rejection",
                        ]
                    )
                ),
                SOA.client_id.in_(client_ids),
                ControlAccount.name.in_(business_control_accounts)
            )
            .group_by(SOA.id)
        )

        # only show active clients requests in dashboard
        if dashboard:
            soa = soa.filter(Client.is_active == True)
        
        # get soa having status == client_submission only for principal
        if user_role and user_role.lower() != "principal":
            soa = soa.filter(SOA.status != "client_submission")

        # high priority filter
        if high_priority:
            soa = soa.filter(SOA.high_priority == True)

        # filter by control_account
        if control_account:
            soa = soa.filter(ControlAccount.name == control_account)
        
        # filter for status
        if stage:
            stages_split = stage.split(",")

            if len(stages_split) > 1:
                soa = soa.filter(SOA.status.in_(stages_split))
            else:
                if stage == "pending":
                    soa = soa.filter(
                        or_(
                            SOA.status == "pending",
                            SOA.status == "reviewed"
                        )
                    )                
                # if stage == "completed":
                #    from src.resources.v2.helpers.convert_datetime import date_concat_time
                #     # current est date: for comparing with last_processed_at(utc)
                #        today = date_concat_time(date_concat="current")
                #        next_day = date_concat_time(date_concat="next")

                #     soa = soa.filter(
                #         SOA.status == "completed",
                #        cast(SOA.last_processed_at, DateTime) >= today,
                #        cast(SOA.last_processed_at, DateTime) <= next_day
                #     )
                else:
                    soa = soa.filter(SOA.status == stage)
        
        soa = soa.order_by(
            SOA.high_priority.desc(),
            func.field(
                Disbursements.payment_method,
                "same_day_ach",
                "wire",
                "direct_deposit",
            ),
            SOA.last_processed_at.asc(),
        )
        
        # pagination
        pagination_obj = soa.paginate(page, rpp, False)
        total_pages = pagination_obj.pages
        soa_data = soa_schema.dump(pagination_obj.items).data
        total_count = pagination_obj.total

        get_invalid_page_msg = (
            "Invalid page number"
            if ((total_count > 1) & (page > total_pages))
            else "Records not found"
        )
        
        # invalid page number
        if len(soa_data) < 1:
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
            "data": soa_data,
        }
