from src import db
import enum
from datetime import datetime, timedelta
from src.models import *
from src.middleware.permissions import Permissions
from src.middleware.organization import Organization
from sqlalchemy import and_, or_, not_, cast, DateTime




class InvoiceSupportingDocuments(db.Model):
    """Invoice Supporting Documents model"""

    __tablename__ = "lc_invoice_supporting_documents"

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
    url = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    name = db.Column(db.String(255), nullable=True)
    user = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    # back relation field
    invoice = db.relationship("Invoice", backref="invoice_supporting_documents")

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.debtor_id = data.get("debtor_id")
        self.invoice_id = data.get("invoice_id")
        self.soa_id = data.get("soa_id")
        self.url = data.get("url")
        self.notes = data.get("notes")
        self.name = data.get("name")
        self.user = data.get("user")
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
        return InvoiceSupportingDocuments.query.filter(
            InvoiceSupportingDocuments.deleted_at == None,
            InvoiceSupportingDocuments.client_id.in_(client_ids),
        )

    @staticmethod
    def get_one(id):
        return InvoiceSupportingDocuments.query.filter(
            InvoiceSupportingDocuments.id == id,
            InvoiceSupportingDocuments.deleted_at == None,
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
            InvoiceSupportingDocuments.query.join(
                Debtor, Client, ClientControlAccounts, ControlAccount
            )
            .filter(
                InvoiceSupportingDocuments.deleted_at == None,
                Debtor.is_deleted == False,
                Client.is_deleted == False,
                ControlAccount.is_deleted == False,
                ClientControlAccounts.is_deleted == False,
                ControlAccount.name.in_(business_control_accounts),
                InvoiceSupportingDocuments.id == id,
            )
            .first()
        )

    def get_invoice_number(self):
        return self.invoice.invoice_number if self.invoice else None

    def get_debtor_name(self):
        return self.debtor.name if self.debtor else None

    def get_debtor_ref_key(self):
        return self.debtor.ref_key if self.debtor else None

    def get_client_name(self):
        return self.client.name if self.client else None

    def object_as_string(self):
        return "Invoice Supporting Documents"

    
