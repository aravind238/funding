from src import db
from datetime import datetime



class Comments(db.Model):
    """ Comments model """

    __tablename__ = "comments"

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
    debtor_limit_approvals_id = db.Column(
        db.Integer,
        db.ForeignKey("debtor_limit_approvals.id", ondelete="CASCADE"),
        nullable=True,
    )
    generic_request_id = db.Column(
        db.Integer,
        db.ForeignKey("lc_generic_request.id", ondelete="CASCADE"),
        nullable=True,
    )
    compliance_repository_id = db.Column(
        db.Integer,
        db.ForeignKey("lc_compliance_repository.id", ondelete="CASCADE"),
        nullable=True,
    )
    comment = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    added_by = db.Column(db.String(255), nullable=True)
    url = db.Column(db.String(255), nullable=True)  # need to update url fields
    name = db.Column(db.String(255), nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.soa_id = data.get("soa_id")
        self.comment = data.get("comment")
        self.reserve_release_id = data.get("reserve_release_id")
        self.payee_id = data.get("payee_id")
        self.debtor_limit_approvals_id = data.get("debtor_limit_approvals_id")
        self.generic_request_id = data.get("generic_request_id")
        self.compliance_repository_id = data.get("compliance_repository_id")
        self.tags = data.get("tags")
        self.added_by = data.get("added_by")
        self.url = data.get("url")
        self.name = data.get("name")
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
    def get_all_comments():
        return Comments.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_comment(id):
        return Comments.query.filter_by(id=id, is_deleted=False).first()
