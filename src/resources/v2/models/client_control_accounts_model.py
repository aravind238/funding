from src import db
from datetime import datetime


class ClientControlAccounts(db.Model):
    """ ClientControlAccounts model """

    __tablename__ = "client_control_accounts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    control_account_id = db.Column(
        db.Integer,
        db.ForeignKey("control_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.control_account_id = data.get("control_account_id")
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
    def get_all_client_control_accounts():
        return ClientControlAccounts.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_client_control_account(id):
        return ClientControlAccounts.query.filter_by(id=id, is_deleted=False).first()
