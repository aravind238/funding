from src import db
from datetime import datetime


class ApprovalsHistory(db.Model):
    """ ApprovalsHistory model """

    __tablename__ = "approvals_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    soa_id = db.Column(
        db.Integer, db.ForeignKey("soa.id", ondelete="CASCADE"), nullable=True
    )
    reserve_release_id = db.Column(
        db.Integer,
        db.ForeignKey("reserve_release.id", ondelete="CASCADE"),
        nullable=True,
    )
    payee_id = db.Column(
        db.Integer,
        db.ForeignKey("payees.id", ondelete="CASCADE"),
        nullable=True,
    )
    key = db.Column(db.String(255), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    user = db.Column(db.String(255), nullable=False)
    attribute = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.soa_id = data.get("soa_id")
        self.reserve_release_id = data.get("reserve_release_id")
        self.payee_id = data.get("payee_id")
        self.key = data.get("key")
        self.value = data.get("value")
        self.user = data.get("user")
        self.attribute = data.get("attribute")
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
    def get_all_approvals_history():
        return ApprovalsHistory.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_approval_history(id):
        return ApprovalsHistory.query.filter_by(id=id, is_deleted=False).first()
