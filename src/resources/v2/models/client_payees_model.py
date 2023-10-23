from src import db
from datetime import datetime
import enum


PayeePaymentStatus = [
    "In-System",
    "Out-of-System"
]

class ClientPayeeStatus(enum.Enum):
    client = "client"
    payee = "payee"


class ClientPayee(db.Model):
    """ Client Payee model """

    __tablename__ = "client_payees"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    payee_id = db.Column(
        db.Integer, db.ForeignKey("payees.id", ondelete="CASCADE"), nullable=False
    )
    ref_type = db.Column(db.Enum(ClientPayeeStatus), default=ClientPayeeStatus.payee.value, server_default=ClientPayeeStatus.payee.value)
    payment_status = db.Column(db.String(255), nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.payee_id = data.get("payee_id")
        self.ref_type = data.get("ref_type")
        self.payment_status = data.get("payment_status")
        self.is_deleted = data.get("is_deleted")
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
    def get_all_client_payees():
        return ClientPayee.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_client_payee(id):
        return ClientPayee.query.filter_by(id=id, is_deleted=False).first()

    @staticmethod
    def get_by_client_payee_id(client_id, payee_id):
        return ClientPayee.query.filter_by(
            payee_id=payee_id, client_id=client_id, is_deleted=False
        ).first()
