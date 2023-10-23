from src import db
from datetime import datetime


class OrganizationClientAccount(db.Model):
    """ OrganizationClientAccount model """

    __tablename__ = "organization_client_account"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    organization_id = db.Column(db.String(255), nullable=True)
    lcra_client_account_id = db.Column(db.String(255), nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = db.Column(db.DateTime)

    # Indexes
    __table_args__ = (
        db.Index("idx_lcra_client_account_id", "lcra_client_account_id"),
        db.Index("idx_organization_id", "organization_id"),
    )

    def __init__(self, data):
        self.client_id = data.get("client_id")
        self.organization_id = data.get("organization_id")
        self.lcra_client_account_id = data.get("lcra_client_account_id")
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
    def get_all_organization_client_account():
        return OrganizationClientAccount.query.filter_by(is_deleted=False)

    @staticmethod
    def get_one_organization_client_account(id):
        return OrganizationClientAccount.query.filter_by(
            id=id, is_deleted=False
        ).first()
