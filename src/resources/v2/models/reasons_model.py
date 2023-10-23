from src import db
from datetime import datetime


class Reasons(db.Model):
    """ Reasons model """

    __tablename__ = "reasons"

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
    lack_of_collateral = db.Column(db.Boolean, default=False)
    unacceptable_collateral = db.Column(db.Boolean, default=False)
    invoice_discrepancy = db.Column(db.Boolean, default=False)
    no_assignment_stamp = db.Column(db.Boolean, default=False)
    pre_billing = db.Column(db.Boolean, default=False)
    client_over_limit = db.Column(db.Boolean, default=False)
    confirmation_issue = db.Column(db.Boolean, default=False)
    others = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(255), nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    def __init__(self, data):
        self.soa_id = data.get("soa_id")
        self.reserve_release_id = data.get("reserve_release_id")
        self.payee_id = data.get("payee_id")
        self.debtor_limit_approvals_id = data.get("debtor_limit_approvals_id")
        self.generic_request_id = data.get("generic_request_id")
        self.compliance_repository_id = data.get("compliance_repository_id")
        self.lack_of_collateral = data.get("lack_of_collateral")
        self.unacceptable_collateral = data.get("unacceptable_collateral")
        self.invoice_discrepancy = data.get("invoice_discrepancy")
        self.no_assignment_stamp = data.get("no_assignment_stamp")
        self.pre_billing = data.get("pre_billing")
        self.client_over_limit = data.get("client_over_limit")
        self.confirmation_issue = data.get("confirmation_issue")
        self.others = data.get("others")
        self.notes = data.get("notes")
        self.status = data.get("status")
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
    def get_all_reasons():
        return Reasons.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_reasons(id):
        return Reasons.query.filter_by(id=id, is_deleted=False).first()
