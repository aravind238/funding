from src import db
from datetime import datetime


class DebtorLimitApprovalsHistory(db.Model):
    """ DebtorLimitApprovalsHistory model """

    __tablename__ = "debtor_limit_approvals_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    debtor_limit_approvals_id = db.Column(
        db.Integer,
        db.ForeignKey("debtor_limit_approvals.id", ondelete="CASCADE"),
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
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.debtor_limit_approvals_id = data.get("debtor_limit_approvals_id")
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
    def get_all():
        return DebtorLimitApprovalsHistory.query.filter_by(deleted_at=None)

    @staticmethod
    def get_one(id):
        return DebtorLimitApprovalsHistory.query.filter_by(
            id=id, deleted_at=None
        ).first()
